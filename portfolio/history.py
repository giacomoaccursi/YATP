"""Historical portfolio performance: 1 month, 6 months, 1 year, since inception."""

import pandas as pd
from datetime import timedelta

from portfolio.market import fetch_price_history
from portfolio.portfolio import (
    get_holdings_at, get_cost_basis_at, value_holdings,
    get_cashflows_between, get_net_new_money_between,
)
from portfolio.returns import calc_simple_return, calc_period_mwrr, calc_period_twr
from portfolio.models import PeriodPerformance


PERIODS = [
    ("1 month", 30),
    ("6 months", 182),
    ("1 year", 365),
    ("Since start", None),
]


def build_history(df, instruments):
    """Calculate portfolio performance for each period."""
    df = df.sort_values("Date")
    first_date = df["Date"].min()
    today = pd.Timestamp.now().normalize()

    price_histories = _fetch_all_histories(df, instruments, first_date, today)
    if not price_histories:
        return None

    results = []
    for label, days in PERIODS:
        period_start, period_days = _resolve_period(today, first_date, days)
        if period_start is None:
            results.append(PeriodPerformance(period=label, available=False))
            continue

        result = _analyze_period(label, period_start, today, period_days, df, price_histories)
        results.append(result)

    return results


def _fetch_all_histories(df, instruments, start_date, end_date):
    """Fetch historical prices for all instruments in the portfolio."""
    price_histories = {}
    for security in df["Security"].unique():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue
        prices = fetch_price_history(instrument["ticker"], start_date, end_date)
        if prices is not None:
            price_histories[security] = prices
    return price_histories


def _resolve_period(today, first_date, days):
    """Determine period start date and duration."""
    if days is not None:
        period_start = today - timedelta(days=days)
        if period_start < first_date:
            return None, None
        return period_start, days
    else:
        return first_date, (today - first_date).days


def _analyze_period(label, period_start, today, days, df, price_histories):
    """Analyze a single period: calculate all returns."""
    start_value = value_holdings(
        get_holdings_at(period_start, df), price_histories, period_start
    )
    end_value = value_holdings(
        get_holdings_at(today, df), price_histories, today
    )

    # If we can't value the portfolio, mark as unavailable
    if end_value <= 0:
        return PeriodPerformance(period=label, available=False)

    # Market gain
    net_new_money = get_net_new_money_between(period_start, today, df)
    market_gain = (end_value - start_value) - net_new_money

    # Simple return
    cost_basis = get_cost_basis_at(period_start, df) + net_new_money
    simple_return = calc_simple_return(market_gain, cost_basis)

    # MWRR (de-annualized XIRR)
    cashflows = []
    if start_value > 0:
        cashflows.append((period_start.to_pydatetime(), -start_value))
    cashflows.extend(get_cashflows_between(period_start, today, df))
    if end_value > 0:
        cashflows.append((today.to_pydatetime(), end_value))
    mwrr = calc_period_mwrr(cashflows, days) if len(cashflows) >= 2 else None

    # TWR
    period_txn_dates = sorted(set(
        df[(df["Date"] > period_start) & (df["Date"] <= today)]["Date"].unique()
    ))
    # Remove today from txn dates if present (it's the end point, not a sub-period boundary)
    eval_dates = [period_start] + [d for d in period_txn_dates if d != today] + [today]
    # Remove duplicates while preserving order
    seen = set()
    unique_eval = []
    for d in eval_dates:
        if d not in seen:
            seen.add(d)
            unique_eval.append(d)
    eval_dates = unique_eval

    def get_value_before(date):
        """Portfolio value just before transactions on this date.

        Uses previous day's holdings (before any transaction on this date)
        valued at this date's prices (the price doesn't change due to our transaction).
        """
        prev_day = date - timedelta(days=1)
        holdings = get_holdings_at(prev_day, df)
        return value_holdings(holdings, price_histories, date)

    def get_value_after(date):
        """Portfolio value after transactions on this date, at this date's price."""
        holdings = get_holdings_at(date, df)
        return value_holdings(holdings, price_histories, date)

    twr = calc_period_twr(eval_dates, get_value_before, get_value_after)

    return PeriodPerformance(
        period=label,
        available=True,
        past_date=period_start,
        market_gain=market_gain,
        simple_return=simple_return,
        twr=twr,
        mwrr=mwrr,
    )
