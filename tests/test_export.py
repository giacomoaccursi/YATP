"""Tests for portfolio.export module."""

import json
import pytest
from datetime import datetime
from portfolio.export import export_json


def _make_results():
    return [{
        "security": "ETF_A",
        "ticker": "X.DE",
        "isin": "IE00TEST",
        "capital_gains_rate": 0.26,
        "data": {
            "shares_held": 10,
            "avg_cost_per_share": 100,
            "cost_basis": 1000,
            "realized_pnl": 50,
            "cashflows": [(datetime(2025, 1, 1), -1000)],
        },
        "analysis": {
            "market_value": 1200,
            "unrealized_pnl": 200,
            "total_pnl": 250,
            "simple_return": 20.0,
            "twr": 0.20,
            "xirr": 0.25,
            "estimated_tax": 52.0,
            "net_after_tax": 148.0,
        },
    }]


def _make_summary():
    return {
        "cost": 1000, "market_value": 1200,
        "unrealized": 200, "realized": 50,
        "total_pnl": 250, "simple_return": 20.0,
        "xirr": 0.25, "tax": 52.0, "net_after_tax": 148.0,
        "allocations": {"ETF_A": 100.0},
        "allocations_by_asset_class": {"ETF": 100.0},
    }


def _make_history():
    return [
        {"period": "1 month", "available": True, "past_date": datetime(2025, 3, 1),
         "market_gain": 50, "simple_return": 5.0, "twr": 0.04, "mwrr": 4.5},
        {"period": "1 year", "available": False},
    ]


class TestExportJson:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), {"country": "IT", "regime": "amministrato"})
        assert (tmp_path / "report.json").exists()

    def test_valid_json(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), {"country": "IT", "regime": "amministrato"})
        with open(path) as f:
            report = json.load(f)
        assert "generated_at" in report
        assert "instruments" in report
        assert "portfolio" in report
        assert "history" in report

    def test_instrument_fields(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), {"country": "IT", "regime": "amministrato"})
        with open(path) as f:
            report = json.load(f)
        instrument = report["instruments"][0]
        assert instrument["security"] == "ETF_A"
        assert instrument["isin"] == "IE00TEST"
        assert instrument["ticker"] == "X.DE"
        assert instrument["shares_held"] == 10
        assert instrument["market_value"] == 1200

    def test_history_unavailable_period(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), _make_history(), {"country": "IT", "regime": "amministrato"})
        with open(path) as f:
            report = json.load(f)
        unavailable = [p for p in report["history"] if not p["available"]]
        assert len(unavailable) == 1
        assert unavailable[0]["period"] == "1 year"

    def test_none_summary(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), None, _make_history(), {"country": "IT", "regime": "amministrato"})
        with open(path) as f:
            report = json.load(f)
        assert report["portfolio"] is None

    def test_none_history(self, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(path, _make_results(), _make_summary(), None, {"country": "IT", "regime": "amministrato"})
        with open(path) as f:
            report = json.load(f)
        assert report["history"] is None
