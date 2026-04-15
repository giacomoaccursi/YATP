"""Output: stampa report a terminale."""


def print_instrument(security, ticker_symbol, data, analysis, capital_gains_rate, tax_info):
    """Stampa il report per un singolo strumento."""
    print(f"{'═' * 55}")
    print(f"📌 {security} ({ticker_symbol})")
    print(f"{'─' * 55}")
    print(f"   Shares in portafoglio:  {data['shares_held']:.4f}")
    print(f"   Costo medio per share:  €{data['avg_cost_per_share']:.2f}")
    print(f"   Costo totale (basis):   €{data['cost_basis']:.2f}")
    print(f"   Prezzo corrente:        €{analysis['market_value'] / data['shares_held']:.2f}" if data['shares_held'] > 0 else "   Prezzo corrente:        N/A")
    print(f"   Valore di mercato:      €{analysis['market_value']:.2f}")
    print()
    print(f"   📈 RENDIMENTI:")
    print(f"   P&L non realizzato:     €{analysis['unrealized_pnl']:+.2f}")
    print(f"   P&L realizzato:         €{data['realized_pnl']:+.2f}")
    print(f"   P&L TOTALE:             €{analysis['total_pnl']:+.2f}")
    print(f"   Rendimento semplice:    {analysis['simple_return']:+.2f}%")
    if analysis["twr"] is not None:
        print(f"   TWR (Time-Weighted):    {analysis['twr'] * 100:+.2f}%")
    if analysis["xirr"] is not None:
        print(f"   XIRR (Money-Weighted):  {analysis['xirr'] * 100:+.2f}% annuo")
    print()
    print(f"   💸 STIMA TASSE (se vendessi oggi):")
    print(f"   Aliquota:               {capital_gains_rate * 100:.0f}% ({tax_info['country']} - {tax_info['regime']})")
    print(f"   Tasse stimate:          €{analysis['estimated_tax']:.2f}")
    print(f"   Guadagno netto:         €{analysis['net_after_tax']:+.2f}")
    print(f"{'═' * 55}")


def print_portfolio_summary(summary):
    """Stampa il riepilogo dell'intero portafoglio."""
    print(f"\n{'═' * 55}")
    print(f"📌 PORTAFOGLIO TOTALE")
    print(f"{'─' * 55}")
    print(f"   Costo totale (basis):   €{summary['cost']:.2f}")
    print(f"   Valore di mercato:      €{summary['market_value']:.2f}")
    print()
    print(f"   📈 RENDIMENTI:")
    print(f"   P&L non realizzato:     €{summary['unrealized']:+.2f}")
    print(f"   P&L realizzato:         €{summary['realized']:+.2f}")
    print(f"   P&L TOTALE:             €{summary['total_pnl']:+.2f}")
    print(f"   Rendimento semplice:    {summary['simple_return']:+.2f}%")
    if summary["xirr"] is not None:
        print(f"   XIRR (Money-Weighted):  {summary['xirr'] * 100:+.2f}% annuo")
    print()
    print(f"   💸 STIMA TASSE (se vendessi tutto oggi):")
    print(f"   Tasse stimate totali:   €{summary['tax']:.2f}")
    print(f"   Guadagno netto totale:  €{summary['net_after_tax']:+.2f}")
    if summary.get("allocations"):
        print()
        print(f"   📊 ALLOCAZIONE PER STRUMENTO:")
        for security, weight in summary["allocations"].items():
            print(f"   {security:<25s} {weight:.1f}%")
    if summary.get("allocations_by_asset_class"):
        print()
        print(f"   📊 ALLOCAZIONE PER ASSET CLASS:")
        for asset_class, weight in summary["allocations_by_asset_class"].items():
            print(f"   {asset_class:<25s} {weight:.1f}%")
    print(f"{'═' * 55}")


def print_history(history):
    """Stampa la performance storica del portafoglio."""
    if not history:
        print("\n⚠️  Nessun dato storico disponibile.")
        return

    print(f"\n{'═' * 72}")
    print(f"📈 PERFORMANCE STORICA")
    print(f"{'─' * 72}")
    print(f"   {'Periodo':<14s} {'Dal':<12s} {'P&L':>10s} {'Semplice':>10s} {'TWR':>10s} {'MWRR':>10s}")
    print(f"   {'─' * 14} {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10}")

    for entry in history:
        if not entry["available"]:
            print(f"   {entry['period']:<14s} {'':>12s} {'N/A':>10s}")
        else:
            date_str = entry["past_date"].strftime("%Y-%m-%d")
            mwrr = f"{entry['mwrr']:>+9.2f}%" if entry["mwrr"] is not None else "      N/A"
            twr = f"{entry['twr'] * 100:>+9.2f}%" if entry["twr"] is not None else "      N/A"
            print(f"   {entry['period']:<14s} {date_str:<12s} €{entry['market_gain']:>+8.2f} {entry['simple_return']:>+9.2f}% {twr} {mwrr}")

    print(f"{'═' * 72}")
