"""JSON report export."""

import json
import math
from datetime import datetime
from portfolio.models import InstrumentResult, PortfolioSummary, PeriodPerformance


def _safe_round(value, decimals=2):
    """Round a value, returning None if NaN or None."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(value, decimals)


def export_json(path, results, summary, history, tax_info, rebalance_actions=None):
    """Save the full report to a JSON file."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "tax_info": tax_info,
        "instruments": [_instrument_to_dict(r) for r in results],
        "portfolio": _summary_to_dict(summary),
        "history": _history_to_dict(history),
    }

    if rebalance_actions is not None:
        report["rebalance"] = _rebalance_to_dict(rebalance_actions)

    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def _instrument_to_dict(result: InstrumentResult):
    """Convert an InstrumentResult to a JSON-serializable dict."""
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
        "yield_on_cost": round(result.analysis.yield_on_cost, 2),
        "total_return": round(result.analysis.total_return, 2),
        "capital_gains_rate": result.capital_gains_rate,
    }


def _summary_to_dict(summary: PortfolioSummary):
    """Convert a PortfolioSummary to a JSON-serializable dict."""
    if not summary:
        return None
    return {
        "cost_basis": round(summary.cost, 2),
        "market_value": round(summary.market_value, 2),
        "unrealized_pnl": round(summary.unrealized, 2),
        "realized_pnl": round(summary.realized, 2),
        "total_pnl": round(summary.total_pnl, 2),
        "simple_return": round(summary.simple_return, 2),
        "xirr": round(summary.xirr * 100, 2) if summary.xirr is not None else None,
        "estimated_tax": round(summary.tax, 2),
        "net_after_tax": round(summary.net_after_tax, 2),
        "allocations": summary.allocations,
        "allocations_by_asset_class": summary.allocations_by_asset_class,
    }


def _history_to_dict(history):
    """Convert history list to JSON-serializable dicts."""
    if not history:
        return None
    periods = []
    for entry in history:
        if not entry.available:
            periods.append({"period": entry.period, "available": False})
        else:
            periods.append({
                "period": entry.period,
                "available": True,
                "from_date": entry.past_date.strftime("%Y-%m-%d"),
                "market_gain": _safe_round(entry.market_gain),
                "simple_return": _safe_round(entry.simple_return),
                "twr": _safe_round(entry.twr * 100) if entry.twr is not None else None,
                "mwrr": _safe_round(entry.mwrr),
            })
    return periods


def _rebalance_to_dict(actions):
    """Convert rebalance actions to JSON-serializable dicts."""
    return [{
        "asset_class": action.asset_class,
        "current_weight": round(action.current_weight, 2),
        "target_weight": round(action.target_weight, 2),
        "current_value": round(action.current_value, 2),
        "target_value": round(action.target_value, 2),
        "difference": round(action.difference, 2),
    } for action in actions]
