"""Tests for portfolio.rebalance module."""

from portfolio.rebalance import calc_rebalance


def _make_result(security, market_value):
    return {"security": security, "analysis": {"market_value": market_value}}


class TestCalcRebalance:
    def test_already_balanced(self):
        results = [_make_result("A", 8000), _make_result("B", 2000)]
        target = {"A": 80, "B": 20}
        actions = calc_rebalance(results, target)
        for action in actions:
            assert abs(action["difference"]) < 0.01

    def test_needs_rebalance(self):
        results = [_make_result("A", 7000), _make_result("B", 3000)]
        target = {"A": 80, "B": 20}
        actions = calc_rebalance(results, target)
        action_a = next(a for a in actions if a["security"] == "A")
        action_b = next(a for a in actions if a["security"] == "B")
        assert action_a["difference"] > 0  # buy A
        assert action_b["difference"] < 0  # sell B

    def test_differences_sum_to_zero(self):
        results = [_make_result("A", 6000), _make_result("B", 4000)]
        target = {"A": 80, "B": 20}
        actions = calc_rebalance(results, target)
        total_diff = sum(a["difference"] for a in actions)
        assert abs(total_diff) < 0.01

    def test_new_instrument_in_target(self):
        results = [_make_result("A", 10000)]
        target = {"A": 80, "C": 20}
        actions = calc_rebalance(results, target)
        action_c = next(a for a in actions if a["security"] == "C")
        assert action_c["current_weight"] == 0
        assert action_c["difference"] == 2000  # 20% of 10000

    def test_instrument_not_in_target(self):
        results = [_make_result("A", 8000), _make_result("B", 2000)]
        target = {"A": 100}
        actions = calc_rebalance(results, target)
        action_b = next(a for a in actions if a["security"] == "B")
        assert action_b["target_weight"] == 0
        assert action_b["difference"] < 0  # sell all B

    def test_empty_portfolio(self):
        actions = calc_rebalance([], {"A": 100})
        assert actions == []

    def test_zero_market_value(self):
        results = [_make_result("A", 0)]
        actions = calc_rebalance(results, {"A": 100})
        assert actions == []

    def test_weights_in_result(self):
        results = [_make_result("A", 6000), _make_result("B", 4000)]
        target = {"A": 80, "B": 20}
        actions = calc_rebalance(results, target)
        action_a = next(a for a in actions if a["security"] == "A")
        assert abs(action_a["current_weight"] - 60.0) < 0.01
        assert action_a["target_weight"] == 80
