"""Tests for portfolio.loader module."""

import pytest
import json
import os
from portfolio.loader import load_config, load_transactions


@pytest.fixture
def tmp_config(tmp_path):
    """Create a temporary config file."""
    config = {"tax": {"country": "IT", "regime": "amministrato"}, "instruments": {}}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return str(path)


@pytest.fixture
def tmp_csv(tmp_path):
    """Create a temporary transactions CSV."""
    csv_content = """Date,Type,Security,Shares,Quote,Net Transaction Value
2025-01-01,Buy,ETF_A,10,100,1000
2025-02-01,Sell,ETF_A,5,110,550"""
    path = tmp_path / "transactions.csv"
    path.write_text(csv_content)
    return str(path)


class TestLoadConfig:
    def test_valid_config(self, tmp_config):
        config = load_config(tmp_config)
        assert config["tax"]["country"] == "IT"

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.json")

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json")
        with pytest.raises(ValueError):
            load_config(str(path))


class TestLoadTransactions:
    def test_valid_csv(self, tmp_csv):
        df = load_transactions(tmp_csv)
        assert len(df) == 2
        assert "Date" in df.columns
        assert df["Shares"].dtype in ["float64", "int64"]

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_transactions("nonexistent.csv")

    def test_missing_columns(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("Date,Type\n2025-01-01,Buy")
        with pytest.raises(ValueError):
            load_transactions(str(path))

    def test_column_stripping(self, tmp_path):
        csv_content = """ Date , Type , Security , Shares , Quote , Net Transaction Value
2025-01-01,Buy,ETF_A,10,100,1000"""
        path = tmp_path / "spaces.csv"
        path.write_text(csv_content)
        df = load_transactions(str(path))
        assert "Date" in df.columns
        assert len(df) == 1
