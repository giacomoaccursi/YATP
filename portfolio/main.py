"""Simple Portfolio Tracker"""

import argparse
from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.market import fetch_current_price
from portfolio.output import print_instrument, print_portfolio_summary, print_history, print_rebalance, print_summary
from portfolio.history import build_history
from portfolio.export import export_json
from portfolio.rebalance import calc_rebalance
from portfolio.models import InstrumentResult
from portfolio.summary import build_summary


def parse_args():
    parser = argparse.ArgumentParser(description="Simple Portfolio Tracker")
    parser.add_argument("--transactions", default="transactions.csv", help="Transactions CSV file")
    parser.add_argument("--config", default="config.json", help="Configuration JSON file")
    parser.add_argument("--export", metavar="FILE", help="Export report to JSON")
    parser.add_argument("--rebalance", action="store_true", help="Show rebalancing suggestions")
    parser.add_argument("--summary", action="store_true", help="Show transaction summary (no market data needed)")
    parser.add_argument("--ui", action="store_true", help="Launch web dashboard")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as error:
        print(f"❌ {error}")
        return

    tax_info = config["tax"]
    instruments = config["instruments"]

    try:
        df = load_transactions(args.transactions)
    except (FileNotFoundError, ValueError) as error:
        print(f"❌ {error}")
        return

    # Web UI mode
    if args.ui:
        from web.app import launch
        launch(args.config, args.transactions)
        return

    portfolio = build_portfolio(df)

    # Summary mode: no market data needed
    if args.summary:
        summary = build_summary(df)
        print_summary(summary)
        return

    print("\n📊 Fetching current prices...\n")

    # Per-instrument analysis
    results = []
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            print(f"⚠️  Instrument '{security}' not found in config.json. Please add it.")
            continue

        current_price = fetch_current_price(instrument["ticker"], isin=instrument.get("isin"), instrument_type=instrument.get("type"))
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
    rebalance_actions = None

    # Rebalancing
    if args.rebalance:
        target_allocation = config.get("target_allocation")
        if not target_allocation:
            print("\n⚠️  No target_allocation defined in config.json.")
        elif results:
            rebalance_actions = calc_rebalance(results, target_allocation, instruments)
            print_rebalance(rebalance_actions)

    if args.export:
        export_json(args.export, results, summary, history, tax_info, rebalance_actions)
        print(f"\n💾 Report exported to {args.export}")


if __name__ == "__main__":
    main()
