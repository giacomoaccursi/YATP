"""Tests for portfolio.rebalance module."""

from portfolio.rebalance import calc_rebalance


def _make_result(security, market_value):
    return {"security": security, "analysis": {"market_value": market_value}}


INSTRUMENTS = {
    "ETF_A": {"type": "ETF"},
    "ETF_B": {"type": "ETF"},
    "GOLD": {"type": "ETC"},
}


class TestCalcRebalance:
    def test_already_balanced(self):
        results = [_make_result("ETF_A", 8000), _make_result("GOLD", 2000)]
        target = {"ETF": 80, "ETC": 20}
        actions = calc_rebalance(results, target, INSTRUMENTS)
        for action in actions:
            assert abs(action["difference"]) < 0.01

    def test_needs_rebalance(self):
        results = [_make_result("ETF_A", 6000), _make_result("GOLD", 4000)]
        target = {"ETF": 80, "ETC": 20}
        actions = calc_rebalance(results, target, INSTRUMENTS)
        etf_action = next(a for a in actions if a["asset_class"] == "ETF")
        etc_action = next(a for a in actions if a["asset_class"] == "ETC")
        assert etf_action["difference"] > 0  # buy ETF
        assert etc_action["difference"] < 0  # sell ETC

    def test_differences_sum_to_zero(self):
        results = [_make_result("ETF_A", 6000), _make_result("GOLD", 4000)]
        target = {"ETF": 80, "ETC": 20}
        actions = calc_rebalance(results, target, INSTRUMENTS)
        total_diff = sum(a["difference"] for a in actions)
        assert abs(total_diff) < 0.01

    def test_multiple_instruments_same_class(self):
        results = [_make_result("ETF_A", 3000), _make_result("ETF_B", 3000), _make_result("GOLD", 4000)]
        target = {"ETF": 80, "ETC": 20}
        actions = calc_rebalance(results, target, INSTRUMENTS)
        etf_action = next(a for a in actions if a["asset_class"] == "ETF")
        assert abs(etf_action["current_weight"] - 60.0) < 0.01

    def test_new_class_in_target(self):
        results = [_make_result("ETF_A", 10000)]
        target = {"ETF": 80, "Bond": 20}
        actions = calc_rebalance(results, target, INSTRUMENTS)
        bond_action = next(a for a in actions if a["asset_class"] == "Bond")
        assert bond_action["current_value"] == 0
        assert bond_action["difference"] == 2000

    def test_class_not_in_target(self):
        results = [_make_result("ETF_A", 8000), _make_result("GOLD", 2000)]
        target = {"ETF": 100}
        actions = calc_rebalance(results, target, INSTRUMENTS)
        etc_action = next(a for a in actions if a["asset_class"] == "ETC")
        assert etc_action["target_weight"] == 0
        assert etc_action["difference"] < 0

    def test_empty_portfolio(self):
        actions = calc_rebalance([], {"ETF": 100}, INSTRUMENTS)
        assert actions == []

    def test_zero_market_value(self):
        results = [_make_result("ETF_A", 0)]
        actions = calc_rebalance(results, {"ETF": 100}, INSTRUMENTS)
        assert actions == []
