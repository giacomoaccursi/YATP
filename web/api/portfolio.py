"""Portfolio API: instruments, prices, refresh."""

from flask import Blueprint, jsonify, request

from web.config import get_paths
from web.errors import ValidationError, ConflictError, NotFoundError
from web.cache import clear_all_caches, get_price_fetch_time
from web.portfolio_service import load_portfolio_data, load_offline_summary
from web.history_service import load_portfolio_daily_change, load_instrument_history
from web.transaction_service import load_instrument_names, add_instrument_to_config
from web.serializers import instrument_to_dict, summary_to_dict, offline_summary_to_dict
from web.validators import validate_instrument_input

portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.route("/api/portfolio")
def api_portfolio():
    """Return full portfolio data. Always returns offline data; market data when available."""
    config_path, transactions_path = get_paths()

    offline = load_offline_summary(config_path, transactions_path)
    response = {
        "offline": offline_summary_to_dict(offline),
        "instruments": [],
        "summary": None,
        "daily_change": None,
        "market_error": None,
        "failed_instruments": [],
    }
    try:
        results, daily_changes, summary, _, failed = load_portfolio_data(config_path, transactions_path)
        total_market_value = sum(r.analysis.market_value for r in results)
        instrument_dicts = []
        for r in results:
            d = instrument_to_dict(r, daily_changes.get(r.security))
            d["weight"] = round(r.analysis.market_value / total_market_value * 100, 1) if total_market_value > 0 else 0
            instrument_dicts.append(d)
        response["instruments"] = instrument_dicts
        response["summary"] = summary_to_dict(summary) if summary else None
        response["daily_change"] = load_portfolio_daily_change(config_path, transactions_path)
        if failed:
            response["failed_instruments"] = failed
    except Exception as e:
        response["market_error"] = str(e)

    return jsonify(response)


@portfolio_bp.route("/api/instruments")
def api_instruments():
    """Return list of configured instruments with their types."""
    config_path, _ = get_paths()
    instrument_types = load_instrument_names(config_path)
    return jsonify({
        "instruments": list(instrument_types.keys()),
        "instrument_types": instrument_types,
    })


@portfolio_bp.route("/api/instruments", methods=["POST"])
def api_add_instrument():
    """Add a new instrument to the config."""
    config_path, _ = get_paths()
    cleaned = validate_instrument_input(request.get_json())

    added = add_instrument_to_config(
        config_path,
        cleaned["security"], cleaned["ticker"], cleaned["type"],
        cleaned["capital_gains_rate"], isin=cleaned["isin"],
    )
    if not added:
        raise ConflictError("Instrument already exists")

    clear_all_caches()
    return jsonify({"success": True})


@portfolio_bp.route("/api/instruments/<path:security>/history")
def api_instrument_history(security):
    """Return price history and cost basis evolution for a single instrument."""
    data = load_instrument_history(
        *get_paths(), security
    )
    if data is None:
        raise NotFoundError("Instrument not found")
    return jsonify(data)


@portfolio_bp.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Clear price cache and force re-fetch."""
    clear_all_caches()
    return jsonify({"success": True})


@portfolio_bp.route("/api/price-status")
def api_price_status():
    """Return the time when prices were last fetched."""
    return jsonify({"fetched_at": get_price_fetch_time()})
