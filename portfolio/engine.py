"""Returns engine: centralized transaction replay and return calculations.

Single-pass replay that produces all portfolio metrics:
holdings, cost basis, realized P&L, income, cashflows, TWR sub-periods.

Used by web/data.py and portfolio/history.py instead of duplicated logic.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class DailySnapshot:
    """Portfolio state at a single date."""
    date: object
    holdings: Dict[str, float]
    cost_basis: float
    realized_pnl: float
    income: float
    total_invested: float
    has_transaction: bool
    prev_holdings: Dict[str, float]  # holdings before today's transactions


@dataclass
class ReplayResult:
    """Complete result of a transaction replay."""
    snapshots: List[DailySnapshot] = field(default_factory=list)
    cashflows: List[Tuple] = field(default_factory=list)  # (datetime, amount)


def replay_transactions(df, market_dates=None):
    """Replay all transactions in a single pass.

    Args:
        df: Sorted transactions DataFrame
        market_dates: Optional list of dates to produce snapshots for.
                      If None, produces snapshots only on transaction dates.

    Returns ReplayResult with snapshots and cashflows.
    """
    # Build transaction events: (date, security, type, shares, net_value)
    tx_events = []
    for _, row in df.iterrows():
        tx_events.append((
            row["Date"].normalize(),
            row["Security"],
            row["Type"].strip().lower(),
            row["Shares"],
            row["Net Transaction Value"],
        ))
    tx_events.sort(key=lambda e: e[0])

    # State
    holdings = {}
    cost_state = {}  # security -> {"shares": float, "cost": float}
    cumulative_realized = 0.0
    cumulative_income = 0.0
    total_invested = 0.0
    cashflows = []

    # Determine which dates to snapshot
    if market_dates is not None:
        all_dates = sorted(market_dates)
    else:
        all_dates = sorted(set(e[0] for e in tx_events))

    tx_idx = 0
    snapshots = []

    for date in all_dates:
        prev_holdings = dict(holdings)
        has_txn = False

        while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
            has_txn = True
            _, security, tx_type, shares, net_value = tx_events[tx_idx]

            if security not in cost_state:
                cost_state[security] = {"shares": 0.0, "cost": 0.0}

            if tx_type == "buy":
                holdings[security] = holdings.get(security, 0.0) + shares
                cost_state[security]["shares"] += shares
                cost_state[security]["cost"] += net_value
                total_invested += net_value
                cashflows.append((date.to_pydatetime(), -net_value))

            elif tx_type == "sell":
                holdings[security] = holdings.get(security, 0.0) - shares
                if cost_state[security]["shares"] > 0:
                    avg = cost_state[security]["cost"] / cost_state[security]["shares"]
                    cost_of_sold = avg * shares
                    cumulative_realized += net_value - cost_of_sold
                    cost_state[security]["cost"] -= cost_of_sold
                cost_state[security]["shares"] -= shares
                if holdings.get(security, 0) <= 1e-9:
                    holdings.pop(security, None)
                    cost_state[security] = {"shares": 0.0, "cost": 0.0}
                cashflows.append((date.to_pydatetime(), net_value))

            elif tx_type in ("dividend", "coupon"):
                cumulative_income += net_value
                cashflows.append((date.to_pydatetime(), net_value))

            tx_idx += 1

        total_cost = sum(s["cost"] for s in cost_state.values())

        snapshots.append(DailySnapshot(
            date=date,
            holdings=dict(holdings),
            cost_basis=total_cost,
            realized_pnl=cumulative_realized,
            income=cumulative_income,
            total_invested=total_invested,
            has_transaction=has_txn,
            prev_holdings=prev_holdings,
        ))

    return ReplayResult(snapshots=snapshots, cashflows=cashflows)


def compute_daily_metrics(replay, price_histories, value_fn):
    """Compute daily portfolio metrics from replay snapshots.

    Args:
        replay: ReplayResult from replay_transactions
        price_histories: dict of security -> price Series
        value_fn: function(holdings, price_histories, date) -> float

    Returns dict with dates, values, costs, return_pcts, total_return_pcts,
    twr_pcts, unrealized_pnls.
    """
    dates = []
    values = []
    costs = []
    return_pcts = []
    total_return_pcts = []
    twr_daily = []
    unrealized_pnls = []

    last_return_pct = 0.0
    last_total_return_pct = 0.0
    cumulative_twr = 1.0
    prev_after_txn_value = None

    for snap in replay.snapshots:
        total = value_fn(snap.holdings, price_histories, snap.date)

        # TWR
        if snap.has_transaction:
            value_before = value_fn(snap.prev_holdings, price_histories, snap.date)
            if prev_after_txn_value is not None and prev_after_txn_value > 0 and value_before > 0:
                cumulative_twr *= value_before / prev_after_txn_value
            prev_after_txn_value = total if total > 0 else None
            twr_daily.append(round((cumulative_twr - 1) * 100, 2))
        elif prev_after_txn_value is not None and prev_after_txn_value > 0 and total > 0:
            running = cumulative_twr * (total / prev_after_txn_value)
            twr_daily.append(round((running - 1) * 100, 2))
        else:
            twr_daily.append(twr_daily[-1] if twr_daily else 0.0)

        # Returns
        unrealized = total - snap.cost_basis
        if snap.cost_basis > 0:
            last_return_pct = round((unrealized / snap.cost_basis) * 100, 2)
            total_gain = unrealized + snap.realized_pnl + snap.income
            last_total_return_pct = round((total_gain / snap.cost_basis) * 100, 2)

        dates.append(snap.date.strftime("%Y-%m-%d"))
        values.append(round(total, 2))
        costs.append(round(snap.cost_basis, 2))
        unrealized_pnls.append(round(unrealized, 2))
        return_pcts.append(last_return_pct)
        total_return_pcts.append(last_total_return_pct)

    return {
        "dates": dates,
        "values": values,
        "costs": costs,
        "return_pcts": return_pcts,
        "total_return_pcts": total_return_pcts,
        "twr_pcts": twr_daily,
        "unrealized_pnls": unrealized_pnls,
    }
