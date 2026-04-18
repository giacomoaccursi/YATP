"""Web API routes: JSON endpoints for the dashboard."""

import csv
import os
import pandas as pd
from flask import jsonify, request
from web.data import (
    load_portfolio_data, load_rebalance_data, load_summary_data,
    load_instrument_names, load_portfolio_history, load_instrument_history,
    load_performance_periods, load_portfolio_daily_change,
    load_offline_summary, simulate_sell, get_price_fetch_time,
    simulate_rebalance, compute_net_transaction_value, clear_price_cache,
    add_instrument_to_config,
)
from web.serializers import (
    instrument_to_dict, summary_to_dict, transaction_row_to_dict,
    instrument_summary_to_dict, rebalance_to_dict, period_to_dict,
)
from portfolio.loader import load_transactions


def register_api_routes(app):
    """Register all API routes on the Flask app."""

    @app.route("/api/portfolio")
    def api_portfolio():
        """Return full portfolio data. Always returns offline data; market data when available."""
        offline = load_offline_summary(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        response = {
            "offline": offline,
            "instruments": [],
            "summary": None,
            "daily_change": None,
            "market_error": None,
            "failed_instruments": [],
        }
        try:
            results, daily_changes, summary, _, failed = load_portfolio_data(
                app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
            )
            response["instruments"] = [instrument_to_dict(r, daily_changes.get(r.security)) for r in results]
            response["summary"] = summary_to_dict(summary) if summary else None
            response["daily_change"] = load_portfolio_daily_change(
                app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
            )
            if failed:
                response["failed_instruments"] = failed
        except Exception as e:
            response["market_error"] = str(e)

        return jsonify(response)

    @app.route("/api/portfolio/history")
    def api_portfolio_history():
        """Return daily portfolio value from first transaction to today."""
        data = load_portfolio_history(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        return jsonify(data)

    @app.route("/api/summary")
    def api_summary():
        """Return transaction summary (no market data needed)."""
        summary = load_summary_data(app.config["TRANSACTIONS_PATH"])
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
        actions = load_rebalance_data(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        return jsonify({"actions": [rebalance_to_dict(a) for a in actions]})

    @app.route("/api/rebalance/simulate", methods=["POST"])
    def api_rebalance_simulate():
        """Simulate rebalance with custom investment and targets."""
        data = request.get_json()
        new_investment = data.get("new_investment", 0)
        custom_targets = data.get("targets", {})
        actions = simulate_rebalance(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"],
            new_investment, custom_targets,
        )
        return jsonify({"actions": actions})

    @app.route("/api/simulate/sell", methods=["POST"])
    def api_simulate_sell():
        """Simulate selling shares of an instrument."""
        data = request.get_json()
        security = data.get("security", "")
        shares = float(data.get("shares", 0) or 0)
        result = simulate_sell(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"],
            security, shares,
        )
        if result is None:
            return jsonify({"error": "Invalid instrument, not enough shares, or no market data"}), 400
        return jsonify(result)

    @app.route("/api/transactions/net-value", methods=["POST"])
    def api_net_value():
        """Compute net transaction value from form fields."""
        data = request.get_json()
        net = compute_net_transaction_value(
            data.get("type", ""),
            float(data.get("shares", 0) or 0),
            float(data.get("quote", 0) or 0),
            float(data.get("fees", 0) or 0),
            float(data.get("taxes", 0) or 0),
        )
        return jsonify({"net_transaction_value": net})

    @app.route("/api/instruments")
    def api_instruments():
        """Return list of configured instruments (for form dropdowns)."""
        names = load_instrument_names(app.config["CONFIG_PATH"])
        return jsonify({"instruments": names})

    @app.route("/api/instruments", methods=["POST"])
    def api_add_instrument():
        """Add a new instrument to the config."""
        data = request.get_json()
        security = data.get("security", "").strip()
        ticker = data.get("ticker", "").strip()
        instrument_type = data.get("type", "ETF").strip()
        capital_gains_rate = float(data.get("capital_gains_rate", 0.26) or 0.26)
        isin = (data.get("isin") or "").strip() or None

        if not security or not ticker:
            return jsonify({"error": "Security name and ticker are required"}), 400

        added = add_instrument_to_config(
            app.config["CONFIG_PATH"], security, ticker, instrument_type, capital_gains_rate, isin=isin,
        )
        if not added:
            return jsonify({"error": "Instrument already exists"}), 409

        clear_price_cache()
        return jsonify({"success": True})

    @app.route("/api/instruments/<path:security>/history")
    def api_instrument_history(security):
        """Return price history and cost basis evolution for a single instrument."""
        data = load_instrument_history(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"], security
        )
        if data is None:
            return jsonify({"error": "Instrument not found"}), 404
        return jsonify(data)

    @app.route("/api/performance/periods")
    def api_performance_periods():
        """Return performance metrics for standard periods."""
        periods = load_performance_periods(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        if not periods:
            return jsonify({"periods": []})
        return jsonify({"periods": [period_to_dict(p) for p in periods]})

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

    @app.route("/api/price-status")
    def api_price_status():
        """Return the time when prices were last fetched."""
        return jsonify({"fetched_at": get_price_fetch_time()})
