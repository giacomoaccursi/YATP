"""Portfolio rebalancing: compare current vs target allocation by asset class."""

from portfolio.models import RebalanceAction


def calc_rebalance(results, target_allocation, instruments):
    """Calculate buy/sell amounts per asset class to reach target allocation.

    target_allocation: dict of asset_class -> target percentage (e.g. {"ETF": 80, "ETC": 20})
    instruments: config instruments dict (used to map security -> asset class)
    """
    total_market_value = sum(r.analysis.market_value for r in results)

    if total_market_value <= 0:
        return []

    # Group current values by asset class
    current_by_class = {}
    for r in results:
        instrument = instruments.get(r.security.strip(), {})
        asset_class = instrument.get("type", "Other")
        current_by_class[asset_class] = current_by_class.get(asset_class, 0) + r.analysis.market_value

    all_classes = set(current_by_class.keys()) | set(target_allocation.keys())

    actions = []
    for asset_class in sorted(all_classes):
        current_value = current_by_class.get(asset_class, 0)
        current_weight = (current_value / total_market_value) * 100
        target_weight = target_allocation.get(asset_class, 0)
        target_value = total_market_value * (target_weight / 100)

        actions.append(RebalanceAction(
            asset_class=asset_class,
            current_weight=current_weight,
            target_weight=target_weight,
            current_value=current_value,
            target_value=target_value,
            difference=target_value - current_value,
        ))

    return actions
