"""Portfolio construction from transactions (progressive average cost)."""

from portfolio.models import InstrumentData


def build_portfolio(df):
    """Process transactions chronologically for each instrument."""
    portfolio = {}

    for security, group in df.groupby("Security"):
        group = group.sort_values("Date")

        shares_held = 0.0
        total_cost = 0.0
        realized_pnl = 0.0
        total_income = 0.0
        cashflows = []

        for _, row in group.iterrows():
            tx_type = row["Type"].strip().lower()
            shares = row["Shares"]
            net_value = row["Net Transaction Value"]
            date = row["Date"].to_pydatetime()

            if tx_type == "buy":
                accrued = row.get("Accrued Interest", 0) or 0
                total_cost += net_value - accrued
                shares_held += shares
                cashflows.append((date, -net_value))
            elif tx_type == "sell":
                accrued = row.get("Accrued Interest", 0) or 0
                sell_proceeds_clean = net_value - accrued
                avg_cost_at_sell = total_cost / shares_held if shares_held > 0 else 0
                cost_of_sold = avg_cost_at_sell * shares
                realized_pnl += sell_proceeds_clean - cost_of_sold
                total_cost -= cost_of_sold
                shares_held -= shares
                cashflows.append((date, net_value))
            elif tx_type in ("dividend", "coupon"):
                total_income += net_value
                cashflows.append((date, net_value))
            else:
                print(f"⚠️  Unknown transaction type: '{tx_type}' for {security} on {date}")
                continue

        avg_cost = total_cost / shares_held if shares_held > 0 else 0

        portfolio[security] = InstrumentData(
            shares_held=shares_held,
            avg_cost_per_share=avg_cost,
            cost_basis=total_cost,
            realized_pnl=realized_pnl,
            total_income=total_income,
            cashflows=cashflows,
        )

    return portfolio


# ── Snapshot functions: portfolio state at a given date ──

def _get_transactions_until(date, transactions_df):
    """Filter transactions up to a given date, grouped by security."""
    return transactions_df[transactions_df["Date"] <= date]


def _get_transactions_between(start_date, end_date, transactions_df):
    """Filter transactions between two dates (exclusive start, inclusive end)."""
    return transactions_df[
        (transactions_df["Date"] > start_date) & (transactions_df["Date"] <= end_date)
    ]


def _replay_transactions(past_df):
    """Replay transactions to get shares and cost per security.

    Returns dict of security -> {"shares": float, "cost": float}
    """
    state = {}
    for security, group in past_df.groupby("Security"):
        shares = 0.0
        cost = 0.0
        for _, row in group.sort_values("Date").iterrows():
            tx_type = row["Type"].strip().lower()
            if tx_type == "buy":
                shares += row["Shares"]
                cost += row["Net Transaction Value"]
            elif tx_type == "sell":
                avg = cost / shares if shares > 0 else 0
                cost -= avg * row["Shares"]
                shares -= row["Shares"]
            # dividend/coupon don't affect shares or cost
        state[security] = {"shares": shares, "cost": cost}
    return state


def get_holdings_at(date, transactions_df):
    """Get shares held per instrument at a given date."""
    past_df = _get_transactions_until(date, transactions_df)
    state = _replay_transactions(past_df)
    return {sec: s["shares"] for sec, s in state.items() if s["shares"] > 0}


def get_cost_basis_at(date, transactions_df):
    """Get portfolio cost basis at a given date."""
    past_df = _get_transactions_until(date, transactions_df)
    state = _replay_transactions(past_df)
    return sum(s["cost"] for s in state.values())


def value_holdings(holdings, price_histories, date):
    """Calculate total market value of holdings at a given date."""
    total = 0.0
    for security, shares in holdings.items():
        if security not in price_histories:
            continue
        prices = price_histories[security]
        available = prices[prices.index <= date]
        if available.empty:
            continue
        total += shares * available.iloc[-1]
    return total


def get_cashflows_between(start_date, end_date, transactions_df):
    """Extract cashflows (for XIRR) between two dates."""
    period_df = _get_transactions_between(start_date, end_date, transactions_df)
    cashflows = []
    for _, row in period_df.iterrows():
        tx_type = row["Type"].strip().lower()
        date = row["Date"].to_pydatetime()
        if tx_type == "buy":
            cashflows.append((date, -row["Net Transaction Value"]))
        elif tx_type in ("sell", "dividend", "coupon"):
            cashflows.append((date, row["Net Transaction Value"]))
    return cashflows


def get_net_new_money_between(start_date, end_date, transactions_df):
    """Calculate net new money invested between two dates (buys - sells)."""
    period_df = _get_transactions_between(start_date, end_date, transactions_df)
    buys = sum(row["Net Transaction Value"]
               for _, row in period_df.iterrows()
               if row["Type"].strip().lower() == "buy")
    sells = sum(row["Net Transaction Value"]
                for _, row in period_df.iterrows()
                if row["Type"].strip().lower() == "sell")
    return buys - sells  # dividends/coupons are not new money
