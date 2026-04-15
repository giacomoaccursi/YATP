"""Tests for portfolio.rebalance module."""

from portfolio.rebalance import calc_rebalance
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


INSTRUMENTS = {"ETF_A": {"type": "ETF"}, "ETF_B": {"type": "ETF"}, "GOLD": {"type": "ETC"}}


class TestCalcRebalance:
    def test_already_balanced(self):
        results = [_make_result("ETF_A", 8000), _make_result("GOLD", 2000)]
        actions = calc_rebalance(results, {"ETF": 80, "ETC": 20}, INSTRUMENTS)
        for action in actions:
            assert abs(action.difference) < 0.01

    def test_needs_rebalance(self):
        results = [_make_result("ETF_A", 6000), _make_result("GOLD", 4000)]
        actions = calc_rebalance(results, {"ETF": 80, "ETC": 20}, INSTRUMENTS)
        etf = next(a for a in actions if a.asset_class == "ETF")
        etc = next(a for a in actions if a.asset_class == "ETC")
        assert etf.difference > 0
        assert etc.difference < 0

    def test_differences_sum_to_zero(self):
        results = [_make_result("ETF_A", 6000), _make_result("GOLD", 4000)]
        actions = calc_rebalance(results, {"ETF": 80, "ETC": 20}, INSTRUMENTS)
        assert abs(sum(a.difference for a in actions)) < 0.01

    def test_multiple_instruments_same_class(self):
        results = [_make_result("ETF_A", 3000), _make_result("ETF_B", 3000), _make_result("GOLD", 4000)]
        actions = calc_rebalance(results, {"ETF": 80, "ETC": 20}, INSTRUMENTS)
        etf = next(a for a in actions if a.asset_class == "ETF")
        assert abs(etf.current_weight - 60.0) < 0.01

    def test_new_class_in_target(self):
        results = [_make_result("ETF_A", 10000)]
        actions = calc_rebalance(results, {"ETF": 80, "Bond": 20}, INSTRUMENTS)
        bond = next(a for a in actions if a.asset_class == "Bond")
        assert bond.current_value == 0
        assert bond.difference == 2000

    def test_class_not_in_target(self):
        results = [_make_result("ETF_A", 8000), _make_result("GOLD", 2000)]
        actions = calc_rebalance(results, {"ETF": 100}, INSTRUMENTS)
        etc = next(a for a in actions if a.asset_class == "ETC")
        assert etc.target_weight == 0
        assert etc.difference < 0

    def test_empty_portfolio(self):
        assert calc_rebalance([], {"ETF": 100}, INSTRUMENTS) == []

    def test_zero_market_value(self):
        results = [_make_result("ETF_A", 0)]
        assert calc_rebalance(results, {"ETF": 100}, INSTRUMENTS) == []
