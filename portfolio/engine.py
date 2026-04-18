"""Portfolio engine: modular calculation of portfolio metrics.

Each method computes one metric independently.
The engine replays transactions once at init, then each method
reads from the shared state without recalculating.
"""

from portfolio.portfolio import value_holdings
from portfolio.returns import calc_xirr, calc_simple_return, calc_period_mwrr, calc_cumulative_twr


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
                last_pct = round(calc_simple_return(val - cost, cost), 2)
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
                total_gain = (val - cost) + self._realized_list[i] + self._income_list[i]
                last_pct = round(calc_simple_return(total_gain, cost), 2)
            result.append(last_pct)
        return result

    def cumulative_twr(self):
        """Cumulative TWR % for each date.

        Uses sub-period chaining: at each transaction, close the sub-period
        with value_before / prev_value_after, then start a new sub-period.
        Between transactions, show running TWR.
        """
        return calc_cumulative_twr(
            dates=self._dates,
            has_txn_list=self._has_txn_list,
            value_at=self._value_at,
            value_before_at=self._value_before_at,
        )

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


    # ── Period methods ──

    def period_twr(self, start_date, end_date):
        """TWR for a specific period. Returns float (decimal, not %) or None."""
        twr_series = self.cumulative_twr()
        dates = self._dates

        # Find indices for start and end
        start_idx = None
        end_idx = None
        for i, d in enumerate(dates):
            if start_idx is None and d >= start_date:
                start_idx = i
            if d <= end_date:
                end_idx = i

        # Use last date before start if exact match not found
        for i, d in enumerate(dates):
            if d <= start_date:
                start_idx = i

        if start_idx is None or end_idx is None or end_idx <= start_idx:
            return None

        start_factor = 1 + twr_series[start_idx] / 100
        end_factor = 1 + twr_series[end_idx] / 100
        if start_factor <= 0:
            return None
        return end_factor / start_factor - 1

    def period_mwrr(self, start_date, end_date, days):
        """MWRR (de-annualized XIRR) for a specific period. Returns float (%) or None."""
        from portfolio.portfolio import value_holdings as _val, get_cashflows_between

        # Find holdings at start
        start_idx = 0
        for i, d in enumerate(self._dates):
            if d <= start_date:
                start_idx = i

        start_value = self._value_at(start_idx) if start_idx < len(self._dates) else 0

        # Find holdings at end
        end_idx = len(self._dates) - 1
        for i, d in enumerate(self._dates):
            if d <= end_date:
                end_idx = i

        end_value = self._value_at(end_idx) if end_idx < len(self._dates) else 0

        # Build cashflows for the period from stored cashflows
        cashflows = []
        if start_value > 0:
            cashflows.append((start_date.to_pydatetime() if hasattr(start_date, 'to_pydatetime') else start_date, -start_value))

        for cf_date, cf_amount in self._cashflows:
            cf_ts = cf_date if hasattr(cf_date, 'timestamp') else cf_date
            sd = start_date.to_pydatetime() if hasattr(start_date, 'to_pydatetime') else start_date
            ed = end_date.to_pydatetime() if hasattr(end_date, 'to_pydatetime') else end_date
            if sd < cf_date <= ed:
                cashflows.append((cf_date, cf_amount))

        if end_value > 0:
            cashflows.append((end_date.to_pydatetime() if hasattr(end_date, 'to_pydatetime') else end_date, end_value))

        if len(cashflows) < 2:
            return None

        return calc_period_mwrr(cashflows, days)

    def period_market_gain(self, start_date, end_date, df):
        """Market gain for a period (price appreciation, excludes new money)."""
        from portfolio.portfolio import get_net_new_money_between

        start_idx = 0
        end_idx = len(self._dates) - 1
        for i, d in enumerate(self._dates):
            if d <= start_date:
                start_idx = i
            if d <= end_date:
                end_idx = i

        start_value = self._value_at(start_idx)
        end_value = self._value_at(end_idx)
        net_new = get_net_new_money_between(start_date, end_date, df)
        return (end_value - start_value) - net_new

    def period_income(self, start_date, end_date, df):
        """Income (dividends + coupons) in a period."""
        period_df = df[(df["Date"] > start_date) & (df["Date"] <= end_date)]
        return sum(
            row["Net Transaction Value"]
            for _, row in period_df.iterrows()
            if row["Type"].strip().lower() in ("dividend", "coupon")
        )

    def period_simple_return(self, start_date, end_date, df):
        """Simple return for a period. Uses end cost basis."""
        market_gain = self.period_market_gain(start_date, end_date, df)
        income = self.period_income(start_date, end_date, df)
        total_gain = market_gain + income

        end_idx = len(self._dates) - 1
        for i, d in enumerate(self._dates):
            if d <= end_date:
                end_idx = i

        end_cost = self._cost_basis_list[end_idx]
        return calc_simple_return(total_gain, end_cost)
