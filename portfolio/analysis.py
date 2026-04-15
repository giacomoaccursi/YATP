"""Analisi rendimenti: calcoli per strumento e portafoglio aggregato."""

from datetime import datetime
from portfolio.returns import calc_xirr, calc_twr, calc_simple_return, calc_estimated_tax
from portfolio.allocation import calc_allocation, calc_allocation_by_asset_class


def analyze_instrument(data, current_price, capital_gains_rate):
    """Calcola tutti i rendimenti per un singolo strumento."""
    market_value = current_price * data["shares_held"]
    unrealized_pnl = market_value - data["cost_basis"]
    estimated_tax = calc_estimated_tax(unrealized_pnl, capital_gains_rate)

    return {
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": unrealized_pnl + data["realized_pnl"],
        "simple_return": calc_simple_return(unrealized_pnl, data["cost_basis"]),
        "twr": calc_twr(data["twr_txns"], current_price),
        "xirr": calc_xirr(data["cashflows"] + [(datetime.now(), market_value)]),
        "estimated_tax": estimated_tax,
        "net_after_tax": unrealized_pnl - estimated_tax,
    }


def analyze_portfolio(results, instruments):
    """Calcola i rendimenti aggregati dell'intero portafoglio."""
    totals = {"cost": 0, "market_value": 0, "unrealized": 0, "realized": 0, "tax": 0}
    all_cashflows = []

    for result in results:
        totals["cost"] += result["data"]["cost_basis"]
        totals["market_value"] += result["analysis"]["market_value"]
        totals["unrealized"] += result["analysis"]["unrealized_pnl"]
        totals["realized"] += result["data"]["realized_pnl"]
        totals["tax"] += result["analysis"]["estimated_tax"]
        all_cashflows.extend(result["data"]["cashflows"])

    all_cashflows.append((datetime.now(), totals["market_value"]))

    return {
        **totals,
        "total_pnl": totals["unrealized"] + totals["realized"],
        "simple_return": calc_simple_return(totals["unrealized"], totals["cost"]),
        "xirr": calc_xirr(all_cashflows),
        "net_after_tax": totals["unrealized"] - totals["tax"],
        "allocations": calc_allocation(results),
        "allocations_by_asset_class": calc_allocation_by_asset_class(results, instruments),
    }
