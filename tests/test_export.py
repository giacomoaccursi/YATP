"""Tests for portfolio.export module."""

import json
from datetime import datetime
from portfolio.export import export_json
from portfolio.models import (
    InstrumentResult, InstrumentData, InstrumentAnalysis,
    PortfolioSummary, PeriodPerformance,
)


def _make_results():
    data = InstrumentData(
        shares_held=10, avg_cost_per_share=100, cost_basis=1000, realized_pnl=50,
        cashflows=[(datetime(2025, 1, 1), -1000)],
    )
    analysis = InstrumentAnalysis(
        market_value=1200, unrealized_pnl=200, total_pnl=250,
        simple_return=20.0, twr=0.20, xirr=0.25,
        estimated_tax=52.0, net_after_tax=148.0,
    )
    return [InstrumentResult(
        security="ETF_A", ticker="X.DE", isin="IE00TEST",
        capital_gains_rate=0.26, data=data, analysis=analysis,
    )]


def _make_summary():
    return PortfolioSummary(
        cost=1000, market_value=1200, unrealized=200, realized=50,
        tax=52.0, total_pnl=250, simple_return=20.0, xirr=0.25,
        net_after_tax=148.0, allocations={"ETF_A": 100.0},
        allocations_by_asset_class={"ETF": 100.0},
    )


def _make_history():
    return [
        PeriodPerformance(period="1 month", available=True, past_date=datetime(2025, 3, 1),
                          market_gain=50, simple_return=5.0, twr=0.04, mwrr=4.5),
        PeriodPerformance(period="1 year", available=False),
    ]


TAX_INFO = {"country": "IT", "regime": "amministrato"}


class TestExportJson:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), TAX_INFO)
        assert (tmp_path / "report.json").exists()

    def test_valid_json(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), TAX_INFO)
        with open(path) as f:
            report = json.load(f)
        assert "generated_at" in report
        assert "instruments" in report
        assert "portfolio" in report
        assert "history" in report

    def test_instrument_fields(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), TAX_INFO)
        with open(path) as f:
            instrument = json.load(f)["instruments"][0]
        assert instrument["security"] == "ETF_A"
        assert instrument["isin"] == "IE00TEST"
        assert instrument["ticker"] == "X.DE"
        assert instrument["shares_held"] == 10
        assert instrument["market_value"] == 1200

    def test_history_unavailable_period(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), TAX_INFO)
        with open(path) as f:
            unavailable = [p for p in json.load(f)["history"] if not p["available"]]
        assert len(unavailable) == 1
        assert unavailable[0]["period"] == "1 year"

    def test_none_summary(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), None, _make_history(), TAX_INFO)
        with open(path) as f:
            assert json.load(f)["portfolio"] is None

    def test_none_history(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), None, TAX_INFO)
        with open(path) as f:
            assert json.load(f)["history"] is None
