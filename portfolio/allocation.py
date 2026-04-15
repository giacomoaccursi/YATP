"""Portfolio allocation breakdown calculations."""


def calc_allocation(results):
    """Calculate percentage weight of each instrument by market value."""
    total_market_value = sum(result["analysis"]["market_value"] for result in results)

    allocations = {}
    for result in results:
        weight = (result["analysis"]["market_value"] / total_market_value * 100
                  if total_market_value > 0 else 0)
        allocations[result["security"]] = weight

    return allocations


def calc_allocation_by_asset_class(results, instruments):
    """Calculate percentage weight by asset class (ETF, ETC, Stock, etc.)."""
    total_market_value = sum(result["analysis"]["market_value"] for result in results)
    by_class = {}

    for result in results:
        instrument = instruments.get(result["security"].strip(), {})
        asset_class = instrument.get("type", "Other")
        market_value = result["analysis"]["market_value"]
        by_class[asset_class] = by_class.get(asset_class, 0) + market_value

    allocations = {}
    for asset_class, value in by_class.items():
        allocations[asset_class] = (value / total_market_value * 100
                                    if total_market_value > 0 else 0)

    return allocations
