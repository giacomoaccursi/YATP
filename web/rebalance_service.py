"""Rebalance service: current allocation vs target, simulation."""

from portfolio.rebalance import calc_rebalance
from portfolio.models import RebalanceAction
from web.portfolio_service import load_portfolio_data


def load_rebalance_data(config_path, transactions_path):
    """Load rebalancing suggestions. Returns list of RebalanceAction."""
    results, _, _, config, _ = load_portfolio_data(config_path, transactions_path)
    target = config.get("target_allocation")
    if not target or not results:
        return []
    return calc_rebalance(results, target, config["instruments"])


def simulate_rebalance(config_path, transactions_path, new_investment, custom_targets):
    """Simulate rebalance with optional new investment and custom targets."""
    results, _, _, config, _ = load_portfolio_data(config_path, transactions_path)
    instruments = config["instruments"]

    total_market = sum(instrument_result.analysis.market_value for instrument_result in results)
    total_value = total_market + new_investment

    if total_value <= 0:
        return []

    current_by_class = {}
    for instrument_result in results:
        instrument = instruments.get(instrument_result.security.strip(), {})
        asset_class = instrument.get("type", "Other")
        current_by_class[asset_class] = current_by_class.get(asset_class, 0) + instrument_result.analysis.market_value

    all_classes = sorted(set(current_by_class.keys()) | set(custom_targets.keys()))

    actions = []
    for asset_class_name in all_classes:
        current_value = current_by_class.get(asset_class_name, 0)
        current_weight = (current_value / total_value) * 100 if total_value > 0 else 0
        target_weight = custom_targets.get(asset_class_name, 0)
        target_value = total_value * (target_weight / 100)
        actions.append(RebalanceAction(
            asset_class=asset_class_name,
            current_value=round(current_value, 2),
            current_weight=round(current_weight, 2),
            target_weight=round(target_weight, 2),
            target_value=round(target_value, 2),
            difference=round(target_value - current_value, 2),
        ))

    return actions
