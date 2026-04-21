"""Transactions API: CRUD operations, net value calculation."""

import csv
import os
import pandas as pd
from flask import Blueprint, jsonify, request, current_app

from web.transaction_service import (
    load_summary_data, load_income_history, simulate_sell, compute_net_transaction_value,
)
from web.serializers import transaction_row_to_dict, instrument_summary_to_dict
from portfolio.loader import load_transactions

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("/api/summary")
def api_summary():
    """Return transaction summary (no market data needed)."""
    summary = load_summary_data(current_app.config["TRANSACTIONS_PATH"])
    return jsonify({
        "total_transactions": summary.total_transactions,
        "total_invested": summary.total_invested,
        "total_sold": summary.total_sold,
        "total_income": summary.total_income,
        "net_invested": summary.net_invested,
        "instruments": [instrument_summary_to_dict(i) for i in summary.instruments],
    })


@transactions_bp.route("/api/income/history")
def api_income_history():
    """Return monthly income (dividends + coupons)."""
    data = load_income_history(current_app.config["TRANSACTIONS_PATH"])
    return jsonify({"months": data})


@transactions_bp.route("/api/simulate/sell", methods=["POST"])
def api_simulate_sell():
    """Simulate selling shares of an instrument."""
    data = request.get_json()
    security = data.get("security", "")
    shares = float(data.get("shares", 0) or 0)
    result = simulate_sell(
        current_app.config["CONFIG_PATH"], current_app.config["TRANSACTIONS_PATH"],
        security, shares,
    )
    if result is None:
        return jsonify({"error": "Invalid instrument, not enough shares, or no market data"}), 400
    return jsonify(result)


@transactions_bp.route("/api/transactions/net-value", methods=["POST"])
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


@transactions_bp.route("/api/transactions/list")
def api_transactions_list():
    """Return all transactions from the CSV with row index."""
    df = load_transactions(current_app.config["TRANSACTIONS_PATH"])
    df = df.sort_values("Date", ascending=False)
    return jsonify({
        "transactions": [transaction_row_to_dict(idx, row) for idx, row in df.iterrows()],
    })


@transactions_bp.route("/api/transactions", methods=["POST"])
def api_add_transaction():
    """Append a new transaction to the CSV file."""
    data = request.get_json()
    required = ["date", "type", "security"]
    missing = [field for field in required if not data.get(field)]
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
        "Accrued Interest": data.get("accrued_interest", ""),
        "Net Transaction Value": data.get("net_transaction_value", ""),
    }

    csv_path = current_app.config["TRANSACTIONS_PATH"]
    file_exists = os.path.exists(csv_path)

    try:
        with open(csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except OSError as e:
        return jsonify({"error": f"Failed to write transaction: {e}"}), 500

    return jsonify({"success": True})


@transactions_bp.route("/api/transactions/<int:row_index>", methods=["PUT"])
def api_update_transaction(row_index):
    """Update a transaction by its row index."""
    csv_path = current_app.config["TRANSACTIONS_PATH"]
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return jsonify({"error": f"Failed to read transactions: {e}"}), 500

    if row_index < 0 or row_index >= len(df):
        return jsonify({"error": "Invalid row index"}), 400

    data = request.get_json()
    required = ["date", "type", "security"]
    missing = [field for field in required if not data.get(field)]
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
    df.at[row_index, "Accrued Interest"] = data.get("accrued_interest", "")
    df.at[row_index, "Net Transaction Value"] = data.get("net_transaction_value", "")

    try:
        df.to_csv(csv_path, index=False)
    except OSError as e:
        return jsonify({"error": f"Failed to save transaction: {e}"}), 500
    return jsonify({"success": True})


@transactions_bp.route("/api/transactions/<int:row_index>", methods=["DELETE"])
def api_delete_transaction(row_index):
    """Delete a transaction by its row index."""
    csv_path = current_app.config["TRANSACTIONS_PATH"]
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return jsonify({"error": f"Failed to read transactions: {e}"}), 500

    if row_index < 0 or row_index >= len(df):
        return jsonify({"error": "Invalid row index"}), 400
    df = df.drop(index=row_index).reset_index(drop=True)
    try:
        df.to_csv(csv_path, index=False)
    except OSError as e:
        return jsonify({"error": f"Failed to save transaction: {e}"}), 500
    return jsonify({"success": True})
