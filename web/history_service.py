"""History service: portfolio history, instrument history, daily change."""

import pandas as pd

from portfolio.loader import load_config, load_transactions
from portfolio.engine import PortfolioEngine
from portfolio.history import build_history
from web.portfolio_service import load_common
from web.cache import get_cached_price_history


def load_portfolio_history(config_path, transactions_path, start_date=None, end_date=None):
    """Calculate daily portfolio value, cost basis, return % and unrealized P&L."""
    _, _, df, price_histories, first_date, today = load_common(config_path, transactions_path)

    empty_response = {"dates": [], "values": [], "costs": [], "return_pcts": [], "total_return_pcts": [], "twr_pcts": [], "drawdown_pcts": []}
    if df.empty or not price_histories:
        return empty_response

    all_dates = _build_date_index(price_histories, first_date, today)
    engine = PortfolioEngine(df, price_histories, market_dates=all_dates)
    return engine.full_history(start_date=start_date, end_date=end_date)


def load_portfolio_daily_change(config_path, transactions_path):
    """Calculate portfolio value change from previous trading day."""
    _, _, df, price_histories, first_date, today = load_common(config_path, transactions_path)

    if df.empty or not price_histories:
        return None

    all_dates = _build_date_index(price_histories, first_date, today)
    recent = [d for d in all_dates if d <= today]
    if len(recent) < 2:
        return None

    engine = PortfolioEngine(df, price_histories, market_dates=recent[-2:])
    return engine.daily_change()


def load_instrument_history(config_path, transactions_path, security):
    """Calculate all metrics for a single instrument using the engine.

    Returns the same structure as portfolio history plus per-share data (prices, cost_avg).
    """
    config = load_config(config_path)
    instrument = config["instruments"].get(security)
    if not instrument:
        return None

    df = load_transactions(transactions_path)
    df = df.sort_values("Date")
    instrument_df = df[df["Security"].str.strip() == security.strip()]

    empty_response = _empty_instrument_response()
    if instrument_df.empty:
        return empty_response

    first_date = instrument_df["Date"].min().normalize()
    today = pd.Timestamp.now().normalize()

    prices = get_cached_price_history(instrument["ticker"], first_date, today, instrument_type=instrument.get("type"), isin=instrument.get("isin"))
    if prices is None:
        return empty_response

    price_histories = {security: prices}
    all_dates = sorted(prices.index.normalize().unique())
    all_dates = [date for date in all_dates if date <= today]

    engine = PortfolioEngine(instrument_df, price_histories, market_dates=all_dates)
    result = engine.full_instrument_history()

    # Add buy transaction dates and amounts for DCA visualization
    buy_transactions = instrument_df[instrument_df["Type"].str.strip().str.lower() == "buy"]
    result["buy_dates"] = [date.strftime("%Y-%m-%d") for date in buy_transactions["Date"]]
    result["buy_amounts"] = [round(row["Shares"] * (row["Net Transaction Value"] / row["Shares"] if row["Shares"] > 0 else 0), 2) for _, row in buy_transactions.iterrows()]
    result["buy_prices"] = [round(row["Net Transaction Value"] / row["Shares"], 4) if row["Shares"] > 0 else 0 for _, row in buy_transactions.iterrows()]

    return result


def _empty_instrument_response():
    """Return an empty instrument history response."""
    return {
        "dates": [], "prices": [], "cost_avg": [], "pnl": [],
        "values": [], "costs": [], "return_pcts": [],
        "total_return_pcts": [], "twr_pcts": [],
        "drawdown_pcts": [],
    }


def load_performance_periods(config_path, transactions_path):
    """Calculate performance metrics for standard periods."""
    _, instruments, df, price_histories, _, _ = load_common(config_path, transactions_path)
    if not price_histories:
        return None
    return build_history(df, instruments, price_histories)


def load_filtered_history(config_path, transactions_path, securities, start_date=None, end_date=None):
    """Calculate daily metrics for a subset of instruments using the engine."""
    _, instruments, df, price_histories, first_date, today = load_common(config_path, transactions_path)

    empty_response = {"dates": [], "values": [], "costs": [], "return_pcts": [], "total_return_pcts": [], "twr_pcts": [], "drawdown_pcts": []}

    filtered_df = df[df["Security"].str.strip().isin(securities)]
    if filtered_df.empty:
        return empty_response

    filtered_prices = {sec: ph for sec, ph in price_histories.items() if sec.strip() in securities}
    if not filtered_prices:
        return empty_response

    first_date = filtered_df["Date"].min().normalize()
    all_dates = _build_date_index(filtered_prices, first_date, today)
    engine = PortfolioEngine(filtered_df, filtered_prices, market_dates=all_dates)
    return engine.full_history(start_date=start_date, end_date=end_date)


def load_filtered_performance_periods(config_path, transactions_path, securities):
    """Calculate performance metrics for standard periods for a subset of instruments."""
    _, instruments, df, price_histories, _, _ = load_common(config_path, transactions_path)

    filtered_df = df[df["Security"].str.strip().isin(securities)]
    if filtered_df.empty:
        return None

    filtered_prices = {sec: ph for sec, ph in price_histories.items() if sec.strip() in securities}
    if not filtered_prices:
        return None

    filtered_instruments = {sec: instrument_config for sec, instrument_config in instruments.items() if sec.strip() in securities}
    return build_history(filtered_df, filtered_instruments, filtered_prices)


def load_instrument_performance_periods(config_path, transactions_path, security):
    """Calculate performance metrics for standard periods for a single instrument."""
    config = load_config(config_path)
    instrument = config["instruments"].get(security)
    if not instrument:
        return None

    df = load_transactions(transactions_path)
    df = df.sort_values("Date")
    instrument_df = df[df["Security"].str.strip() == security.strip()]
    if instrument_df.empty:
        return None

    first_date = instrument_df["Date"].min().normalize()
    today = pd.Timestamp.now().normalize()

    prices = get_cached_price_history(instrument["ticker"], first_date, today, instrument_type=instrument.get("type"), isin=instrument.get("isin"))
    if prices is None:
        return None

    price_histories = {security: prices}
    return build_history(instrument_df, {security: instrument}, price_histories)


def _build_date_index(price_histories, first_date, today):
    """Build a sorted list of unique market dates from all price histories."""
    all_dates = set()
    for prices in price_histories.values():
        all_dates.update(prices.index.normalize())
    return sorted(date for date in all_dates if first_date <= date <= today)
