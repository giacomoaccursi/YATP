"""Terminal report output."""

from portfolio.models import InstrumentResult, PortfolioSummary


def print_instrument(result: InstrumentResult, tax_info):
    """Print report for a single instrument."""
    data = result.data
    analysis = result.analysis

    print(f"{'═' * 55}")
    print(f"📌 {result.security} ({result.ticker})")
    print(f"{'─' * 55}")
    print(f"   Shares held:            {data.shares_held:.4f}")
    print(f"   Avg cost per share:     €{data.avg_cost_per_share:.2f}")
    print(f"   Cost basis:             €{data.cost_basis:.2f}")
    print(f"   Current price:          €{analysis.market_value / data.shares_held:.2f}" if data.shares_held > 0 else "   Current price:          N/A")
    print(f"   Market value:           €{analysis.market_value:.2f}")
    print()
    print(f"   📈 RETURNS:")
    print(f"   Unrealized P&L:         €{analysis.unrealized_pnl:+.2f}")
    print(f"   Realized P&L:           €{data.realized_pnl:+.2f}")
    print(f"   Total P&L:              €{analysis.total_pnl:+.2f}")
    print(f"   Simple return:          {analysis.simple_return:+.2f}%")
    if analysis.twr is not None:
        print(f"   TWR (Time-Weighted):    {analysis.twr * 100:+.2f}%")
    if analysis.xirr is not None:
        print(f"   XIRR (Money-Weighted):  {analysis.xirr * 100:+.2f}% p.a.")
    if analysis.total_income > 0:
        print(f"   Dividends/Coupons:      €{analysis.total_income:+.2f}")
        print(f"   Yield on cost:          {analysis.yield_on_cost:+.2f}%")
        print(f"   Total return:           €{analysis.total_return:+.2f}")
    print()
    print(f"   💸 TAX ESTIMATE (if sold today):")
    print(f"   Rate:                   {result.capital_gains_rate * 100:.0f}% ({tax_info['country']} - {tax_info['regime']})")
    print(f"   Estimated tax:          €{analysis.estimated_tax:.2f}")
    print(f"   Net gain:               €{analysis.net_after_tax:+.2f}")
    print(f"{'═' * 55}")


def print_portfolio_summary(summary: PortfolioSummary):
    """Print aggregate portfolio summary."""
    print(f"\n{'═' * 55}")
    print(f"📌 TOTAL PORTFOLIO")
    print(f"{'─' * 55}")
    print(f"   Cost basis:             €{summary.cost:.2f}")
    print(f"   Market value:           €{summary.market_value:.2f}")
    print()
    print(f"   📈 RETURNS:")
    print(f"   Unrealized P&L:         €{summary.unrealized:+.2f}")
    print(f"   Realized P&L:           €{summary.realized:+.2f}")
    print(f"   Total P&L:              €{summary.total_pnl:+.2f}")
    print(f"   Simple return:          {summary.simple_return:+.2f}%")
    if summary.xirr is not None:
        print(f"   XIRR (Money-Weighted):  {summary.xirr * 100:+.2f}% p.a.")
    print()
    print(f"   💸 TAX ESTIMATE (if sold today):")
    print(f"   Total estimated tax:    €{summary.tax:.2f}")
    print(f"   Total net gain:         €{summary.net_after_tax:+.2f}")
    if summary.allocations:
        print()
        print(f"   📊 ALLOCATION BY INSTRUMENT:")
        for security, weight in summary.allocations.items():
            print(f"   {security:<25s} {weight:.1f}%")
    if summary.allocations_by_asset_class:
        print()
        print(f"   📊 ALLOCATION BY ASSET CLASS:")
        for asset_class, weight in summary.allocations_by_asset_class.items():
            print(f"   {asset_class:<25s} {weight:.1f}%")
    print(f"{'═' * 55}")


def print_history(history):
    """Print historical performance table."""
    if not history:
        print("\n⚠️  No historical data available.")
        return

    print(f"\n{'═' * 72}")
    print(f"📈 HISTORICAL PERFORMANCE")
    print(f"{'─' * 72}")
    print(f"   {'Period':<14s} {'From':<12s} {'P&L':>10s} {'Simple':>10s} {'TWR':>10s} {'MWRR':>10s}")
    print(f"   {'─' * 14} {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10}")

    for entry in history:
        if not entry.available:
            print(f"   {entry.period:<14s} {'':>12s} {'N/A':>10s}")
        else:
            date_str = entry.past_date.strftime("%Y-%m-%d")
            mwrr = f"{entry.mwrr:>+9.2f}%" if entry.mwrr is not None else "      N/A"
            twr = f"{entry.twr * 100:>+9.2f}%" if entry.twr is not None else "      N/A"
            print(f"   {entry.period:<14s} {date_str:<12s} €{entry.market_gain:>+8.2f} {entry.simple_return:>+9.2f}% {twr} {mwrr}")

    print(f"{'═' * 72}")


def print_rebalance(actions):
    """Print rebalancing suggestions."""
    if not actions:
        print("\n⚠️  No rebalancing data available.")
        return

    print(f"\n{'═' * 72}")
    print(f"⚖️  REBALANCE")
    print(f"{'─' * 72}")
    print(f"   {'Asset Class':<25s} {'Current':>8s} {'Target':>8s} {'Action':>12s}")
    print(f"   {'─' * 25} {'─' * 8} {'─' * 8} {'─' * 12}")

    for action in actions:
        diff = action.difference
        label = f"Buy €{diff:,.0f}" if diff > 0 else f"Sell €{abs(diff):,.0f}" if diff < 0 else "On target"
        print(f"   {action.asset_class:<25s} {action.current_weight:>7.1f}% {action.target_weight:>7.1f}% {label:>12s}")

    print(f"{'═' * 72}")
