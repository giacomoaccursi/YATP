"""Portfolio engine: modular calculation of portfolio metrics.

Each method computes one metric independently.
The engine replays transactions once at init, then each method
reads from the shared state without recalculating.
"""

from portfolio.portfolio import value_holdings
from portfolio.returns import calc_xirr, calc_simple_return, calc_period_mwrr


class PortfolioEngine:
    """Stateful engine that replays transactions once and exposes metric methods.

    Usage:
        engine = PortfolioEngine(df, price_histories)
        history = engine.daily_values()
        change = engine.daily_change()
        twr = engine.cumulative_twr()
    """

    def __init__(self, df, price_histories, market_dates=None):
        """Replay all transactions and build internal state.

        Args:
            df: Sorted transactions DataFrame
            price_histories: dict of security -> price Series
            market_dates: list of dates to track (defaults to all price dates)
        """
        self._price_histories = price_histories
        self._replay(df, market_dates)

    # ── Internal replay (runs once at init) ──

    def _replay(self, df, market_dates):
        """Single-pass replay of all transactions. Populates internal state."""
        tx_events = []
        for _, row in df.iterrows():
            tx_events.append((
                row["Date"].normalize(),
                row["Security"],
                row["Type"].strip().lower(),
                row["Shares"],
                row["Net Transaction Value"],
            ))
        tx_events.sort(key=lambda e: e[0])

        if market_dates is not None:
            all_dates = sorted(market_dates)
        else:
            all_dates = sorted(set(e[0] for e in tx_events))

        # State accumulators
        holdings = {}
        cost_state = {}
        cum_realized = 0.0
        cum_income = 0.0
        total_invested = 0.0
        cashflows = []
        tx_idx = 0

        # Per-date snapshots
        self._dates = []
        self._holdings_list = []
        self._prev_holdings_list = []
        self._cost_basis_list = []
        self._realized_list = []
        self._income_list = []
        self._invested_list = []
        self._has_txn_list = []
        self._cashflows = []

        for date in all_dates:
            prev_holdings = dict(holdings)
            has_txn = False

            while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
                has_txn = True
                _, security, tx_type, shares, net_value = tx_events[tx_idx]

                if security not in cost_state:
                    cost_state[security] = {"shares": 0.0, "cost": 0.0}

                if tx_type == "buy":
                    holdings[security] = holdings.get(security, 0.0) + shares
                    cost_state[security]["shares"] += shares
                    cost_state[security]["cost"] += net_value
                    total_invested += net_value
                    cashflows.append((date.to_pydatetime(), -net_value))

                elif tx_type == "sell":
                    holdings[security] = holdings.get(security, 0.0) - shares
                    if cost_state[security]["shares"] > 0:
                        avg = cost_state[security]["cost"] / cost_state[security]["shares"]
                        cost_of_sold = avg * shares
                        cum_realized += net_value - cost_of_sold
                        cost_state[security]["cost"] -= cost_of_sold
                    cost_state[security]["shares"] -= shares
                    if holdings.get(security, 0) <= 1e-9:
                        holdings.pop(security, None)
                        cost_state[security] = {"shares": 0.0, "cost": 0.0}
                    cashflows.append((date.to_pydatetime(), net_value))

                elif tx_type in ("dividend", "coupon"):
                    cum_income += net_value
                    cashflows.append((date.to_pydatetime(), net_value))

                tx_idx += 1

            total_cost = sum(s["cost"] for s in cost_state.values())

            self._dates.append(date)
            self._holdings_list.append(dict(holdings))
            self._prev_holdings_list.append(prev_holdings)
            self._cost_basis_list.append(total_cost)
            self._realized_list.append(cum_realized)
            self._income_list.append(cum_income)
            self._invested_list.append(total_invested)
            self._has_txn_list.append(has_txn)

        self._cashflows = cashflows

    # ── Value methods ──

    def _value_at(self, index):
        """Portfolio market value at a given snapshot index."""
        return value_holdings(self._holdings_list[index], self._price_histories, self._dates[index])

    def _value_before_at(self, index):
        """Portfolio value with previous holdings at current date's prices."""
        return value_holdings(self._prev_holdings_list[index], self._price_histories, self._dates[index])

    # ── Public metric methods ──

    def daily_values(self):
        """Market value for each date. Returns list of (date_str, value)."""
        result = []
        for i in range(len(self._dates)):
            val = self._value_at(i)
            result.append((self._dates[i].strftime("%Y-%m-%d"), round(val, 2)))
        return result

    def daily_costs(self):
        """Cost basis for each date. Returns list of (date_str, cost)."""
        return [(self._dates[i].strftime("%Y-%m-%d"), round(self._cost_basis_list[i], 2))
                for i in range(len(self._dates))]

    def daily_unrealized(self):
        """Unrealized P&L for each date. Returns list of (date_str, pnl)."""
        result = []
        for i in range(len(self._dates)):
            val = self._value_at(i)
            result.append((self._dates[i].strftime("%Y-%m-%d"), round(val - self._cost_basis_list[i], 2)))
        return result

    def simple_return_series(self):
        """Unrealized return % for each date. Carries forward when portfolio is empty."""
        last_pct = 0.0
        result = []
        for i in range(len(self._dates)):
            cost = self._cost_basis_list[i]
            if cost > 0:
                val = self._value_at(i)
                last_pct = round(((val - cost) / cost) * 100, 2)
            result.append(last_pct)
        return result

    def total_return_series(self):
        """Total return % (unrealized + realized + income) for each date."""
        last_pct = 0.0
        result = []
        for i in range(len(self._dates)):
            cost = self._cost_basis_list[i]
            if cost > 0:
                val = self._value_at(i)
                unrealized = val - cost
                total_gain = unrealized + self._realized_list[i] + self._income_list[i]
                last_pct = round((total_gain / cost) * 100, 2)
            result.append(last_pct)
        return result

    def cumulative_twr(self):
        """Cumulative TWR % for each date."""
        cum = 1.0
        prev_after = None
        result = []

        for i in range(len(self._dates)):
            val = self._value_at(i)

            if self._has_txn_list[i]:
                val_before = self._value_before_at(i)
                if prev_after is not None and prev_after > 0 and val_before > 0:
                    cum *= val_before / prev_after
                prev_after = val if val > 0 else None
                result.append(round((cum - 1) * 100, 2))
            elif prev_after is not None and prev_after > 0 and val > 0:
                running = cum * (val / prev_after)
                result.append(round((running - 1) * 100, 2))
            else:
                result.append(result[-1] if result else 0.0)

        return result

    def daily_change(self):
        """Portfolio value change from previous day. Returns dict or None."""
        if len(self._dates) < 2:
            return None

        val_prev = self._value_at(-2)
        val_today = self._value_at(-1)

        if val_prev <= 0:
            return None

        amount = val_today - val_prev
        pct = (amount / val_prev) * 100
        return {"amount": round(amount, 2), "pct": round(pct, 2)}

    def holdings_at(self, index=-1):
        """Holdings dict at a given snapshot index."""
        return dict(self._holdings_list[index])

    def cost_basis_at(self, index=-1):
        """Cost basis at a given snapshot index."""
        return self._cost_basis_list[index]

    def realized_pnl(self):
        """Total cumulative realized P&L."""
        return self._realized_list[-1] if self._realized_list else 0.0

    def total_income(self):
        """Total cumulative income (dividends + coupons)."""
        return self._income_list[-1] if self._income_list else 0.0

    def xirr(self):
        """Annualized XIRR from all cashflows. Returns float or None."""
        if not self._cashflows or len(self._dates) == 0:
            return None
        val = self._value_at(-1)
        if val <= 0:
            return None
        cfs = self._cashflows + [(self._dates[-1].to_pydatetime(), val)]
        return calc_xirr(cfs)

    def date_strings(self):
        """List of date strings."""
        return [d.strftime("%Y-%m-%d") for d in self._dates]

    def full_history(self):
        """All daily metrics in one dict. Convenience method."""
        return {
            "dates": self.date_strings(),
            "values": [v for _, v in self.daily_values()],
            "costs": [c for _, c in self.daily_costs()],
            "return_pcts": self.simple_return_series(),
            "total_return_pcts": self.total_return_series(),
            "twr_pcts": self.cumulative_twr(),
            "unrealized_pnls": [p for _, p in self.daily_unrealized()],
        }
