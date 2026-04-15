"""Tests for portfolio.allocation module."""

from portfolio.allocation import calc_allocation, calc_allocation_by_asset_class
from portfolio.models import InstrumentResult, InstrumentData, InstrumentAnalysis


def _make_result(security, market_value):
    data = InstrumentData(shares_held=0, avg_cost_per_share=0, cost_basis=0, realized_pnl=0)
    analysis = InstrumentAnalysis(
        market_value=market_value, unrealized_pnl=0, total_pnl=0,
        simple_return=0, twr=None, xirr=None, estimated_tax=0, net_after_tax=0,
    )
    return InstrumentResult(
        security=security, ticker="", isin=None, capital_gains_rate=0.26,
        data=data, analysis=analysis,
    )


class TestCalcAllocation:
    def test_two_instruments(self):
        results = [_make_result("A", 7000), _make_result("B", 3000)]
        alloc = calc_allocation(results)
        assert abs(alloc["A"] - 70.0) < 0.01
        assert abs(alloc["B"] - 30.0) < 0.01

    def test_single_instrument(self):
        results = [_make_result("A", 5000)]
        alloc = calc_allocation(results)
        assert abs(alloc["A"] - 100.0) < 0.01

    def test_equal_weights(self):
        results = [_make_result("A", 1000), _make_result("B", 1000), _make_result("C", 1000)]
        alloc = calc_allocation(results)
        for weight in alloc.values():
            assert abs(weight - 33.33) < 0.01

    def test_zero_total_value(self):
        results = [_make_result("A", 0), _make_result("B", 0)]
        alloc = calc_allocation(results)
        assert alloc["A"] == 0
        assert alloc["B"] == 0

    def test_sums_to_100(self):
        results = [_make_result("A", 3000), _make_result("B", 5000), _make_result("C", 2000)]
        alloc = calc_allocation(results)
        assert abs(sum(alloc.values()) - 100.0) < 0.01


class TestCalcAllocationByAssetClass:
    def test_different_classes(self):
        results = [_make_result("ETF_A", 7000), _make_result("GOLD", 3000)]
        instruments = {"ETF_A": {"type": "ETF"}, "GOLD": {"type": "ETC"}}
        alloc = calc_allocation_by_asset_class(results, instruments)
        assert abs(alloc["ETF"] - 70.0) < 0.01
        assert abs(alloc["ETC"] - 30.0) < 0.01

    def test_same_class_aggregated(self):
        results = [_make_result("ETF_A", 5000), _make_result("ETF_B", 5000)]
        instruments = {"ETF_A": {"type": "ETF"}, "ETF_B": {"type": "ETF"}}
        alloc = calc_allocation_by_asset_class(results, instruments)
        assert abs(alloc["ETF"] - 100.0) < 0.01

    def test_missing_instrument_defaults_to_other(self):
        results = [_make_result("UNKNOWN", 1000)]
        alloc = calc_allocation_by_asset_class(results, {})
        assert "Other" in alloc

    def test_sums_to_100(self):
        results = [_make_result("A", 3000), _make_result("B", 5000), _make_result("C", 2000)]
        instruments = {"A": {"type": "ETF"}, "B": {"type": "ETC"}, "C": {"type": "Stock"}}
        alloc = calc_allocation_by_asset_class(results, instruments)
        assert abs(sum(alloc.values()) - 100.0) < 0.01
