"""Web data layer: builds portfolio data for the API. Handles price caching."""

import pandas as pd

from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.market import fetch_current_price, fetch_price_history, clear_bond_price_cache
from portfolio.models import InstrumentResult
from portfolio.summary import build_summary
from portfolio.rebalance import calc_rebalance
from portfolio.history import build_history
from portfolio.engine import replay_transactions, compute_daily_metrics
from portfolio.portfolio import value_holdings

# ── In-memory caches (persist while server is running) ──

_price_cache = {}
_daily_change_cache = {}
_price_history_cache = {}
_price_fetch_time = None


def get_cached_price(ticker, isin=None):
    """Fetch current price with in-memory caching."""
    global _price_fetch_time
    if ticker not in _price_cache:
        _price_cache[ticker] = fetch_current_price(ticker, isin=isin)
        if _price_fetch_time is None:
            from datetime import datetime
            _price_fetch_time = datetime.now().strftime("%H:%M")
    return _price_cache[ticker]


def get_price_fetch_time():
    """Return the time when prices were last fetched, or None."""
    return _price_fetch_time


def get_cached_daily_change(ticker):
    """Fetch daily price change percentage with caching."""
    if ticker not in _daily_change_cache:
        _daily_change_cache[ticker] = _calc_daily_change(ticker)
    return _daily_change_cache[ticker]


def get_cached_price_history(ticker, start_date, end_date):
    """Fetch price history with in-memory caching. Keyed by ticker."""
    if ticker not in _price_history_cache:
        _price_history_cache[ticker] = fetch_price_history(ticker, start_date, end_date)
    return _price_history_cache[ticker]


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
    """Clear all price caches to force re-fetch."""
    global _price_fetch_time
    _price_cache.clear()
    _daily_change_cache.clear()
    _price_history_cache.clear()
    _price_fetch_time = None
    clear_bond_price_cache()


# ── Core data loading ──

def _load_common(config_path, transactions_path):
    """Load config, transactions, and price histories. Shared by multiple functions."""
    config = load_config(config_path)
    instruments = config["instruments"]
    df = load_transactions(transactions_path)
    df = df.sort_values("Date")

    first_date = df["Date"].min().normalize() if not df.empty else pd.Timestamp.now().normalize()
    today = pd.Timestamp.now().normalize()

    price_histories = {}
    for security in df["Security"].unique():
        inst = instruments.get(security.strip())
        if not inst:
            continue
        prices = get_cached_price_history(inst["ticker"], first_date, today)
        if prices is not None:
            price_histories[security] = prices

    return config, instruments, df, price_histories, first_date, today


def load_offline_summary(config_path, transactions_path):
    """Load portfolio summary from CSV only (no market data needed).

    Returns dict with cost_basis, transaction_count, total_income, instruments_count.
    Always succeeds if the CSV is readable.
    """
    config = load_config(config_path)
    instruments = config["instruments"]
    df = load_transactions(transactions_path)

    if df.empty:
        return {"cost_basis": 0, "transaction_count": 0, "total_income": 0, "instruments_count": 0}

    portfolio = build_portfolio(df)
    cost_basis = sum(d.cost_basis for d in portfolio.values())
    total_income = sum(d.total_income for d in portfolio.values())
    instruments_count = sum(1 for d in portfolio.values() if d.shares_held > 0)

    return {
        "cost_basis": round(cost_basis, 2),
        "transaction_count": len(df),
        "total_income": round(total_income, 2),
        "instruments_count": instruments_count,
    }


def load_portfolio_data(config_path, transactions_path):
    """Load and analyze the full portfolio. Returns (results, daily_changes, summary, config)."""
    config, instruments, df, _, _, _ = _load_common(config_path, transactions_path)
    portfolio = build_portfolio(df)

    results = []
    daily_changes = {}
    failed_instruments = []
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue

        ticker = instrument["ticker"]
        current_price = get_cached_price(ticker, isin=instrument.get("isin"))
        if current_price is None:
            if data.shares_held > 0:
                failed_instruments.append(security)
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
    return results, daily_changes, summary, config, failed_instruments


def load_rebalance_data(config_path, transactions_path):
    """Load rebalancing suggestions. Returns list of RebalanceAction."""
    results, _, _, config, _ = load_portfolio_data(config_path, transactions_path)
    target = config.get("target_allocation")
    if not target or not results:
        return []
    return calc_rebalance(results, target, config["instruments"])


def simulate_rebalance(config_path, transactions_path, new_investment, custom_targets):
    """Simulate rebalance with optional new investment and custom targets."""
    results, _, _, config, _ = load_portfolio_data(config_path, transactions_path)
    instruments = config["instruments"]

    total_market = sum(r.analysis.market_value for r in results)
    total_value = total_market + new_investment

    if total_value <= 0:
        return []

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
    """Compute net transaction value from form fields."""
    amount = shares * quote
    if tx_type == "Buy":
        return round(amount + fees, 2)
    if tx_type == "Sell":
        return round(amount - fees - taxes, 2)
    return 0.0


def simulate_sell(config_path, transactions_path, security, shares_to_sell):
    """Simulate selling shares of an instrument.

    Uses the full transaction history to compute correct avg cost,
    then calculates projected gain, taxes and net proceeds.

    Returns dict or None if instrument not found / not enough shares.
    """
    config = load_config(config_path)
    instrument = config["instruments"].get(security)
    if not instrument:
        return None

    df = load_transactions(transactions_path)
    portfolio = build_portfolio(df)
    data = portfolio.get(security)
    if not data or data.shares_held < shares_to_sell or shares_to_sell <= 0:
        return None

    current_price = get_cached_price(instrument["ticker"], isin=instrument.get("isin"))
    if current_price is None:
        return None

    capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
    gross_proceeds = shares_to_sell * current_price
    cost_of_sold = shares_to_sell * data.avg_cost_per_share
    gain = gross_proceeds - cost_of_sold
    tax = max(0, gain) * capital_gains_rate
    net_proceeds = gross_proceeds - tax

    return {
        "security": security,
        "shares_to_sell": round(shares_to_sell, 6),
        "shares_held": round(data.shares_held, 6),
        "current_price": round(current_price, 4),
        "avg_cost_per_share": round(data.avg_cost_per_share, 4),
        "gross_proceeds": round(gross_proceeds, 2),
        "cost_of_sold": round(cost_of_sold, 2),
        "gain": round(gain, 2),
        "capital_gains_rate": capital_gains_rate,
        "estimated_tax": round(tax, 2),
        "net_proceeds": round(net_proceeds, 2),
    }


def load_summary_data(transactions_path):
    """Load transaction summary. Returns Summary object."""
    df = load_transactions(transactions_path)
    return build_summary(df)


def load_instrument_names(config_path):
    """Load list of configured instrument names."""
    config = load_config(config_path)
    return list(config["instruments"].keys())


def add_instrument_to_config(config_path, security, ticker, instrument_type, capital_gains_rate, isin=None):
    """Add a new instrument to the config file."""
    import json
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


def load_portfolio_daily_change(config_path, transactions_path):
    """Calculate portfolio value change from previous trading day."""
    _, _, df, price_histories, first_date, today = _load_common(config_path, transactions_path)

    if df.empty or not price_histories:
        return None

    all_dates = _build_date_index(price_histories, first_date, today)
    recent = [d for d in all_dates if d <= today]
    if len(recent) < 2:
        return None

    date_today = recent[-1]
    date_prev = recent[-2]

    tx_events = _build_tx_events(df)

    holdings_prev = {}
    tx_idx = 0
    for d in [d for d in all_dates if d <= date_prev]:
        tx_idx = _apply_transactions(tx_events, tx_idx, d, holdings_prev)
    val_prev = value_holdings(holdings_prev, price_histories, date_prev)

    holdings_today = dict(holdings_prev)
    for d in [d for d in all_dates if date_prev < d <= date_today]:
        tx_idx = _apply_transactions(tx_events, tx_idx, d, holdings_today)
    val_today = value_holdings(holdings_today, price_histories, date_today)

    if val_prev <= 0:
        return None

    amount = val_today - val_prev
    pct = (amount / val_prev) * 100
    return {"amount": round(amount, 2), "pct": round(pct, 2)}


def load_portfolio_history(config_path, transactions_path):
    """Calculate daily portfolio value, cost basis, return % and unrealized P&L."""
    _, _, df, price_histories, first_date, today = _load_common(config_path, transactions_path)

    empty = {"dates": [], "values": [], "costs": [], "return_pcts": [], "total_return_pcts": [], "twr_pcts": [], "unrealized_pnls": []}
    if df.empty or not price_histories:
        return empty

    all_dates = _build_date_index(price_histories, first_date, today)
    replay = replay_transactions(df, market_dates=all_dates)
    return compute_daily_metrics(replay, price_histories, value_holdings)


def load_instrument_history(config_path, transactions_path, security):
    """Calculate price, avg cost and P&L history for a single instrument."""
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

    prices = get_cached_price_history(inst["ticker"], first_date, today)
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
    all_dates = [d for d in all_dates if d <= today]

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

    # Handle transactions after the last available price date (e.g. today, market closed)
    while tx_idx < len(tx_events):
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

    if shares > 1e-9 and not dates:
        # No chart data yet — use last available price
        if not prices.empty:
            last_price = prices.iloc[-1]
            last_date = prices.index[-1].normalize()
            avg_cost = total_cost / shares if shares > 0 else 0
            market_val = shares * last_price
            unrealized = market_val - total_cost
            dates.append(last_date.strftime("%Y-%m-%d"))
            price_values.append(round(float(last_price), 4))
            cost_avg_values.append(round(avg_cost, 4))
            pnl_values.append(round(unrealized, 2))

    return {
        "dates": dates,
        "prices": price_values,
        "cost_avg": cost_avg_values,
        "pnl": pnl_values,
    }


def load_performance_periods(config_path, transactions_path):
    """Calculate performance metrics for standard periods."""
    _, instruments, df, price_histories, _, _ = _load_common(config_path, transactions_path)
    if not price_histories:
        return None
    return build_history(df, instruments, price_histories)


# ── Private helpers ──

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

