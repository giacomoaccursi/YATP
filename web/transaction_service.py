"""Transaction service: net value, sell simulation, instrument management."""

import json

from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.summary import build_summary
from web.cache import get_cached_price


def compute_net_transaction_value(tx_type, shares, quote, fees, taxes):
    """Compute net transaction value from form fields."""
    amount = shares * quote
    if tx_type == "Buy":
        return round(amount + fees, 2)
    if tx_type == "Sell":
        return round(amount - fees - taxes, 2)
    return 0.0


def simulate_sell(config_path, transactions_path, security, shares_to_sell):
    """Simulate selling shares of an instrument."""
    config = load_config(config_path)
    instrument = config["instruments"].get(security)
    if not instrument:
        return None

    df = load_transactions(transactions_path)
    portfolio = build_portfolio(df)
    instrument_data = portfolio.get(security)
    if not instrument_data or instrument_data.shares_held < shares_to_sell or shares_to_sell <= 0:
        return None

    current_price = get_cached_price(instrument["ticker"], isin=instrument.get("isin"), instrument_type=instrument.get("type"))
    if current_price is None:
        return None

    capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
    gross_proceeds = shares_to_sell * current_price
    # avg_cost_per_share already excludes accrued interest (clean price basis)
    cost_of_sold = shares_to_sell * instrument_data.avg_cost_per_share
    gain = gross_proceeds - cost_of_sold
    tax = max(0, gain) * capital_gains_rate
    net_proceeds = gross_proceeds - tax

    return {
        "security": security,
        "shares_to_sell": round(shares_to_sell, 6),
        "shares_held": round(instrument_data.shares_held, 6),
        "current_price": round(current_price, 4),
        "avg_cost_per_share": round(instrument_data.avg_cost_per_share, 4),
        "gross_proceeds": round(gross_proceeds, 2),
        "cost_of_sold": round(cost_of_sold, 2),
        "gain": round(gain, 2),
        "capital_gains_rate": capital_gains_rate,
        "estimated_tax": round(tax, 2),
        "net_proceeds": round(net_proceeds, 2),
    }


def load_summary_data(transactions_path):
    """Load transaction summary."""
    df = load_transactions(transactions_path)
    return build_summary(df)


def load_income_history(transactions_path):
    """Load monthly income (dividends + coupons) grouped by month.

    Returns list of {month: "YYYY-MM", amount: float, details: [{security, type, amount}]}.
    """
    df = load_transactions(transactions_path)
    income_df = df[df["Type"].str.strip().str.lower().isin(["dividend", "coupon"])]

    if income_df.empty:
        return []

    income_df = income_df.copy()
    income_df["Month"] = income_df["Date"].dt.to_period("M").astype(str)

    months = {}
    for _, row in income_df.iterrows():
        month = row["Month"]
        if month not in months:
            months[month] = {"month": month, "amount": 0.0, "details": []}
        months[month]["amount"] += row["Net Transaction Value"]
        months[month]["details"].append({
            "security": row["Security"].strip(),
            "type": row["Type"].strip(),
            "amount": round(row["Net Transaction Value"], 2),
            "date": row["Date"].strftime("%Y-%m-%d"),
        })

    result = sorted(months.values(), key=lambda entry: entry["month"])
    for entry in result:
        entry["amount"] = round(entry["amount"], 2)
    return result


def load_instrument_names(config_path):
    """Load list of configured instrument names with their types."""
    config = load_config(config_path)
    return {name: instrument_config.get("type", "ETF") for name, instrument_config in config["instruments"].items()}


def add_instrument_to_config(config_path, security, ticker, instrument_type, capital_gains_rate, isin=None):
    """Add a new instrument to the config file."""
    with open(config_path, "r") as f:
        config = json.load(f)

    if security in config.get("instruments", {}):
        return False

    if "instruments" not in config:
        config["instruments"] = {}

    instrument = {
        "ticker": ticker,
        "type": instrument_type,
        "capital_gains_rate": capital_gains_rate,
    }
    if isin:
        instrument["isin"] = isin

    config["instruments"][security] = instrument

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return True
