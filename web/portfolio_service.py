"""Portfolio service: loads and analyzes the full portfolio."""

import pandas as pd

from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.models import InstrumentResult
from web.cache import get_cached_price, get_cached_daily_change, get_cached_price_history, get_common_cache, set_common_cache


def load_common(config_path, transactions_path):
    """Load config, transactions, and price histories. Cached between requests until invalidated."""
    cached = get_common_cache()
    if cached is not None:
        return cached

    config = load_config(config_path)
    instruments = config["instruments"]
    df = load_transactions(transactions_path)
    df = df.sort_values("Date")

    first_date = df["Date"].min().normalize() if not df.empty else pd.Timestamp.now().normalize()
    today = pd.Timestamp.now().normalize()

    price_histories = {}
    for security in df["Security"].unique():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue
        prices = get_cached_price_history(instrument["ticker"], first_date, today, instrument_type=instrument.get("type"), isin=instrument.get("isin"))
        if prices is not None:
            price_histories[security] = prices

    result = (config, instruments, df, price_histories, first_date, today)
    set_common_cache(result)
    return result


def load_portfolio_data(config_path, transactions_path):
    """Load and analyze the full portfolio.

    Returns (results, daily_changes, summary, config, failed_instruments).
    """
    config, instruments, df, _, _, _ = load_common(config_path, transactions_path)
    portfolio = build_portfolio(df)

    results = []
    daily_changes = {}
    failed_instruments = []

    for security, instrument_data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue

        ticker = instrument["ticker"]
        current_price = get_cached_price(ticker, isin=instrument.get("isin"), instrument_type=instrument.get("type"))
        if current_price is None:
            if instrument_data.shares_held > 0:
                failed_instruments.append(security)
            continue

        capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
        analysis = analyze_instrument(instrument_data, current_price, capital_gains_rate)
        results.append(InstrumentResult(
            security=security,
            ticker=ticker,
            isin=instrument.get("isin"),
            capital_gains_rate=capital_gains_rate,
            data=instrument_data,
            analysis=analysis,
        ))
        daily_changes[security] = get_cached_daily_change(ticker, instrument_type=instrument.get("type"))

    summary = analyze_portfolio(results, instruments) if results else None
    return results, daily_changes, summary, config, failed_instruments


def load_offline_summary(config_path, transactions_path):
    """Load portfolio summary from CSV only (no market data needed)."""
    config = load_config(config_path)
    df = load_transactions(transactions_path)

    if df.empty:
        return {"cost_basis": 0, "transaction_count": 0, "total_income": 0, "instruments_count": 0}

    portfolio = build_portfolio(df)
    cost_basis = sum(instrument_data.cost_basis for instrument_data in portfolio.values())
    total_income = sum(instrument_data.total_income for instrument_data in portfolio.values())
    instruments_count = sum(1 for instrument_data in portfolio.values() if instrument_data.shares_held > 0)

    return {
        "cost_basis": round(cost_basis, 2),
        "transaction_count": len(df),
        "total_income": round(total_income, 2),
        "instruments_count": instruments_count,
    }
