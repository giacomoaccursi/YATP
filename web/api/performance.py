"""Performance API: history, periods, filtered views."""

from flask import Blueprint, jsonify, request

from web.config import get_paths
from web.history_service import (
    load_portfolio_history, load_performance_periods,
    load_instrument_performance_periods,
    load_filtered_history, load_filtered_performance_periods,
)
from web.serializers import period_to_dict

performance_bp = Blueprint("performance", __name__)


@performance_bp.route("/api/portfolio/history")
def api_portfolio_history():
    """Return daily portfolio value from first transaction to today."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    data = load_portfolio_history(
        *get_paths(),
        start_date=start_date, end_date=end_date,
    )
    return jsonify(data)


@performance_bp.route("/api/instruments/<path:security>/periods")
def api_instrument_periods(security):
    """Return performance metrics for standard periods for a single instrument."""
    periods = load_instrument_performance_periods(
        *get_paths(), security
    )
    if not periods:
        return jsonify({"periods": []})
    return jsonify({"periods": [period_to_dict(p) for p in periods]})


@performance_bp.route("/api/performance/periods")
def api_performance_periods():
    """Return performance metrics for standard periods."""
    periods = load_performance_periods(
        *get_paths()
    )
    if not periods:
        return jsonify({"periods": []})
    return jsonify({"periods": [period_to_dict(p) for p in periods]})


@performance_bp.route("/api/performance/filtered/history", methods=["POST"])
def api_filtered_history():
    """Return daily metrics for a subset of instruments."""
    data = request.get_json()
    securities = data.get("securities", [])
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    if not securities:
        return jsonify({"dates": [], "values": [], "costs": [], "return_pcts": [], "total_return_pcts": [], "twr_pcts": [], "drawdown_pcts": []})
    result = load_filtered_history(
        *get_paths(),
        securities, start_date=start_date, end_date=end_date,
    )
    return jsonify(result)


@performance_bp.route("/api/performance/filtered/periods", methods=["POST"])
def api_filtered_periods():
    """Return performance periods for a subset of instruments."""
    data = request.get_json()
    securities = data.get("securities", [])
    if not securities:
        return jsonify({"periods": []})
    periods = load_filtered_performance_periods(
        *get_paths(), securities
    )
    if not periods:
        return jsonify({"periods": []})
    return jsonify({"periods": [period_to_dict(p) for p in periods]})
