"""Serialization helpers: convert dataclasses to API response dicts."""

import math


def safe_float(value, decimals=2):
    """Safely convert a value to a rounded float. Returns 0 for NaN/None/invalid."""
    try:
        val = float(value)
        return round(val, decimals) if not math.isnan(val) else 0
    except (ValueError, TypeError):
        return 0


def instrument_to_dict(result, daily_change=None):
    """Convert InstrumentResult to API response dict."""
    return {
        "security": result.security,
        "ticker": result.ticker,
        "isin": result.isin,
        "shares_held": round(result.data.shares_held, 4),
        "avg_cost_per_share": round(result.data.avg_cost_per_share, 2),
        "cost_basis": round(result.data.cost_basis, 2),
        "market_value": round(result.analysis.market_value, 2),
        "unrealized_pnl": round(result.analysis.unrealized_pnl, 2),
        "realized_pnl": round(result.data.realized_pnl, 2),
        "total_pnl": round(result.analysis.total_pnl, 2),
        "simple_return": round(result.analysis.simple_return, 2),
        "twr": round(result.analysis.twr * 100, 2) if result.analysis.twr is not None else None,
        "xirr": round(result.analysis.xirr * 100, 2) if result.analysis.xirr is not None else None,
        "estimated_tax": round(result.analysis.estimated_tax, 2),
        "net_after_tax": round(result.analysis.net_after_tax, 2),
        "total_income": round(result.analysis.total_income, 2),
        "capital_gains_rate": result.capital_gains_rate,
        "daily_change": round(daily_change, 2) if daily_change is not None else None,
    }


def summary_to_dict(summary):
    """Convert PortfolioSummary to API response dict."""
    return {
        "cost": round(summary.cost, 2),
        "market_value": round(summary.market_value, 2),
        "unrealized": round(summary.unrealized, 2),
        "realized": round(summary.realized, 2),
        "total_pnl": round(summary.total_pnl, 2),
        "simple_return": round(summary.simple_return, 2),
        "xirr": round(summary.xirr * 100, 2) if summary.xirr is not None else None,
        "tax": round(summary.tax, 2),
        "net_after_tax": round(summary.net_after_tax, 2),
        "allocations": {k: round(v, 1) for k, v in summary.allocations.items()},
        "allocations_by_class": {k: round(v, 1) for k, v in summary.allocations_by_asset_class.items()},
    }


def transaction_row_to_dict(idx, row):
    """Convert a CSV row to API response dict."""
    return {
        "index": int(idx),
        "date": row["Date"].strftime("%Y-%m-%d"),
        "type": row["Type"].strip(),
        "security": row["Security"].strip(),
        "shares": safe_float(row["Shares"], 6),
        "quote": safe_float(row["Quote"]),
        "fees": safe_float(row.get("Fees", 0)),
        "taxes": safe_float(row.get("Taxes", 0)),
        "accrued_interest": safe_float(row.get("Accrued Interest", 0)),
        "net_transaction_value": safe_float(row["Net Transaction Value"]),
    }


def instrument_summary_to_dict(inst):
    """Convert InstrumentSummary to API response dict."""
    return {
        "security": inst.security,
        "total_buys": inst.total_buys,
        "total_sells": inst.total_sells,
        "total_invested": round(inst.total_invested, 2),
        "total_sold": round(inst.total_sold, 2),
        "total_income": round(inst.total_income, 2),
        "shares_held": round(inst.shares_held, 4),
        "avg_cost_per_share": round(inst.avg_cost_per_share, 2),
    }


def rebalance_to_dict(action):
    """Convert RebalanceAction to API response dict."""
    return {
        "asset_class": action.asset_class,
        "current_weight": round(action.current_weight, 2),
        "target_weight": round(action.target_weight, 2),
        "current_value": round(action.current_value, 2),
        "target_value": round(action.target_value, 2),
        "difference": round(action.difference, 2),
    }


def period_to_dict(period):
    """Convert PeriodPerformance to API response dict."""
    if not period.available:
        return {
            "period": period.period,
            "available": False,
            "market_gain": None,
            "simple_return": None,
            "twr": None,
            "mwrr": None,
        }
    return {
        "period": period.period,
        "available": True,
        "market_gain": round(period.market_gain, 2),
        "simple_return": round(period.simple_return, 2),
        "twr": round(period.twr * 100, 2) if period.twr is not None else None,
        "mwrr": round(period.mwrr, 2) if period.mwrr is not None else None,
    }
