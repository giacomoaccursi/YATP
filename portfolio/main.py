"""Simple Portfolio Tracker"""

import argparse
from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.market import fetch_current_price
from portfolio.output import print_instrument, print_portfolio_summary, print_history, print_rebalance
from portfolio.history import build_history
from portfolio.export import export_json
from portfolio.rebalance import calc_rebalance
from portfolio.models import InstrumentResult


def parse_args():
    parser = argparse.ArgumentParser(description="Simple Portfolio Tracker")
    parser.add_argument("--transactions", default="transactions.csv", help="Transactions CSV file")
    parser.add_argument("--config", default="config.json", help="Configuration JSON file")
    parser.add_argument("--export", metavar="FILE", help="Export report to JSON")
    parser.add_argument("--rebalance", action="store_true", help="Show rebalancing suggestions")
    return parser.parse_args()


def main():
    args = parse_args()

    config = load_config(args.config)
    tax_info = config["tax"]
    instruments = config["instruments"]
    df = load_transactions(args.transactions)
    portfolio = build_portfolio(df)

    print("\n📊 Fetching current prices...\n")

    # Per-instrument analysis
    results = []
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            print(f"⚠️  Instrument '{security}' not found in config.json. Please add it.")
            continue

        current_price = fetch_current_price(instrument["ticker"])
        if current_price is None:
            print(f"⚠️  No data for {instrument['ticker']}")
            continue

        capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
        analysis = analyze_instrument(data, current_price, capital_gains_rate)
        results.append(InstrumentResult(
            security=security,
            ticker=instrument["ticker"],
            isin=instrument.get("isin"),
            capital_gains_rate=capital_gains_rate,
            data=data,
            analysis=analysis,
        ))

    # Per-instrument output
    for result in results:
        print_instrument(result, tax_info)

    # Portfolio summary
    summary = None
    if results:
        summary = analyze_portfolio(results, instruments)
        print_portfolio_summary(summary)

    # Historical performance
    print("\n📈 Calculating historical performance...\n")
    history = build_history(df, instruments)
    print_history(history)

    # JSON export
    if args.export:
        export_json(args.export, results, summary, history, tax_info)
        print(f"\n💾 Report exported to {args.export}")

    # Rebalancing
    if args.rebalance:
        target_allocation = config.get("target_allocation")
        if not target_allocation:
            print("\n⚠️  No target_allocation defined in config.json.")
        elif results:
            actions = calc_rebalance(results, target_allocation, instruments)
            print_rebalance(actions)


if __name__ == "__main__":
    main()
