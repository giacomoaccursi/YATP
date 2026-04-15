"""Portfolio construction from transactions (progressive average cost)."""


def build_portfolio(df):
    """Process transactions chronologically for each instrument."""
    portfolio = {}

    for security, group in df.groupby("Security"):
        group = group.sort_values("Date")

        shares_held = 0.0
        total_cost = 0.0
        realized_pnl = 0.0
        cashflows = []
        twr_txns = []

        for _, row in group.iterrows():
            tx_type = row["Type"].strip().lower()
            shares = row["Shares"]
            net_value = row["Net Transaction Value"]
            quote = row["Quote"]
            date = row["Date"].to_pydatetime()

            if tx_type == "buy":
                total_cost += net_value
                shares_held += shares
                cashflows.append((date, -net_value))
            elif tx_type == "sell":
                avg_cost_at_sell = total_cost / shares_held if shares_held > 0 else 0
                cost_of_sold = avg_cost_at_sell * shares
                realized_pnl += net_value - cost_of_sold
                total_cost -= cost_of_sold
                shares_held -= shares
                cashflows.append((date, net_value))
            else:
                print(f"⚠️  Unknown transaction type: '{tx_type}' for {security} on {date}")
                continue

            twr_txns.append((date, tx_type, quote))

        avg_cost = total_cost / shares_held if shares_held > 0 else 0

        portfolio[security] = {
            "shares_held": shares_held,
            "avg_cost_per_share": avg_cost,
            "cost_basis": total_cost,
            "realized_pnl": realized_pnl,
            "cashflows": cashflows,
            "twr_txns": twr_txns,
        }

    return portfolio


def get_holdings_at(date, transactions_df):
    """Get shares held per instrument at a given date."""
    holdings = {}
    for security, group in transactions_df.groupby("Security"):
        past = group[group["Date"] <= date].sort_values("Date")
        shares = 0.0
        for _, row in past.iterrows():
            tx_type = row["Type"].strip().lower()
            if tx_type == "buy":
                shares += row["Shares"]
            elif tx_type == "sell":
                shares -= row["Shares"]
        if shares > 0:
            holdings[security] = shares
    return holdings


def get_cost_basis_at(date, transactions_df):
    """Get portfolio cost basis at a given date."""
    total_cost = 0.0
    for security, group in transactions_df.groupby("Security"):
        past = group[group["Date"] <= date].sort_values("Date")
        shares = 0.0
        cost = 0.0
        for _, row in past.iterrows():
            tx_type = row["Type"].strip().lower()
            if tx_type == "buy":
                shares += row["Shares"]
                cost += row["Net Transaction Value"]
            elif tx_type == "sell":
                avg = cost / shares if shares > 0 else 0
                cost -= avg * row["Shares"]
                shares -= row["Shares"]
        total_cost += cost
    return total_cost


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
    period_txns = transactions_df[
        (transactions_df["Date"] > start_date) & (transactions_df["Date"] <= end_date)
    ]
    cashflows = []
    for _, row in period_txns.iterrows():
        tx_type = row["Type"].strip().lower()
        date = row["Date"].to_pydatetime()
        if tx_type == "buy":
            cashflows.append((date, -row["Net Transaction Value"]))
        elif tx_type == "sell":
            cashflows.append((date, row["Net Transaction Value"]))
    return cashflows


def get_net_new_money_between(start_date, end_date, transactions_df):
    """Calculate net new money invested between two dates (buys - sells)."""
    period_txns = transactions_df[
        (transactions_df["Date"] > start_date) & (transactions_df["Date"] <= end_date)
    ]
    buys = sum(row["Net Transaction Value"]
               for _, row in period_txns.iterrows()
               if row["Type"].strip().lower() == "buy")
    sells = sum(row["Net Transaction Value"]
                for _, row in period_txns.iterrows()
                if row["Type"].strip().lower() == "sell")
    return buys - sells
