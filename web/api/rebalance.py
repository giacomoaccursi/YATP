"""Rebalance API: suggestions and simulation."""

from flask import Blueprint, jsonify, request

from web.config import get_paths
from web.rebalance_service import load_rebalance_data, simulate_rebalance
from web.serializers import rebalance_to_dict
from web.validators import validate_rebalance_input

rebalance_bp = Blueprint("rebalance", __name__)


@rebalance_bp.route("/api/rebalance")
def api_rebalance():
    """Return rebalancing suggestions."""
    actions = load_rebalance_data(
        *get_paths()
    )
    return jsonify({"actions": [rebalance_to_dict(a) for a in actions]})


@rebalance_bp.route("/api/rebalance/simulate", methods=["POST"])
def api_rebalance_simulate():
    """Simulate rebalance with custom investment and targets."""
    new_investment, custom_targets = validate_rebalance_input(request.get_json())
    actions = simulate_rebalance(
        *get_paths(),
        new_investment, custom_targets,
    )
    return jsonify({"actions": [rebalance_to_dict(a) for a in actions]})
