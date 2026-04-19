"""Portfolio engine: modular calculation of portfolio metrics.

Each method computes one metric independently.
The engine replays transactions once at init, then each method
reads from the shared state without recalculating.

Formulas are delegated to portfolio.returns — no inline math here.
"""

from portfolio.portfolio import value_holdings, get_net_new_money_between
from portfolio.returns import (
    calc_xirr, calc_simple_return, calc_period_mwrr, calc_cumulative_twr,
)


class PortfolioEngine:
    """Stateful engine that replays transactions once and exposes metric methods."""

    def __init__(self, df, price_histories, market_dates=None):
        self._price_histories = price_histories
        self._df = df
        self._replay(df, market_dates)
        self._cache_values()

    # ── Replay ──

    def _replay(self, df, market_dates):
        """Single-pass replay. Populates per-date snapshot lists."""
        tx_events = self._parse_transactions(df)

        if market_dates is not None:
            all_dates = sorted(market_dates)
        else:
            all_dates = sorted(set(e[0] for e in tx_events))

        holdings = {}
        cost_state = {}
        cumulative_realized_pnl = 0.0
        cumulative_income = 0.0
        total_invested = 0.0
        cashflows = []
        transaction_index = 0

        self._dates = []
        self._holdings_list = []
        self._prev_holdings_list = []
        self._cost_basis_list = []
        self._realized_list = []
        self._income_list = []
        self._invested_list = []
        self._has_transaction_list = []

        for date in all_dates:
            prev_holdings = dict(holdings)
            has_transaction = False

            while transaction_index < len(tx_events) and tx_events[transaction_index][0] <= date:
                has_transaction = True
                _, security, tx_type, shares, net_value = tx_events[transaction_index]

                if security not in cost_state:
                    cost_state[security] = {"shares": 0.0, "cost": 0.0}

                if tx_type == "buy":
                    holdings[security] = holdings.get(security, 0.0) + shares
                    cost_state[security]["shares"] += shares
                    cost_state[security]["cost"] += net_value
                    total_invested += net_value
                    cashflows.append((date.to_pydatetime(), -net_value))
                elif tx_type == "sell":
                    self._apply_sell(holdings, cost_state, security, shares, net_value)
                    cumulative_realized_pnl += self._last_sell_realized
                    cashflows.append((date.to_pydatetime(), net_value))
                elif tx_type in ("dividend", "coupon"):
                    cumulative_income += net_value
                    cashflows.append((date.to_pydatetime(), net_value))

                transaction_index += 1

            self._dates.append(date)
            self._holdings_list.append(dict(holdings))
            self._prev_holdings_list.append(prev_holdings)
            self._cost_basis_list.append(sum(s["cost"] for s in cost_state.values()))
            self._realized_list.append(cumulative_realized_pnl)
            self._income_list.append(cumulative_income)
            self._invested_list.append(total_invested)
            self._has_transaction_list.append(has_transaction)

        self._cashflows = cashflows

    def _apply_sell(self, holdings, cost_state, security, shares, net_value):
        """Apply a sell transaction. Sets self._last_sell_realized."""
        holdings[security] = holdings.get(security, 0.0) - shares
        self._last_sell_realized = 0.0
        if cost_state[security]["shares"] > 0:
            avg_cost_per_share = cost_state[security]["cost"] / cost_state[security]["shares"]
            cost_of_sold = avg_cost_per_share * shares
            self._last_sell_realized = net_value - cost_of_sold
            cost_state[security]["cost"] -= cost_of_sold
        cost_state[security]["shares"] -= shares
        if holdings.get(security, 0) <= 1e-9:
            holdings.pop(security, None)
            cost_state[security] = {"shares": 0.0, "cost": 0.0}

    @staticmethod
    def _parse_transactions(df):
        """Parse DataFrame into sorted list of (date, security, type, shares, net_value)."""
        events = []
        for _, row in df.iterrows():
            events.append((
                row["Date"].normalize(),
                row["Security"],
                row["Type"].strip().lower(),
                row["Shares"],
                row["Net Transaction Value"],
            ))
        events.sort(key=lambda e: e[0])
        return events

    # ── Value cache (computed once, reused by all methods) ──

    def _cache_values(self):
        """Pre-compute market values for all dates. Avoids repeated value_holdings calls."""
        self._values = []
        self._values_before = []
        for i in range(len(self._dates)):
            self._values.append(
                value_holdings(self._holdings_list[i], self._price_histories, self._dates[i])
            )
            self._values_before.append(
                value_holdings(self._prev_holdings_list[i], self._price_histories, self._dates[i])
            )

    # ── Index lookup ──

    def _index_at_or_before(self, target_date):
        """Find the last snapshot index where date <= target_date."""
        snapshot_index = None
        for i, date in enumerate(self._dates):
            if date <= target_date:
                snapshot_index = i
        return snapshot_index

    def _index_at_or_after(self, target_date):
        """Find the first snapshot index where date >= target_date."""
        for i, date in enumerate(self._dates):
            if date >= target_date:
                return i
        return None

    # ── Single-date accessors ──

    def value_at(self, index):
        """Portfolio market value at snapshot index."""
        return self._values[index]

    def cost_at(self, index):
        """Cost basis at snapshot index."""
        return self._cost_basis_list[index]

    def holdings_at(self, index=-1):
        """Holdings dict at snapshot index."""
        return dict(self._holdings_list[index])

    def cost_basis_at(self, index=-1):
        """Cost basis at snapshot index."""
        return self._cost_basis_list[index]

    def realized_pnl(self):
        """Total cumulative realized P&L."""
        return self._realized_list[-1] if self._realized_list else 0.0

    def total_income(self):
        """Total cumulative income (dividends + coupons)."""
        return self._income_list[-1] if self._income_list else 0.0

    def date_strings(self):
        """List of date strings."""
        return [d.strftime("%Y-%m-%d") for d in self._dates]

    # ── Daily series ──

    def daily_values(self):
        """Market value for each date."""
        return [round(v, 2) for v in self._values]

    def daily_costs(self):
        """Cost basis for each date."""
        return [round(c, 2) for c in self._cost_basis_list]

    def daily_unrealized(self):
        """Unrealized P&L for each date."""
        return [round(self._values[i] - self._cost_basis_list[i], 2) for i in range(len(self._dates))]

    def drawdown_series(self):
        """Drawdown % from peak for each date. Always negative or zero."""
        peak = 0.0
        series = []
        for value in self._values:
            if value > peak:
                peak = value
            drawdown_pct = ((value - peak) / peak * 100) if peak > 0 else 0.0
            series.append(round(drawdown_pct, 2))
        return series

    def shares_series(self):
        """Total shares held for each date (single-instrument use)."""
        series = []
        for holdings in self._holdings_list:
            total_shares = sum(holdings.values())
            series.append(round(total_shares, 6))
        return series

    def price_series(self):
        """Price per share for each date. Derived from value / shares.

        Meaningful when the engine runs on a single instrument.
        For multi-instrument, returns value per total shares (less useful).
        """
        series = []
        for i in range(len(self._dates)):
            total_shares = sum(self._holdings_list[i].values())
            if total_shares > 1e-9:
                series.append(round(self._values[i] / total_shares, 4))
            else:
                series.append(None)
        return series

    def avg_cost_series(self):
        """Average cost per share for each date. Derived from cost / shares.

        Meaningful when the engine runs on a single instrument.
        """
        series = []
        for i in range(len(self._dates)):
            total_shares = sum(self._holdings_list[i].values())
            if total_shares > 1e-9:
                series.append(round(self._cost_basis_list[i] / total_shares, 4))
            else:
                series.append(None)
        return series

    def simple_return_series(self):
        """Unrealized return % for each date. Carries forward when empty."""
        last_pct = 0.0
        series = []
        for i in range(len(self._dates)):
            cost = self._cost_basis_list[i]
            if cost > 0:
                last_pct = round(calc_simple_return(self._values[i] - cost, cost), 2)
            series.append(last_pct)
        return series

    def total_return_series(self):
        """Total return % (unrealized + realized + income) for each date."""
        last_pct = 0.0
        series = []
        for i in range(len(self._dates)):
            cost = self._cost_basis_list[i]
            if cost > 0:
                total_gain = (self._values[i] - cost) + self._realized_list[i] + self._income_list[i]
                last_pct = round(calc_simple_return(total_gain, cost), 2)
            series.append(last_pct)
        return series

    def cumulative_twr(self):
        """Cumulative TWR % for each date."""
        return calc_cumulative_twr(
            dates=self._dates,
            has_txn_list=self._has_transaction_list,
            value_at=lambda i: self._values[i],
            value_before_at=lambda i: self._values_before[i],
        )

    # ── Single metrics ──

    def daily_change(self):
        """Portfolio value change from previous day. Returns dict or None."""
        if len(self._dates) < 2:
            return None
        previous_value = self._values[-2]
        current_value = self._values[-1]
        if previous_value <= 0:
            return None
        change_amount = current_value - previous_value
        change_pct = calc_simple_return(change_amount, previous_value)
        return {"amount": round(change_amount, 2), "pct": round(change_pct, 2)}

    def xirr(self):
        """Annualized XIRR from all cashflows. Returns float or None."""
        if not self._cashflows or not self._dates:
            return None
        final_value = self._values[-1]
        if final_value <= 0:
            return None
        cashflows_with_final = self._cashflows + [(self._dates[-1].to_pydatetime(), final_value)]
        return calc_xirr(cashflows_with_final)

    # ── Period metrics ──

    def period_twr(self, start_date, end_date):
        """TWR for a specific period. Returns float (decimal) or None."""
        twr_series = self.cumulative_twr()
        start_idx = self._index_at_or_before(start_date)
        end_idx = self._index_at_or_before(end_date)
        if start_idx is None or end_idx is None or end_idx <= start_idx:
            return None
        start_factor = 1 + twr_series[start_idx] / 100
        end_factor = 1 + twr_series[end_idx] / 100
        if start_factor <= 0:
            return None
        return end_factor / start_factor - 1

    def period_mwrr(self, start_date, end_date, days):
        """MWRR (de-annualized XIRR) for a period. Returns float (%) or None."""
        start_idx = self._index_at_or_before(start_date)
        end_idx = self._index_at_or_before(end_date)
        if start_idx is None or end_idx is None:
            return None

        start_value = self._values[start_idx]
        end_value = self._values[end_idx]

        cashflows = []
        if start_value > 0:
            cashflows.append((self._to_datetime(start_date), -start_value))
        for cf_date, cf_amount in self._cashflows:
            if self._to_datetime(start_date) < cf_date <= self._to_datetime(end_date):
                cashflows.append((cf_date, cf_amount))
        if end_value > 0:
            cashflows.append((self._to_datetime(end_date), end_value))

        if len(cashflows) < 2:
            return None
        return calc_period_mwrr(cashflows, days)

    def period_market_gain(self, start_date, end_date):
        """Market gain for a period (excludes new money)."""
        start_idx = self._index_at_or_before(start_date)
        end_idx = self._index_at_or_before(end_date)
        if start_idx is None or end_idx is None:
            return 0
        start_value = self._values[start_idx]
        end_value = self._values[end_idx]
        net_new = get_net_new_money_between(start_date, end_date, self._df)
        return (end_value - start_value) - net_new

    def period_income(self, start_date, end_date):
        """Income (dividends + coupons) in a period."""
        total = 0.0
        for cf_date, cf_amount in self._cashflows:
            if self._to_datetime(start_date) < cf_date <= self._to_datetime(end_date):
                # Income cashflows are positive (dividends, coupons)
                # Buy cashflows are negative, sell cashflows are positive
                # We need to identify income specifically
                pass
        # Use DataFrame for accuracy
        period_df = self._df[(self._df["Date"] > start_date) & (self._df["Date"] <= end_date)]
        return sum(
            row["Net Transaction Value"]
            for _, row in period_df.iterrows()
            if row["Type"].strip().lower() in ("dividend", "coupon")
        )

    def period_simple_return(self, start_date, end_date):
        """Simple return for a period."""
        market_gain = self.period_market_gain(start_date, end_date)
        income = self.period_income(start_date, end_date)
        end_idx = self._index_at_or_before(end_date)
        if end_idx is None:
            return 0
        end_cost = self._cost_basis_list[end_idx]
        return calc_simple_return(market_gain + income, end_cost)

    # ── Convenience ──

    def full_history(self):
        """All daily metrics in one dict (portfolio-level)."""
        return {
            "dates": self.date_strings(),
            "values": self.daily_values(),
            "costs": self.daily_costs(),
            "return_pcts": self.simple_return_series(),
            "total_return_pcts": self.total_return_series(),
            "twr_pcts": self.cumulative_twr(),
            "unrealized_pnls": self.daily_unrealized(),
            "drawdown_pcts": self.drawdown_series(),
        }

    def full_instrument_history(self):
        """All daily metrics for a single instrument, including per-share data.

        Skips dates where shares held is zero (instrument not yet bought or fully sold).
        """
        dates = self.date_strings()
        prices = self.price_series()
        avg_costs = self.avg_cost_series()
        pnl = self.daily_unrealized()
        values = self.daily_values()
        costs = self.daily_costs()
        return_pcts = self.simple_return_series()
        total_return_pcts = self.total_return_series()
        twr_pcts = self.cumulative_twr()
        drawdown_pcts = self.drawdown_series()

        # Filter out dates where no shares are held
        filtered = {
            "dates": [], "prices": [], "cost_avg": [], "pnl": [],
            "values": [], "costs": [], "return_pcts": [],
            "total_return_pcts": [], "twr_pcts": [],
            "drawdown_pcts": [],
        }
        for i in range(len(dates)):
            if prices[i] is None:
                continue
            filtered["dates"].append(dates[i])
            filtered["prices"].append(prices[i])
            filtered["cost_avg"].append(avg_costs[i])
            filtered["pnl"].append(pnl[i])
            filtered["values"].append(values[i])
            filtered["costs"].append(costs[i])
            filtered["return_pcts"].append(return_pcts[i])
            filtered["total_return_pcts"].append(total_return_pcts[i])
            filtered["twr_pcts"].append(twr_pcts[i])
            filtered["drawdown_pcts"].append(drawdown_pcts[i])

        return filtered

    # ── Helpers ──

    @staticmethod
    def _to_datetime(date):
        """Convert pandas Timestamp or datetime to datetime."""
        return date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date
