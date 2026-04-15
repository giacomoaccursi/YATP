"""Portfolio allocation breakdown calculations."""


def calc_allocation(results):
    """Calculate percentage weight of each instrument by market value."""
    total_market_value = sum(r.analysis.market_value for r in results)

    allocations = {}
    for r in results:
        weight = (r.analysis.market_value / total_market_value * 100
                  if total_market_value > 0 else 0)
        allocations[r.security] = weight

    return allocations


def calc_allocation_by_asset_class(results, instruments):
    """Calculate percentage weight by asset class (ETF, ETC, Stock, etc.)."""
    total_market_value = sum(r.analysis.market_value for r in results)
    by_class = {}

    for r in results:
        instrument = instruments.get(r.security.strip(), {})
        asset_class = instrument.get("type", "Other")
        by_class[asset_class] = by_class.get(asset_class, 0) + r.analysis.market_value

    allocations = {}
    for asset_class, value in by_class.items():
        allocations[asset_class] = (value / total_market_value * 100
                                    if total_market_value > 0 else 0)

    return allocations
