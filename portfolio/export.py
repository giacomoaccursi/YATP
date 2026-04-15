"""JSON report export."""

import json
from datetime import datetime


def export_json(path, results, summary, history, tax_info):
    """Save the full report to a JSON file."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "tax_info": tax_info,
        "instruments": _build_instruments_section(results),
        "portfolio": _build_portfolio_section(summary),
        "history": _build_history_section(history),
    }

    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def _build_instruments_section(results):
    """Build the instruments section for export."""
    instruments = []
    for result in results:
        analysis = result["analysis"]
        data = result["data"]
        instruments.append({
            "security": result["security"],
            "ticker": result["ticker"],
            "isin": result.get("isin"),
            "shares_held": round(data["shares_held"], 4),
            "avg_cost_per_share": round(data["avg_cost_per_share"], 2),
            "cost_basis": round(data["cost_basis"], 2),
            "market_value": round(analysis["market_value"], 2),
            "unrealized_pnl": round(analysis["unrealized_pnl"], 2),
            "realized_pnl": round(data["realized_pnl"], 2),
            "total_pnl": round(analysis["total_pnl"], 2),
            "simple_return": round(analysis["simple_return"], 2),
            "twr": round(analysis["twr"] * 100, 2) if analysis["twr"] is not None else None,
            "xirr": round(analysis["xirr"] * 100, 2) if analysis["xirr"] is not None else None,
            "estimated_tax": round(analysis["estimated_tax"], 2),
            "net_after_tax": round(analysis["net_after_tax"], 2),
            "capital_gains_rate": result["capital_gains_rate"],
        })
    return instruments


def _build_portfolio_section(summary):
    """Build the total portfolio section for export."""
    if not summary:
        return None
    return {
        "cost_basis": round(summary["cost"], 2),
        "market_value": round(summary["market_value"], 2),
        "unrealized_pnl": round(summary["unrealized"], 2),
        "realized_pnl": round(summary["realized"], 2),
        "total_pnl": round(summary["total_pnl"], 2),
        "simple_return": round(summary["simple_return"], 2),
        "xirr": round(summary["xirr"] * 100, 2) if summary.get("xirr") is not None else None,
        "estimated_tax": round(summary["tax"], 2),
        "net_after_tax": round(summary["net_after_tax"], 2),
        "allocations": summary.get("allocations"),
        "allocations_by_asset_class": summary.get("allocations_by_asset_class"),
    }


def _build_history_section(history):
    """Build the historical performance section for export."""
    if not history:
        return None
    periods = []
    for entry in history:
        if not entry["available"]:
            periods.append({"period": entry["period"], "available": False})
        else:
            periods.append({
                "period": entry["period"],
                "available": True,
                "from_date": entry["past_date"].strftime("%Y-%m-%d"),
                "market_gain": round(entry["market_gain"], 2),
                "simple_return": round(entry["simple_return"], 2),
                "twr": round(entry["twr"] * 100, 2) if entry["twr"] is not None else None,
                "mwrr": round(entry["mwrr"], 2) if entry["mwrr"] is not None else None,
            })
    return periods
