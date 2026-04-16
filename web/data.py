"""Web data layer: builds portfolio data for the API. Handles price caching."""

import pandas as pd

from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.market import fetch_current_price, fetch_price_history
from portfolio.models import InstrumentResult
from portfolio.summary import build_summary
from portfolio.rebalance import calc_rebalance
from portfolio.history import build_history

# In-memory price cache (persists while server is running)
_price_cache = {}


def get_cached_price(ticker):
    """Fetch price with in-memory caching."""
    if ticker not in _price_cache:
        _price_cache[ticker] = fetch_current_price(ticker)
    return _price_cache[ticker]


def clear_price_cache():
    """Clear the price cache to force re-fetch."""
    _price_cache.clear()


def load_portfolio_data(config_path, transactions_path):
    """Load and analyze the full portfolio. Returns (results, summary, config)."""
    config = load_config(config_path)
    instruments = config["instruments"]
    df = load_transactions(transactions_path)
    portfolio = build_portfolio(df)

    results = []
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue

        current_price = get_cached_price(instrument["ticker"])
        if current_price is None:
            continue

        capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
        analysis = analyze_instrument(data, current_price, capital_gains_rate)
        results.append(InstrumentResult(
            security=security,
            ticker=instrument["ticker"],
            isin=instrument.get("isin"),
            capital_gains_rate=capital_gains_rate,
            data=data,
            analysis=analysis,
        ))

    summary = analyze_portfolio(results, instruments) if results else None
    return results, summary, config


def load_rebalance_data(config_path, transactions_path):
    """Load rebalancing suggestions. Returns list of RebalanceAction."""
    results, _, config = load_portfolio_data(config_path, transactions_path)
    target = config.get("target_allocation")
    if not target or not results:
        return []
    return calc_rebalance(results, target, config["instruments"])


def load_summary_data(transactions_path):
    """Load transaction summary. Returns Summary object."""
    df = load_transactions(transactions_path)
    return build_summary(df)


def load_instrument_names(config_path):
    """Load list of configured instrument names."""
    config = load_config(config_path)
    return list(config["instruments"].keys())


def load_portfolio_history(config_path, transactions_path):
    """Calculate daily portfolio value from first transaction to today.

    Returns dict with 'dates' (list of str) and 'values' (list of float).
    """
    df = load_transactions(transactions_path)
    config = load_config(config_path)
    instruments = config["instruments"]

    df = df.sort_values("Date")
    first_date = df["Date"].min().normalize()
    today = pd.Timestamp.now().normalize()

    price_histories = _fetch_all_price_histories(df, instruments, first_date, today)
    if not price_histories:
        return {"dates": [], "values": []}

    all_dates = _build_date_index(price_histories, first_date, today)
    tx_events = _build_tx_events(df)

    holdings = {}
    tx_idx = 0
    dates = []
    values = []

    for date in all_dates:
        tx_idx = _apply_transactions(tx_events, tx_idx, date, holdings)
        total = _value_holdings_at(holdings, price_histories, date)
        dates.append(date.strftime("%Y-%m-%d"))
        values.append(round(total, 2))

    return {"dates": dates, "values": values}


def load_instrument_history(config_path, transactions_path, security):
    """Calculate price, avg cost and P&L history for a single instrument.

    Returns dict with 'dates', 'prices', 'cost_avg', 'pnl' (all lists),
    or None if instrument not found.
    """
    config = load_config(config_path)
    inst = config["instruments"].get(security)
    if not inst:
        return None

    df = load_transactions(transactions_path)
    df = df.sort_values("Date")
    inst_df = df[df["Security"].str.strip() == security.strip()]

    empty = {"dates": [], "prices": [], "cost_avg": [], "pnl": []}
    if inst_df.empty:
        return empty

    first_date = inst_df["Date"].min().normalize()
    today = pd.Timestamp.now().normalize()

    prices = fetch_price_history(inst["ticker"], first_date, today)
    if prices is None:
        return empty

    tx_events = []
    for _, row in inst_df.iterrows():
        tx_events.append((
            row["Date"].normalize(),
            row["Type"].strip().lower(),
            row["Shares"],
            row["Net Transaction Value"],
        ))
    tx_events.sort(key=lambda e: e[0])

    all_dates = sorted(prices.index.normalize().unique())
    all_dates = [d for d in all_dates if first_date <= d <= today]

    tx_idx = 0
    shares = 0.0
    total_cost = 0.0
    dates = []
    price_values = []
    cost_avg_values = []
    pnl_values = []

    for date in all_dates:
        while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
            _, tx_type, tx_shares, net_value = tx_events[tx_idx]
            if tx_type == "buy":
                shares += tx_shares
                total_cost += net_value
            elif tx_type == "sell":
                if shares > 0:
                    avg = total_cost / shares
                    total_cost -= avg * tx_shares
                shares -= tx_shares
                if shares <= 1e-9:
                    shares = 0.0
                    total_cost = 0.0
            tx_idx += 1

        if shares <= 1e-9:
            continue

        available = prices[prices.index <= date]
        if available.empty:
            continue

        price = available.iloc[-1]
        avg_cost = total_cost / shares if shares > 0 else 0
        market_val = shares * price
        unrealized = market_val - total_cost

        dates.append(date.strftime("%Y-%m-%d"))
        price_values.append(round(price, 4))
        cost_avg_values.append(round(avg_cost, 4))
        pnl_values.append(round(unrealized, 2))

    return {
        "dates": dates,
        "prices": price_values,
        "cost_avg": cost_avg_values,
        "pnl": pnl_values,
    }


def load_performance_periods(config_path, transactions_path):
    """Calculate performance metrics for standard periods. Returns list of PeriodPerformance."""
    df = load_transactions(transactions_path)
    config = load_config(config_path)
    return build_history(df, config["instruments"])


# ── Private helpers ──

def _fetch_all_price_histories(df, instruments, start_date, end_date):
    """Fetch historical prices for all instruments in the DataFrame."""
    price_histories = {}
    for security in df["Security"].unique():
        inst = instruments.get(security.strip())
        if not inst:
            continue
        prices = fetch_price_history(inst["ticker"], start_date, end_date)
        if prices is not None:
            price_histories[security] = prices
    return price_histories


def _build_date_index(price_histories, first_date, today):
    """Build a sorted list of unique market dates from all price histories."""
    all_dates = set()
    for prices in price_histories.values():
        all_dates.update(prices.index.normalize())
    return sorted(d for d in all_dates if first_date <= d <= today)


def _build_tx_events(df):
    """Build sorted list of (date, security, type, shares) from transactions."""
    tx_events = []
    for _, row in df.iterrows():
        tx_events.append((
            row["Date"].normalize(),
            row["Security"],
            row["Type"].strip().lower(),
            row["Shares"],
        ))
    tx_events.sort(key=lambda e: e[0])
    return tx_events


def _apply_transactions(tx_events, tx_idx, date, holdings):
    """Apply all transactions up to and including date. Mutates holdings. Returns new tx_idx."""
    while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
        _, security, tx_type, shares = tx_events[tx_idx]
        if tx_type == "buy":
            holdings[security] = holdings.get(security, 0.0) + shares
        elif tx_type == "sell":
            holdings[security] = holdings.get(security, 0.0) - shares
            if holdings[security] <= 1e-9:
                holdings.pop(security, None)
        tx_idx += 1
    return tx_idx


def _value_holdings_at(holdings, price_histories, date):
    """Calculate total market value of holdings at a given date."""
    total = 0.0
    for security, shares in holdings.items():
        if security not in price_histories:
            continue
        prices = price_histories[security]
        available = prices[prices.index <= date]
        if not available.empty:
            total += shares * available.iloc[-1]
    return total
