"""Return calculations: XIRR, TWR, simple return, tax estimation."""

from scipy.optimize import brentq


def calc_xirr(cashflows):
    """XIRR: annualized money-weighted return."""
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
    """TWR: time-weighted return."""
    txns = sorted(twr_txns, key=lambda x: x[0])
    # Filter out entries with zero price (coupons, dividends)
    txns = [t for t in txns if t[2] > 0]
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
    for sub_period_return in sub_returns:
        twr *= sub_period_return
    return twr - 1


def calc_simple_return(pnl, cost_basis):
    """Simple return as a percentage."""
    return (pnl / cost_basis) * 100 if cost_basis > 0 else 0


def calc_estimated_tax(unrealized_pnl, rate):
    """Estimated tax: rate applied only on positive gains."""
    return max(0, unrealized_pnl) * rate


def calc_period_mwrr(cashflows, days):
    """De-annualized MWRR for a specific period.

    cashflows: list of (date, amount) including start value and end value
    days: period duration in days
    """
    xirr_annual = calc_xirr(cashflows)
    if xirr_annual is None:
        return None
    years_fraction = days / 365.25
    return ((1 + xirr_annual) ** years_fraction - 1) * 100


def calc_period_twr(eval_dates, get_value_before, get_value_after):
    """TWR between evaluation points.

    eval_dates: sorted list of dates
    get_value_before: function(date) -> portfolio value with previous day's holdings
    get_value_after: function(date) -> portfolio value with that day's holdings
    """
    if len(eval_dates) < 2:
        return None

    twr = 1.0
    prev_value = get_value_after(eval_dates[0])

    if prev_value <= 0:
        return None

    for date in eval_dates[1:]:
        value_before = get_value_before(date)
        if prev_value > 0:
            twr *= value_before / prev_value
        prev_value = get_value_after(date)

    return twr - 1


def calc_cumulative_twr(dates, has_txn_list, value_at, value_before_at):
    """Compute cumulative TWR % for each date.

    Sub-period chaining: at each transaction date, close the sub-period
    with value_before / prev_value_after, then start a new sub-period.
    Between transactions, show running TWR including partial period.

    Args:
        dates: list of dates
        has_txn_list: list of bool, True if date has a transaction
        value_at: function(index) -> portfolio value after transactions
        value_before_at: function(index) -> portfolio value before transactions (prev holdings, today's prices)

    Returns list of TWR % values, one per date.
    """
    cumulative = 1.0
    prev_after = None
    twr_series = []

    for i in range(len(dates)):
        current_value = value_at(i)

        if has_txn_list[i]:
            value_before = value_before_at(i)
            if prev_after is not None and prev_after > 0 and value_before > 0:
                cumulative *= value_before / prev_after
            prev_after = current_value if current_value > 0 else None
            twr_series.append(round((cumulative - 1) * 100, 2))
        elif prev_after is not None and prev_after > 0 and current_value > 0:
            running = cumulative * (current_value / prev_after)
            twr_series.append(round((running - 1) * 100, 2))
        else:
            twr_series.append(twr_series[-1] if twr_series else 0.0)

    return twr_series
