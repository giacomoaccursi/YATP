"""Tests for portfolio.analysis module."""

import pytest
from datetime import datetime
from portfolio.analysis import analyze_instrument, analyze_portfolio


def _make_instrument_data(shares=10, avg_cost=100, cost_basis=1000, realized_pnl=0):
    """Helper to create instrument data dict."""
    return {
        "shares_held": shares,
        "avg_cost_per_share": avg_cost,
        "cost_basis": cost_basis,
        "realized_pnl": realized_pnl,
        "cashflows": [(datetime(2025, 1, 1), -cost_basis)],
        "twr_txns": [(datetime(2025, 1, 1), "buy", avg_cost)],
    }


# ── analyze_instrument ──

class TestAnalyzeInstrument:
    def test_market_value(self):
        data = _make_instrument_data(shares=10)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert result["market_value"] == 1200

    def test_unrealized_pnl(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert result["unrealized_pnl"] == 200

    def test_total_pnl_includes_realized(self):
        data = _make_instrument_data(shares=10, cost_basis=1000, realized_pnl=50)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert result["total_pnl"] == 250  # 200 unrealized + 50 realized

    def test_estimated_tax_on_gain(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert abs(result["estimated_tax"] - 52.0) < 0.01  # 26% of 200

    def test_no_tax_on_loss(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=80, capital_gains_rate=0.26)
        assert result["estimated_tax"] == 0

    def test_net_after_tax(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert abs(result["net_after_tax"] - 148.0) < 0.01  # 200 - 52

    def test_simple_return(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert abs(result["simple_return"] - 20.0) < 0.01

    def test_xirr_is_calculated(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert result["xirr"] is not None

    def test_twr_is_calculated(self):
        data = _make_instrument_data(shares=10, cost_basis=1000)
        result = analyze_instrument(data, current_price=120, capital_gains_rate=0.26)
        assert result["twr"] is not None


# ── analyze_portfolio ──

class TestAnalyzePortfolio:
    def _make_results(self):
        data_a = _make_instrument_data(shares=10, cost_basis=1000, realized_pnl=50)
        data_b = _make_instrument_data(shares=5, avg_cost=80, cost_basis=400, realized_pnl=0)
        analysis_a = analyze_instrument(data_a, current_price=120, capital_gains_rate=0.26)
        analysis_b = analyze_instrument(data_b, current_price=90, capital_gains_rate=0.26)
        instruments = {
            "ETF_A": {"type": "ETF"},
            "GOLD": {"type": "ETC"},
        }
        results = [
            {"security": "ETF_A", "data": data_a, "analysis": analysis_a, "ticker": "X.DE", "capital_gains_rate": 0.26},
            {"security": "GOLD", "data": data_b, "analysis": analysis_b, "ticker": "Y.DE", "capital_gains_rate": 0.26},
        ]
        return results, instruments

    def test_total_cost(self):
        results, instruments = self._make_results()
        summary = analyze_portfolio(results, instruments)
        assert summary["cost"] == 1400

    def test_total_market_value(self):
        results, instruments = self._make_results()
        summary = analyze_portfolio(results, instruments)
        assert summary["market_value"] == 1200 + 450  # 10*120 + 5*90

    def test_total_pnl(self):
        results, instruments = self._make_results()
        summary = analyze_portfolio(results, instruments)
        unrealized = (1200 - 1000) + (450 - 400)
        realized = 50
        assert abs(summary["total_pnl"] - (unrealized + realized)) < 0.01

    def test_allocations_present(self):
        results, instruments = self._make_results()
        summary = analyze_portfolio(results, instruments)
        assert "allocations" in summary
        assert "ETF_A" in summary["allocations"]
        assert "GOLD" in summary["allocations"]

    def test_allocations_by_asset_class_present(self):
        results, instruments = self._make_results()
        summary = analyze_portfolio(results, instruments)
        assert "allocations_by_asset_class" in summary
        assert "ETF" in summary["allocations_by_asset_class"]
        assert "ETC" in summary["allocations_by_asset_class"]

    def test_xirr_present(self):
        results, instruments = self._make_results()
        summary = analyze_portfolio(results, instruments)
        assert summary["xirr"] is not None
