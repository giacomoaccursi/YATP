"""Return analysis: per-instrument and aggregate portfolio calculations."""

from datetime import datetime
from portfolio.returns import calc_xirr, calc_twr, calc_simple_return, calc_estimated_tax
from portfolio.allocation import calc_allocation, calc_allocation_by_asset_class
from portfolio.models import InstrumentAnalysis, PortfolioSummary, InstrumentData


def analyze_instrument(data: InstrumentData, current_price, capital_gains_rate):
    """Calculate all returns for a single instrument."""
    market_value = current_price * data.shares_held
    unrealized_pnl = market_value - data.cost_basis
    estimated_tax = calc_estimated_tax(unrealized_pnl, capital_gains_rate)

    return InstrumentAnalysis(
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        total_pnl=unrealized_pnl + data.realized_pnl,
        simple_return=calc_simple_return(unrealized_pnl, data.cost_basis),
        twr=calc_twr(data.twr_txns, current_price),
        xirr=calc_xirr(data.cashflows + [(datetime.now(), market_value)]),
        estimated_tax=estimated_tax,
        net_after_tax=unrealized_pnl - estimated_tax,
        total_income=data.total_income,
        yield_on_cost=(data.total_income / data.cost_basis * 100) if data.cost_basis > 0 else 0,
        total_return=unrealized_pnl + data.realized_pnl + data.total_income,
    )


def analyze_portfolio(results, instruments):
    """Calculate aggregate returns for the entire portfolio."""
    cost = sum(r.data.cost_basis for r in results)
    market_value = sum(r.analysis.market_value for r in results)
    unrealized = sum(r.analysis.unrealized_pnl for r in results)
    realized = sum(r.data.realized_pnl for r in results)
    tax = sum(r.analysis.estimated_tax for r in results)

    all_cashflows = []
    for r in results:
        all_cashflows.extend(r.data.cashflows)
    all_cashflows.append((datetime.now(), market_value))

    return PortfolioSummary(
        cost=cost,
        market_value=market_value,
        unrealized=unrealized,
        realized=realized,
        tax=tax,
        total_pnl=unrealized + realized,
        simple_return=calc_simple_return(unrealized, cost),
        xirr=calc_xirr(all_cashflows),
        net_after_tax=unrealized - tax,
        allocations=calc_allocation(results),
        allocations_by_asset_class=calc_allocation_by_asset_class(results, instruments),
    )
