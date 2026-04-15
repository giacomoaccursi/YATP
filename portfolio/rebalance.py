"""Portfolio rebalancing: compare current vs target allocation."""


def calc_rebalance(results, target_allocation):
    """Calculate buy/sell amounts to reach target allocation.

    Returns a list of dicts with security, current weight, target weight,
    and the euro amount to buy (positive) or sell (negative).
    """
    total_market_value = sum(result["analysis"]["market_value"] for result in results)

    if total_market_value <= 0:
        return []

    actions = []
    for result in results:
        security = result["security"]
        current_value = result["analysis"]["market_value"]
        current_weight = (current_value / total_market_value) * 100
        target_weight = target_allocation.get(security, 0)
        target_value = total_market_value * (target_weight / 100)
        difference = target_value - current_value

        actions.append({
            "security": security,
            "current_weight": current_weight,
            "target_weight": target_weight,
            "current_value": current_value,
            "target_value": target_value,
            "difference": difference,
        })

    # Include instruments in target but not in portfolio
    portfolio_securities = {result["security"] for result in results}
    for security, target_weight in target_allocation.items():
        if security not in portfolio_securities:
            target_value = total_market_value * (target_weight / 100)
            actions.append({
                "security": security,
                "current_weight": 0,
                "target_weight": target_weight,
                "current_value": 0,
                "target_value": target_value,
                "difference": target_value,
            })

    return actions
