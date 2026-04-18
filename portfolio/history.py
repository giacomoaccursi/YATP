"""Historical portfolio performance: 1 month, 6 months, 1 year, since inception.

All return calculations delegated to PortfolioEngine.
"""

import pandas as pd
from datetime import timedelta

from portfolio.engine import PortfolioEngine
from portfolio.models import PeriodPerformance


PERIODS = [
    ("1 month", 30),
    ("6 months", 182),
    ("1 year", 365),
    ("Since start", None),
]


def build_history(df, instruments, price_histories=None):
    """Calculate portfolio performance for each period using the engine."""
    df = df.sort_values("Date")
    first_date = df["Date"].min()
    today = pd.Timestamp.now().normalize()

    if price_histories is None:
        from portfolio.market import fetch_price_history
        price_histories = {}
        for security in df["Security"].unique():
            instrument = instruments.get(security.strip())
            if not instrument:
                continue
            prices = fetch_price_history(instrument["ticker"], first_date, today)
            if prices is not None:
                price_histories[security] = prices

    if not price_histories:
        return None

    # Build date index from price histories
    all_dates = set()
    for prices in price_histories.values():
        all_dates.update(prices.index.normalize())
    all_dates = sorted(d for d in all_dates if first_date <= d <= today)

    engine = PortfolioEngine(df, price_histories, market_dates=all_dates)

    results = []
    for label, days in PERIODS:
        period_start, period_days = _resolve_period(today, first_date, days)
        if period_start is None:
            results.append(PeriodPerformance(period=label, available=False))
            continue

        result = _analyze_period(engine, label, period_start, today, period_days, df)
        results.append(result)

    return results


def _resolve_period(today, first_date, days):
    """Determine period start date and duration."""
    if days is not None:
        period_start = today - timedelta(days=days)
        if period_start < first_date:
            return None, None
        return period_start, days
    else:
        return first_date, (today - first_date).days


def _analyze_period(engine, label, period_start, today, days, df):
    """Analyze a single period using the engine."""
    market_gain = engine.period_market_gain(period_start, today, df)
    simple_return = engine.period_simple_return(period_start, today, df)
    twr = engine.period_twr(period_start, today)
    mwrr = engine.period_mwrr(period_start, today, days)

    # Check if we have valid data
    end_idx = len(engine._dates) - 1
    for i, d in enumerate(engine._dates):
        if d <= today:
            end_idx = i
    end_value = engine._value_at(end_idx)

    if end_value <= 0:
        return PeriodPerformance(period=label, available=False)

    return PeriodPerformance(
        period=label,
        available=True,
        past_date=period_start,
        market_gain=market_gain,
        simple_return=simple_return,
        twr=twr,
        mwrr=mwrr,
    )
