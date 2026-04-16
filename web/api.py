"""Web API routes: JSON endpoints for the dashboard."""

import csv
import os
import pandas as pd
from flask import jsonify, request
from web.data import load_portfolio_data, clear_price_cache
from web.serializers import (
    instrument_to_dict, summary_to_dict, transaction_row_to_dict,
    instrument_summary_to_dict, rebalance_to_dict,
)
from portfolio.summary import build_summary
from portfolio.loader import load_config, load_transactions
from portfolio.rebalance import calc_rebalance


def register_api_routes(app):
    """Register all API routes on the Flask app."""

    @app.route("/api/portfolio/history")
    def api_portfolio_history():
        """Return daily portfolio value from first transaction to today."""
        df = load_transactions(app.config["TRANSACTIONS_PATH"])
        config = load_config(app.config["CONFIG_PATH"])
        instruments = config["instruments"]

        df = df.sort_values("Date")
        first_date = df["Date"].min().normalize()
        today = pd.Timestamp.now().normalize()

        from portfolio.market import fetch_price_history

        price_histories = {}
        for security in df["Security"].unique():
            inst = instruments.get(security.strip())
            if not inst:
                continue
            prices = fetch_price_history(inst["ticker"], first_date, today)
            if prices is not None:
                price_histories[security] = prices

        if not price_histories:
            return jsonify({"dates": [], "values": []})

        # Build sorted date index from all price histories
        all_dates = set()
        for prices in price_histories.values():
            all_dates.update(prices.index.normalize())
        all_dates = sorted(d for d in all_dates if first_date <= d <= today)

        # Build transaction events sorted by date: list of (date, security, type, shares)
        tx_events = []
        for _, row in df.iterrows():
            tx_events.append((
                row["Date"].normalize(),
                row["Security"],
                row["Type"].strip().lower(),
                row["Shares"],
            ))
        tx_events.sort(key=lambda e: e[0])

        # Single-pass: walk through market days, apply transactions incrementally
        holdings = {}  # security -> shares
        tx_idx = 0
        dates = []
        values = []

        for date in all_dates:
            # Apply all transactions up to and including this date
            while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
                _, security, tx_type, shares = tx_events[tx_idx]
                if tx_type == "buy":
                    holdings[security] = holdings.get(security, 0.0) + shares
                elif tx_type == "sell":
                    holdings[security] = holdings.get(security, 0.0) - shares
                    if holdings[security] <= 1e-9:
                        holdings.pop(security, None)
                tx_idx += 1

            # Value current holdings at today's prices
            total = 0.0
            for security, shares in holdings.items():
                if security not in price_histories:
                    continue
                prices = price_histories[security]
                available = prices[prices.index <= date]
                if not available.empty:
                    total += shares * available.iloc[-1]

            dates.append(date.strftime("%Y-%m-%d"))
            values.append(round(total, 2))

        return jsonify({"dates": dates, "values": values})

    @app.route("/api/portfolio")
    def api_portfolio():
        """Return full portfolio data: instruments, summary, allocations."""
        results, summary, config = load_portfolio_data(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        return jsonify({
            "instruments": [instrument_to_dict(r) for r in results],
            "summary": summary_to_dict(summary) if summary else None,
        })

    @app.route("/api/summary")
    def api_summary():
        """Return transaction summary (no market data needed)."""
        df = load_transactions(app.config["TRANSACTIONS_PATH"])
        summary = build_summary(df)
        return jsonify({
            "total_transactions": summary.total_transactions,
            "total_invested": summary.total_invested,
            "total_sold": summary.total_sold,
            "total_income": summary.total_income,
            "net_invested": summary.net_invested,
            "instruments": [instrument_summary_to_dict(i) for i in summary.instruments],
        })

    @app.route("/api/rebalance")
    def api_rebalance():
        """Return rebalancing suggestions."""
        results, _, config = load_portfolio_data(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        target = config.get("target_allocation")
        if not target or not results:
            return jsonify({"actions": []})
        actions = calc_rebalance(results, target, config["instruments"])
        return jsonify({"actions": [rebalance_to_dict(a) for a in actions]})

    @app.route("/api/instruments")
    def api_instruments():
        """Return list of configured instruments (for form dropdowns)."""
        config = load_config(app.config["CONFIG_PATH"])
        return jsonify({"instruments": list(config["instruments"].keys())})

    @app.route("/api/instruments/<path:security>/history")
    def api_instrument_history(security):
        """Return price history and cost basis evolution for a single instrument."""
        df = load_transactions(app.config["TRANSACTIONS_PATH"])
        config = load_config(app.config["CONFIG_PATH"])
        inst = config["instruments"].get(security)
        if not inst:
            return jsonify({"error": "Instrument not found"}), 404

        from portfolio.market import fetch_price_history

        df = df.sort_values("Date")
        inst_df = df[df["Security"].str.strip() == security.strip()]
        if inst_df.empty:
            return jsonify({"dates": [], "prices": [], "cost_avg": [], "pnl": []})

        first_date = inst_df["Date"].min().normalize()
        today = pd.Timestamp.now().normalize()

        prices = fetch_price_history(inst["ticker"], first_date, today)
        if prices is None:
            return jsonify({"dates": [], "prices": [], "cost_avg": [], "pnl": []})

        # Build transaction events for this instrument
        tx_events = []
        for _, row in inst_df.iterrows():
            tx_events.append((
                row["Date"].normalize(),
                row["Type"].strip().lower(),
                row["Shares"],
                row["Net Transaction Value"],
            ))
        tx_events.sort(key=lambda e: e[0])

        # Walk through price dates, track holdings and cost incrementally
        all_dates = sorted(prices.index.normalize().unique())
        all_dates = [d for d in all_dates if first_date <= d <= today]

        tx_idx = 0
        shares = 0.0
        total_cost = 0.0

        dates = []
        price_values = []
        cost_avg_values = []
        pnl_values = []

        for date in all_dates:
            while tx_idx < len(tx_events) and tx_events[tx_idx][0] <= date:
                _, tx_type, tx_shares, net_value = tx_events[tx_idx]
                if tx_type == "buy":
                    shares += tx_shares
                    total_cost += net_value
                elif tx_type == "sell":
                    if shares > 0:
                        avg = total_cost / shares
                        total_cost -= avg * tx_shares
                    shares -= tx_shares
                    if shares <= 1e-9:
                        shares = 0.0
                        total_cost = 0.0
                tx_idx += 1

            if shares <= 1e-9:
                continue

            available = prices[prices.index <= date]
            if available.empty:
                continue

            price = available.iloc[-1]
            avg_cost = total_cost / shares if shares > 0 else 0
            market_val = shares * price
            unrealized = market_val - total_cost

            dates.append(date.strftime("%Y-%m-%d"))
            price_values.append(round(price, 4))
            cost_avg_values.append(round(avg_cost, 4))
            pnl_values.append(round(unrealized, 2))

        return jsonify({
            "dates": dates,
            "prices": price_values,
            "cost_avg": cost_avg_values,
            "pnl": pnl_values,
        })

    @app.route("/api/transactions/list")
    def api_transactions_list():
        """Return all transactions from the CSV with row index."""
        df = load_transactions(app.config["TRANSACTIONS_PATH"])
        df = df.sort_values("Date", ascending=False)
        return jsonify({
            "transactions": [transaction_row_to_dict(idx, row) for idx, row in df.iterrows()],
        })

    @app.route("/api/transactions", methods=["POST"])
    def api_add_transaction():
        """Append a new transaction to the CSV file."""
        data = request.get_json()
        required = ["date", "type", "security"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        row = {
            "Date": data["date"] + " 00:00:00",
            "Type": data["type"],
            "Security": data["security"],
            "Shares": data.get("shares", ""),
            "Quote": data.get("quote", ""),
            "Amount": data.get("amount", ""),
            "Fees": data.get("fees", ""),
            "Taxes": data.get("taxes", ""),
            "Net Transaction Value": data.get("net_transaction_value", ""),
        }

        csv_path = app.config["TRANSACTIONS_PATH"]
        file_exists = os.path.exists(csv_path)

        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        return jsonify({"success": True})

    @app.route("/api/transactions/<int:row_index>", methods=["PUT"])
    def api_update_transaction(row_index):
        """Update a transaction by its row index."""
        csv_path = app.config["TRANSACTIONS_PATH"]
        df = pd.read_csv(csv_path)
        if row_index < 0 or row_index >= len(df):
            return jsonify({"error": "Invalid row index"}), 400

        data = request.get_json()
        required = ["date", "type", "security"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        df.at[row_index, "Date"] = data["date"] + " 00:00:00"
        df.at[row_index, "Type"] = data["type"]
        df.at[row_index, "Security"] = data["security"]
        df.at[row_index, "Shares"] = data.get("shares", "")
        df.at[row_index, "Quote"] = data.get("quote", "")
        df.at[row_index, "Amount"] = data.get("amount", "")
        df.at[row_index, "Fees"] = data.get("fees", "")
        df.at[row_index, "Taxes"] = data.get("taxes", "")
        df.at[row_index, "Net Transaction Value"] = data.get("net_transaction_value", "")

        df.to_csv(csv_path, index=False)
        return jsonify({"success": True})

    @app.route("/api/transactions/<int:row_index>", methods=["DELETE"])
    def api_delete_transaction(row_index):
        """Delete a transaction by its row index."""
        csv_path = app.config["TRANSACTIONS_PATH"]
        df = pd.read_csv(csv_path)
        if row_index < 0 or row_index >= len(df):
            return jsonify({"error": "Invalid row index"}), 400
        df = df.drop(index=row_index).reset_index(drop=True)
        df.to_csv(csv_path, index=False)
        return jsonify({"success": True})

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        """Clear price cache and force re-fetch."""
        clear_price_cache()
        return jsonify({"success": True})

    @app.route("/api/performance/periods")
    def api_performance_periods():
        """Return performance metrics for standard periods (1m, 6m, 1y, since start)."""
        from portfolio.history import build_history
        df = load_transactions(app.config["TRANSACTIONS_PATH"])
        config = load_config(app.config["CONFIG_PATH"])
        history = build_history(df, config["instruments"])
        if not history:
            return jsonify({"periods": []})
        periods = []
        for p in history:
            periods.append({
                "period": p.period,
                "available": p.available,
                "market_gain": round(p.market_gain, 2) if p.available else None,
                "simple_return": round(p.simple_return, 2) if p.available else None,
                "twr": round(p.twr * 100, 2) if p.available and p.twr is not None else None,
                "mwrr": round(p.mwrr * 100, 2) if p.available and p.mwrr is not None else None,
            })
        return jsonify({"periods": periods})
