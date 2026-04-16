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
_daily_change_cache = {}


def get_cached_price(ticker):
    """Fetch price with in-memory caching."""
    if ticker not in _price_cache:
        _price_cache[ticker] = fetch_current_price(ticker)
    return _price_cache[ticker]


def get_cached_daily_change(ticker):
    """Fetch daily price change percentage with caching. Returns float or None."""
    if ticker not in _daily_change_cache:
        _daily_change_cache[ticker] = _calc_daily_change(ticker)
    return _daily_change_cache[ticker]


def _calc_daily_change(ticker):
    """Calculate daily price change percentage from Yahoo Finance."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is None or len(hist) < 2:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None
        prev = closes.iloc[-2]
        curr = closes.iloc[-1]
        return ((curr - prev) / prev) * 100 if prev > 0 else None
    except Exception:
        return None


def clear_price_cache():
    """Clear the price cache to force re-fetch."""
    _price_cache.clear()
    _daily_change_cache.clear()


def load_portfolio_data(config_path, transactions_path):
    """Load and analyze the full portfolio. Returns (results, daily_changes, summary, config)."""
    config = load_config(config_path)
    instruments = config["instruments"]
    df = load_transactions(transactions_path)
    portfolio = build_portfolio(df)

    results = []
    daily_changes = {}
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue

        ticker = instrument["ticker"]
        current_price = get_cached_price(ticker)
        if current_price is None:
            continue

        capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
        analysis = analyze_instrument(data, current_price, capital_gains_rate)
        results.append(InstrumentResult(
            security=security,
            ticker=ticker,
            isin=instrument.get("isin"),
            capital_gains_rate=capital_gains_rate,
            data=data,
            analysis=analysis,
        ))
        daily_changes[security] = get_cached_daily_change(ticker)

    summary = analyze_portfolio(results, instruments) if results else None
    return results, daily_changes, summary, config


def load_rebalance_data(config_path, transactions_path):
    """Load rebalancing suggestions. Returns list of RebalanceAction."""
    results, _, _, config = load_portfolio_data(config_path, transactions_path)
    target = config.get("target_allocation")
    if not target or not results:
        return []
    return calc_rebalance(results, target, config["instruments"])


def simulate_rebalance(config_path, transactions_path, new_investment, custom_targets):
    """Simulate rebalance with optional new investment and custom targets.

    Returns list of dicts with asset_class, current_value, current_weight,
    target_weight, target_value, difference.
    """
    results, _, _, config = load_portfolio_data(config_path, transactions_path)
    instruments = config["instruments"]

    total_market = sum(r.analysis.market_value for r in results)
    total_value = total_market + new_investment

    if total_value <= 0:
        return []

    # Group current values by asset class
    current_by_class = {}
    for r in results:
        inst = instruments.get(r.security.strip(), {})
        asset_class = inst.get("type", "Other")
        current_by_class[asset_class] = current_by_class.get(asset_class, 0) + r.analysis.market_value

    all_classes = sorted(set(current_by_class.keys()) | set(custom_targets.keys()))

    actions = []
    for cls in all_classes:
        current_value = current_by_class.get(cls, 0)
        current_weight = (current_value / total_value) * 100 if total_value > 0 else 0
        target_weight = custom_targets.get(cls, 0)
        target_value = total_value * (target_weight / 100)
        actions.append({
            "asset_class": cls,
            "current_value": round(current_value, 2),
            "current_weight": round(current_weight, 2),
            "target_weight": round(target_weight, 2),
            "target_value": round(target_value, 2),
            "difference": round(target_value - current_value, 2),
        })

    return actions


def compute_net_transaction_value(tx_type, shares, quote, fees, taxes):
    """Compute net transaction value from form fields.

    Returns rounded float.
    """
    amount = shares * quote
    if tx_type == "Buy":
        return round(amount + fees, 2)
    if tx_type == "Sell":
        return round(amount - fees - taxes, 2)
    return 0.0


def load_summary_data(transactions_path):
    """Load transaction summary. Returns Summary object."""
    df = load_transactions(transactions_path)
    return build_summary(df)


def load_portfolio_daily_change(config_path, transactions_path):
    """Calculate portfolio value change from previous trading day.

    Returns dict with 'amount' (float) and 'pct' (float), or None if unavailable.
    """
    df = load_transactions(transactions_path)
    config = load_config(config_path)
    instruments = config["instruments"]

    df = df.sort_values("Date")
    if df.empty:
        return None

    today = pd.Timestamp.now().normalize()
    start = today - pd.Timedelta(days=10)

    price_histories = _fetch_all_price_histories(df, instruments, start, today)
    if not price_histories:
        return None

    all_dates = _build_date_index(price_histories, df["Date"].min().normalize(), today)
    recent = [d for d in all_dates if d <= today]
    if len(recent) < 2:
        return None

    date_today = recent[-1]
    date_prev = recent[-2]

    tx_events = _build_tx_events(df)

    # Holdings at previous close
    holdings_prev = {}
    tx_idx = 0
    for d in [d for d in all_dates if d <= date_prev]:
        tx_idx = _apply_transactions(tx_events, tx_idx, d, holdings_prev)
    val_prev = _value_holdings_at(holdings_prev, price_histories, date_prev)

    # Holdings at today's close
    holdings_today = dict(holdings_prev)
    for d in [d for d in all_dates if date_prev < d <= date_today]:
        tx_idx = _apply_transactions(tx_events, tx_idx, d, holdings_today)
    val_today = _value_holdings_at(holdings_today, price_histories, date_today)

    if val_prev <= 0:
        return None

    amount = val_today - val_prev
    pct = (amount / val_prev) * 100
    return {"amount": round(amount, 2), "pct": round(pct, 2)}


def load_instrument_names(config_path):
    """Load list of configured instrument names."""
    config = load_config(config_path)
    return list(config["instruments"].keys())


def load_portfolio_history(config_path, transactions_path):
    """Calculate daily portfolio value and cost basis from first transaction to today.

    Returns dict with 'dates', 'values', 'costs' (all lists).
    """
    df = load_transactions(transactions_path)
    config = load_config(config_path)
    instruments = config["instruments"]

    df = df.sort_values("Date")
    first_date = df["Date"].min().normalize()
    today = pd.Timestamp.now().normalize()

    price_histories = _fetch_all_price_histories(df, instruments, first_date, today)
    if not price_histories:
        return {"dates": [], "values": [], "costs": [], "return_pcts": [], "unrealized_pnls": []}

    all_dates = _build_date_index(price_histories, first_date, today)

    # Build tx events with net value for cost tracking
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

    holdings = {}
    cost_state = {}  # security -> {"shares": float, "cost": float}
    tx_idx = 0
    dates = []
    values = []
    costs = []

    for date in all_dates:
        while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
            _, security, tx_type, shares, net_value = tx_events[tx_idx]
            if security not in cost_state:
                cost_state[security] = {"shares": 0.0, "cost": 0.0}
            if tx_type == "buy":
                holdings[security] = holdings.get(security, 0.0) + shares
                cost_state[security]["shares"] += shares
                cost_state[security]["cost"] += net_value
            elif tx_type == "sell":
                holdings[security] = holdings.get(security, 0.0) - shares
                if cost_state[security]["shares"] > 0:
                    avg = cost_state[security]["cost"] / cost_state[security]["shares"]
                    cost_state[security]["cost"] -= avg * shares
                cost_state[security]["shares"] -= shares
                if holdings.get(security, 0) <= 1e-9:
                    holdings.pop(security, None)
                    cost_state[security] = {"shares": 0.0, "cost": 0.0}
            tx_idx += 1

        total = _value_holdings_at(holdings, price_histories, date)
        total_cost = sum(s["cost"] for s in cost_state.values())
        pnl_pct = ((total - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        dates.append(date.strftime("%Y-%m-%d"))
        values.append(round(total, 2))
        costs.append(round(total_cost, 2))

    # Pre-compute return_pct and unrealized_pnl for each day
    return_pcts = []
    unrealized_pnls = []
    for i in range(len(values)):
        cost = costs[i]
        return_pcts.append(round(((values[i] - cost) / cost) * 100, 2) if cost > 0 else 0.0)
        unrealized_pnls.append(round(values[i] - cost, 2))

    return {
        "dates": dates, "values": values, "costs": costs,
        "return_pcts": return_pcts, "unrealized_pnls": unrealized_pnls,
    }


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
