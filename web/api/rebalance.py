"""Rebalance API: suggestions and simulation."""

from flask import Blueprint, jsonify, request, current_app

from web.rebalance_service import load_rebalance_data, simulate_rebalance
from web.serializers import rebalance_to_dict

rebalance_bp = Blueprint("rebalance", __name__)


@rebalance_bp.route("/api/rebalance")
def api_rebalance():
    """Return rebalancing suggestions."""
    actions = load_rebalance_data(
        current_app.config["CONFIG_PATH"], current_app.config["TRANSACTIONS_PATH"]
    )
    return jsonify({"actions": [rebalance_to_dict(a) for a in actions]})


@rebalance_bp.route("/api/rebalance/simulate", methods=["POST"])
def api_rebalance_simulate():
    """Simulate rebalance with custom investment and targets."""
    data = request.get_json()
    new_investment = data.get("new_investment", 0)
    custom_targets = data.get("targets", {})
    actions = simulate_rebalance(
        current_app.config["CONFIG_PATH"], current_app.config["TRANSACTIONS_PATH"],
        new_investment, custom_targets,
    )
    return jsonify({"actions": actions})
