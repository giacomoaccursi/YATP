"""Performance storica del portafoglio: 1 mese, 6 mesi, 1 anno, dall'inizio."""

import pandas as pd
from datetime import timedelta

from portfolio.market import fetch_price_history
from portfolio.portfolio import (
    get_holdings_at, get_cost_basis_at, value_holdings,
    get_cashflows_between, get_net_new_money_between,
)
from portfolio.returns import calc_simple_return, calc_period_mwrr, calc_period_twr


PERIODS = [
    ("1 mese", 30),
    ("6 mesi", 182),
    ("1 anno", 365),
    ("Dall'inizio", None),
]


def build_history(df, instruments):
    """Calcola la performance del portafoglio per ogni periodo."""
    df = df.sort_values("Date")
    first_date = df["Date"].min()
    today = pd.Timestamp.now().normalize()

    # Scarica prezzi storici
    price_histories = _fetch_all_histories(df, instruments, first_date, today)
    if not price_histories:
        return None

    results = []
    for label, days in PERIODS:
        period_start, period_days = _resolve_period(today, first_date, days)
        if period_start is None:
            results.append({"period": label, "available": False})
            continue

        result = _analyze_period(label, period_start, today, period_days, df, price_histories)
        results.append(result)

    return results


def _fetch_all_histories(df, instruments, start_date, end_date):
    """Scarica i prezzi storici per tutti gli strumenti nel portafoglio."""
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
    """Determina la data di inizio e la durata del periodo."""
    if days is not None:
        period_start = today - timedelta(days=days)
        if period_start < first_date:
            return None, None
        return period_start, days
    else:
        return first_date, (today - first_date).days


def _analyze_period(label, period_start, today, days, df, price_histories):
    """Analizza un singolo periodo: calcola tutti i rendimenti."""
    # Valori del portafoglio
    start_value = value_holdings(
        get_holdings_at(period_start, df), price_histories, period_start
    )
    end_value = value_holdings(
        get_holdings_at(today, df), price_histories, today
    )

    # Guadagno di mercato
    net_new_money = get_net_new_money_between(period_start, today, df)
    market_gain = (end_value - start_value) - net_new_money

    # Rendimento semplice
    cost_basis = get_cost_basis_at(period_start, df) + net_new_money
    simple_return = calc_simple_return(market_gain, cost_basis)

    # MWRR (via XIRR de-annualizzato)
    cashflows = []
    if start_value > 0:
        cashflows.append((period_start.to_pydatetime(), -start_value))
    cashflows.extend(get_cashflows_between(period_start, today, df))
    if end_value > 0:
        cashflows.append((today.to_pydatetime(), end_value))
    mwrr = calc_period_mwrr(cashflows, days) if len(cashflows) >= 2 else None

    # TWR
    period_txn_dates = sorted(
        df[(df["Date"] > period_start) & (df["Date"] <= today)]["Date"].unique()
    )
    eval_dates = [period_start] + list(period_txn_dates) + [today]

    def get_value_before(date):
        holdings = get_holdings_at(date - timedelta(days=1), df)
        return value_holdings(holdings, price_histories, date)

    def get_value_after(date):
        holdings = get_holdings_at(date, df)
        return value_holdings(holdings, price_histories, date)

    twr = calc_period_twr(eval_dates, get_value_before, get_value_after)

    return {
        "period": label,
        "available": True,
        "past_date": period_start,
        "market_gain": market_gain,
        "simple_return": simple_return,
        "twr": twr,
        "mwrr": mwrr,
    }
