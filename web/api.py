"""Web API routes: JSON endpoints for the dashboard."""

import csv
import os
from flask import jsonify, request
from web.data import load_portfolio_data, clear_price_cache
from portfolio.summary import build_summary
from portfolio.loader import load_config, load_transactions
from portfolio.rebalance import calc_rebalance


def register_api_routes(app):
    """Register all API routes on the Flask app."""

    @app.route("/api/portfolio")
    def api_portfolio():
        """Return full portfolio data: instruments, summary, allocations."""
        results, summary, config = load_portfolio_data(
            app.config["CONFIG_PATH"], app.config["TRANSACTIONS_PATH"]
        )
        return jsonify({
            "instruments": [_instrument_to_dict(r) for r in results],
            "summary": _summary_to_dict(summary) if summary else None,
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
            "instruments": [_instrument_summary_to_dict(i) for i in summary.instruments],
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
        return jsonify({
            "actions": [_rebalance_to_dict(a) for a in actions],
        })

    @app.route("/api/instruments")
    def api_instruments():
        """Return list of configured instruments (for form dropdowns)."""
        config = load_config(app.config["CONFIG_PATH"])
        return jsonify({"instruments": list(config["instruments"].keys())})

    @app.route("/api/transactions/list")
    def api_transactions_list():
        """Return all transactions from the CSV."""
        df = load_transactions(app.config["TRANSACTIONS_PATH"])
        df = df.sort_values("Date", ascending=False)
        transactions = []
        for _, row in df.iterrows():
            transactions.append({
                "date": row["Date"].strftime("%Y-%m-%d"),
                "type": row["Type"].strip(),
                "security": row["Security"].strip(),
                "shares": round(row["Shares"], 6) if row["Shares"] else 0,
                "quote": round(row["Quote"], 2) if row["Quote"] else 0,
                "net_transaction_value": round(row["Net Transaction Value"], 2) if row["Net Transaction Value"] else 0,
            })
        return jsonify({"transactions": transactions})

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

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        """Clear price cache and force re-fetch."""
        clear_price_cache()
        return jsonify({"success": True})


# ── Serialization helpers ──

def _instrument_to_dict(result):
    """Convert InstrumentResult to API response dict."""
    return {
        "security": result.security,
        "ticker": result.ticker,
        "isin": result.isin,
        "shares_held": round(result.data.shares_held, 4),
        "avg_cost_per_share": round(result.data.avg_cost_per_share, 2),
        "cost_basis": round(result.data.cost_basis, 2),
        "market_value": round(result.analysis.market_value, 2),
        "unrealized_pnl": round(result.analysis.unrealized_pnl, 2),
        "realized_pnl": round(result.data.realized_pnl, 2),
        "total_pnl": round(result.analysis.total_pnl, 2),
        "simple_return": round(result.analysis.simple_return, 2),
        "twr": round(result.analysis.twr * 100, 2) if result.analysis.twr is not None else None,
        "xirr": round(result.analysis.xirr * 100, 2) if result.analysis.xirr is not None else None,
        "estimated_tax": round(result.analysis.estimated_tax, 2),
        "net_after_tax": round(result.analysis.net_after_tax, 2),
        "total_income": round(result.analysis.total_income, 2),
        "capital_gains_rate": result.capital_gains_rate,
    }


def _summary_to_dict(summary):
    """Convert PortfolioSummary to API response dict."""
    return {
        "cost": round(summary.cost, 2),
        "market_value": round(summary.market_value, 2),
        "unrealized": round(summary.unrealized, 2),
        "realized": round(summary.realized, 2),
        "total_pnl": round(summary.total_pnl, 2),
        "simple_return": round(summary.simple_return, 2),
        "xirr": round(summary.xirr * 100, 2) if summary.xirr is not None else None,
        "tax": round(summary.tax, 2),
        "net_after_tax": round(summary.net_after_tax, 2),
        "allocations": {k: round(v, 1) for k, v in summary.allocations.items()},
        "allocations_by_class": {k: round(v, 1) for k, v in summary.allocations_by_asset_class.items()},
    }


def _instrument_summary_to_dict(inst):
    """Convert InstrumentSummary to API response dict."""
    return {
        "security": inst.security,
        "total_buys": inst.total_buys,
        "total_sells": inst.total_sells,
        "total_invested": round(inst.total_invested, 2),
        "total_sold": round(inst.total_sold, 2),
        "total_income": round(inst.total_income, 2),
        "shares_held": round(inst.shares_held, 4),
        "avg_cost_per_share": round(inst.avg_cost_per_share, 2),
    }


def _rebalance_to_dict(action):
    """Convert RebalanceAction to API response dict."""
    return {
        "asset_class": action.asset_class,
        "current_weight": round(action.current_weight, 2),
        "target_weight": round(action.target_weight, 2),
        "difference": round(action.difference, 2),
    }
