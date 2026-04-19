"""History service: portfolio history, instrument history, daily change."""

import pandas as pd

from portfolio.loader import load_config, load_transactions
from portfolio.engine import PortfolioEngine
from portfolio.history import build_history
from web.portfolio_service import load_common
from web.cache import get_cached_price_history


def load_portfolio_history(config_path, transactions_path):
    """Calculate daily portfolio value, cost basis, return % and unrealized P&L."""
    _, _, df, price_histories, first_date, today = load_common(config_path, transactions_path)

    empty = {"dates": [], "values": [], "costs": [], "return_pcts": [], "total_return_pcts": [], "twr_pcts": [], "unrealized_pnls": []}
    if df.empty or not price_histories:
        return empty

    all_dates = _build_date_index(price_histories, first_date, today)
    engine = PortfolioEngine(df, price_histories, market_dates=all_dates)
    return engine.full_history()


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

    # Handle transactions after last available price
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
        if not prices.empty:
            last_price = prices.iloc[-1]
            last_date = prices.index[-1].normalize()
            avg_cost = total_cost / shares if shares > 0 else 0
            unrealized = shares * last_price - total_cost
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
    _, instruments, df, price_histories, _, _ = load_common(config_path, transactions_path)
    if not price_histories:
        return None
    return build_history(df, instruments, price_histories)


def _build_date_index(price_histories, first_date, today):
    """Build a sorted list of unique market dates from all price histories."""
    all_dates = set()
    for prices in price_histories.values():
        all_dates.update(prices.index.normalize())
    return sorted(d for d in all_dates if first_date <= d <= today)
