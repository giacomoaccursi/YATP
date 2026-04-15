"""
Portfolio Tracker
Calcola rendimenti, P&L e stima tasse per un portafoglio di strumenti finanziari.

Uso:
  python run.py                          # solo output a terminale
  python run.py --export report.json     # salva anche in JSON
  python run.py -t mio.csv -c mio.json  # file custom
"""

import argparse
from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.market import fetch_current_price
from portfolio.output import print_instrument, print_portfolio_summary, print_history
from portfolio.history import build_history
from portfolio.export import export_json


def parse_args():
    parser = argparse.ArgumentParser(description="Portfolio Tracker")
    parser.add_argument("-t", "--transactions", default="transactions.csv", help="File CSV transazioni")
    parser.add_argument("-c", "--config", default="config.json", help="File configurazione JSON")
    parser.add_argument("--export", metavar="FILE", help="Esporta il report in JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    config = load_config(args.config)
    tax_info = config["tax"]
    instruments = config["instruments"]
    df = load_transactions(args.transactions)
    portfolio = build_portfolio(df)

    print("\n📊 Scarico prezzi correnti...\n")

    # Analisi per strumento
    results = []
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            print(f"⚠️  Strumento '{security}' non trovato in config.json. Aggiungilo.")
            continue

        current_price = fetch_current_price(instrument["ticker"])
        if current_price is None:
            print(f"⚠️  Nessun dato per {instrument['ticker']}")
            continue

        capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
        analysis = analyze_instrument(data, current_price, capital_gains_rate)
        results.append({"security": security, "data": data, "analysis": analysis,
                        "ticker": instrument["ticker"], "isin": instrument.get("isin"),
                        "capital_gains_rate": capital_gains_rate})

    # Output per strumento
    for result in results:
        print_instrument(result["security"], result["ticker"], result["data"],
                        result["analysis"], result["capital_gains_rate"], tax_info)

    # Output portafoglio totale
    summary = None
    if results:
        summary = analyze_portfolio(results, instruments)
        print_portfolio_summary(summary)

    # Storico portafoglio
    print("\n📈 Calcolo storico portafoglio...\n")
    history = build_history(df, instruments)
    print_history(history)

    # Export JSON
    if args.export:
        export_json(args.export, results, summary, history, tax_info)
        print(f"\n💾 Report esportato in {args.export}")


if __name__ == "__main__":
    main()
