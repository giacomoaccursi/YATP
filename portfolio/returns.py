"""Calcoli di rendimento: XIRR, TWR, rendimento semplice, stima tasse."""

from scipy.optimize import brentq


def calc_xirr(cashflows):
    """XIRR: rendimento annualizzato pesato per i flussi di cassa (Money-Weighted Return)."""
    if len(cashflows) < 2:
        return None
    dates, amounts = zip(*cashflows)
    first_date = min(dates)
    years = [(date - first_date).days / 365.25 for date in dates]

    def npv(rate):
        return sum(amount / (1 + rate) ** year for amount, year in zip(amounts, years))

    try:
        return brentq(npv, -0.99, 10.0)
    except ValueError:
        return None


def calc_twr(twr_txns, current_price):
    """TWR: rendimento ponderato per il tempo (Time-Weighted Return)."""
    txns = sorted(twr_txns, key=lambda x: x[0])
    if not txns:
        return None

    sub_returns = []
    prev_price = txns[0][2]

    for i in range(1, len(txns)):
        curr_price = txns[i][2]
        if prev_price > 0:
            sub_returns.append(curr_price / prev_price)
        prev_price = curr_price

    if prev_price > 0:
        sub_returns.append(current_price / prev_price)

    if not sub_returns:
        return None

    twr = 1.0
    for ratio in sub_returns:
        twr *= ratio
    return twr - 1


def calc_simple_return(pnl, cost_basis):
    """Rendimento semplice percentuale."""
    return (pnl / cost_basis) * 100 if cost_basis > 0 else 0


def calc_estimated_tax(unrealized_pnl, rate):
    """Stima tasse: aliquota applicata solo su plusvalenza positiva."""
    return max(0, unrealized_pnl) * rate


def calc_period_mwrr(cashflows, days):
    """Calcola il MWRR de-annualizzato per un periodo specifico.

    cashflows: lista di (date, amount) già completa (incluso valore iniziale e finale)
    days: durata del periodo in giorni
    """
    xirr_annual = calc_xirr(cashflows)
    if xirr_annual is None:
        return None
    years_fraction = days / 365.25
    return ((1 + xirr_annual) ** years_fraction - 1) * 100


def calc_period_twr(eval_dates, get_value_before, get_value_after):
    """Calcola il TWR tra punti di valutazione.

    eval_dates: lista di date ordinate
    get_value_before: funzione(date) -> valore del portafoglio con holdings del giorno prima
    get_value_after: funzione(date) -> valore del portafoglio con holdings di quel giorno
    """
    twr = 1.0
    prev_value = None

    for i, date in enumerate(eval_dates):
        if i == 0:
            prev_value = get_value_after(date)
            continue

        value_before = get_value_before(date)
        if prev_value is not None and prev_value > 0:
            twr *= value_before / prev_value

        prev_value = get_value_after(date)

    return twr - 1
