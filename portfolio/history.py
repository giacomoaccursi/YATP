"""Historical portfolio performance: 1 month, 6 months, 1 year, since inception."""

import pandas as pd
from datetime import timedelta

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


def build_history(df, instruments, price_histories=None):
    """Calculate portfolio performance for each period.

    If price_histories is provided, reuses them instead of fetching again.
    """
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

    # Pre-compute holdings at all unique transaction dates (single replay)
    holdings_cache = _build_holdings_cache(df)

    results = []
    for label, days in PERIODS:
        period_start, period_days = _resolve_period(today, first_date, days)
        if period_start is None:
            results.append(PeriodPerformance(period=label, available=False))
            continue

        result = _analyze_period(
            label, period_start, today, period_days, df, price_histories, holdings_cache
        )
        results.append(result)

    return results


def _build_holdings_cache(df):
    """Replay transactions once and cache holdings at every transaction date.

    Returns dict of date -> {security: shares}.
    Single O(n) pass instead of O(n) per date lookup.
    """
    df = df.sort_values("Date")
    holdings = {}  # security -> shares
    cache = {}     # date -> snapshot of holdings

    for _, row in df.iterrows():
        date = row["Date"]
        tx_type = row["Type"].strip().lower()
        security = row["Security"]
        shares = row["Shares"]

        if tx_type == "buy":
            holdings[security] = holdings.get(security, 0.0) + shares
        elif tx_type == "sell":
            holdings[security] = holdings.get(security, 0.0) - shares
            if holdings.get(security, 0) <= 1e-9:
                holdings.pop(security, None)

        # Snapshot after processing this date's transactions
        cache[date] = {s: sh for s, sh in holdings.items() if sh > 1e-9}

    return cache


def _get_holdings_from_cache(date, df, cache):
    """Get holdings at a date using the pre-computed cache.

    If the exact date is in the cache, use it.
    Otherwise find the latest cached date before this date.
    """
    if date in cache:
        return dict(cache[date])

    # Find latest date in cache that is <= date
    cached_dates = sorted(cache.keys())
    best = None
    for d in cached_dates:
        if d <= date:
            best = d
        else:
            break

    if best is not None:
        return dict(cache[best])
    return {}


def _resolve_period(today, first_date, days):
    """Determine period start date and duration."""
    if days is not None:
        period_start = today - timedelta(days=days)
        if period_start < first_date:
            return None, None
        return period_start, days
    else:
        return first_date, (today - first_date).days


def _analyze_period(label, period_start, today, days, df, price_histories, holdings_cache):
    """Analyze a single period: calculate all returns."""
    start_holdings = _get_holdings_from_cache(period_start, df, holdings_cache)
    end_holdings = _get_holdings_from_cache(today, df, holdings_cache)

    start_value = value_holdings(start_holdings, price_histories, period_start)
    end_value = value_holdings(end_holdings, price_histories, today)

    if end_value <= 0:
        return PeriodPerformance(period=label, available=False)

    # Market gain (price appreciation only)
    net_new_money = get_net_new_money_between(period_start, today, df)
    market_gain = (end_value - start_value) - net_new_money

    # Income in period (dividends + coupons)
    period_df = df[(df["Date"] > period_start) & (df["Date"] <= today)]
    period_income = sum(
        row["Net Transaction Value"]
        for _, row in period_df.iterrows()
        if row["Type"].strip().lower() in ("dividend", "coupon")
    )

    # Simple return: total gain (market + income) / cost basis
    total_gain = market_gain + period_income
    cost_basis = get_cost_basis_at(period_start, df) + net_new_money
    simple_return = calc_simple_return(total_gain, cost_basis)

    # MWRR (de-annualized XIRR)
    cashflows = []
    if start_value > 0:
        cashflows.append((period_start.to_pydatetime(), -start_value))
    cashflows.extend(get_cashflows_between(period_start, today, df))
    if end_value > 0:
        cashflows.append((today.to_pydatetime(), end_value))
    mwrr = calc_period_mwrr(cashflows, days) if len(cashflows) >= 2 else None

    # TWR — use cached holdings instead of replaying per date
    period_txn_dates = sorted(set(
        df[(df["Date"] > period_start) & (df["Date"] <= today)]["Date"].unique()
    ))
    eval_dates = [period_start] + [d for d in period_txn_dates if d != today] + [today]
    seen = set()
    unique_eval = []
    for d in eval_dates:
        if d not in seen:
            seen.add(d)
            unique_eval.append(d)
    eval_dates = unique_eval

    def get_value_before(date):
        """Portfolio value just before transactions on this date."""
        prev_day = date - timedelta(days=1)
        holdings = _get_holdings_from_cache(prev_day, df, holdings_cache)
        return value_holdings(holdings, price_histories, date)

    def get_value_after(date):
        """Portfolio value after transactions on this date."""
        holdings = _get_holdings_from_cache(date, df, holdings_cache)
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
