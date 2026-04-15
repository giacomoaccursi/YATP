"""Tests for portfolio.summary module."""

import pandas as pd
from portfolio.summary import build_summary


def _make_df(rows):
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    for col in ["Shares", "Quote", "Net Transaction Value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


MIXED_TRANSACTIONS = [
    {"Date": "2025-01-01", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-02-01", "Type": "Buy", "Security": "ETF_A", "Shares": 5, "Quote": 120, "Net Transaction Value": 600},
    {"Date": "2025-03-01", "Type": "Sell", "Security": "ETF_A", "Shares": 3, "Quote": 130, "Net Transaction Value": 390},
    {"Date": "2025-06-15", "Type": "Dividend", "Security": "ETF_A", "Shares": 0, "Quote": 0, "Net Transaction Value": 25},
    {"Date": "2025-01-01", "Type": "Buy", "Security": "GOLD", "Shares": 5, "Quote": 80, "Net Transaction Value": 400},
]


class TestBuildSummary:
    def test_total_transactions(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        assert summary.total_transactions == 5

    def test_total_invested(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        assert summary.total_invested == 2000  # 1000 + 600 + 400

    def test_total_sold(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        assert summary.total_sold == 390

    def test_total_income(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        assert summary.total_income == 25

    def test_net_invested(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        assert summary.net_invested == 2000 - 390

    def test_instrument_count(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        assert len(summary.instruments) == 2

    def test_instrument_buys_sells(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        etf = next(i for i in summary.instruments if i.security == "ETF_A")
        assert etf.total_buys == 2
        assert etf.total_sells == 1
        assert etf.total_dividends == 1

    def test_instrument_shares_held(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        etf = next(i for i in summary.instruments if i.security == "ETF_A")
        assert etf.shares_held == 12  # 10 + 5 - 3

    def test_instrument_avg_cost(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        gold = next(i for i in summary.instruments if i.security == "GOLD")
        assert gold.avg_cost_per_share == 80

    def test_instrument_dates(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        etf = next(i for i in summary.instruments if i.security == "ETF_A")
        assert etf.first_transaction.strftime("%Y-%m-%d") == "2025-01-01"
        assert etf.last_transaction.strftime("%Y-%m-%d") == "2025-06-15"

    def test_no_sells_instrument(self):
        summary = build_summary(_make_df(MIXED_TRANSACTIONS))
        gold = next(i for i in summary.instruments if i.security == "GOLD")
        assert gold.total_sells == 0
        assert gold.total_sold == 0
