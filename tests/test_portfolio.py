"""Tests for portfolio.portfolio module."""

import pandas as pd
import pytest
from datetime import datetime
from portfolio.portfolio import (
    build_portfolio, get_holdings_at, get_cost_basis_at,
    value_holdings, get_cashflows_between, get_net_new_money_between,
)


def _make_df(rows):
    """Helper to create a transactions DataFrame from a list of dicts."""
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Shares"] = pd.to_numeric(df["Shares"])
    df["Quote"] = pd.to_numeric(df["Quote"])
    df["Net Transaction Value"] = pd.to_numeric(df["Net Transaction Value"])
    return df


SIMPLE_BUY = [
    {"Date": "2025-01-01", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
]

TWO_BUYS = [
    {"Date": "2025-01-01", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-02-01", "Type": "Buy", "Security": "ETF_A", "Shares": 5, "Quote": 120, "Net Transaction Value": 600},
]

BUY_AND_SELL = [
    {"Date": "2025-01-01", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-02-01", "Type": "Buy", "Security": "ETF_A", "Shares": 5, "Quote": 120, "Net Transaction Value": 600},
    {"Date": "2025-03-01", "Type": "Sell", "Security": "ETF_A", "Shares": 8, "Quote": 130, "Net Transaction Value": 1040},
]

TWO_INSTRUMENTS = [
    {"Date": "2025-01-01", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-01-01", "Type": "Buy", "Security": "GOLD", "Shares": 5, "Quote": 80, "Net Transaction Value": 400},
]


# ── build_portfolio ──

class TestBuildPortfolio:
    def test_single_buy(self):
        portfolio = build_portfolio(_make_df(SIMPLE_BUY))
        assert "ETF_A" in portfolio
        p = portfolio["ETF_A"]
        assert p.shares_held == 10
        assert p.cost_basis == 1000
        assert p.avg_cost_per_share == 100
        assert p.realized_pnl == 0

    def test_two_buys_avg_cost(self):
        portfolio = build_portfolio(_make_df(TWO_BUYS))
        p = portfolio["ETF_A"]
        assert p.shares_held == 15
        assert p.cost_basis == 1600
        assert abs(p.avg_cost_per_share - 1600 / 15) < 0.01

    def test_buy_and_sell_progressive_cost(self):
        """Sell uses cost basis at time of sale, not global average."""
        portfolio = build_portfolio(_make_df(BUY_AND_SELL))
        p = portfolio["ETF_A"]
        assert p.shares_held == 7  # 15 - 8
        avg_at_sell = 1600 / 15  # ~106.67
        expected_realized = 1040 - (avg_at_sell * 8)
        assert abs(p.realized_pnl - expected_realized) < 0.01

    def test_two_instruments_separate(self):
        portfolio = build_portfolio(_make_df(TWO_INSTRUMENTS))
        assert "ETF_A" in portfolio
        assert "GOLD" in portfolio
        assert portfolio["ETF_A"].shares_held == 10
        assert portfolio["GOLD"].shares_held == 5

    def test_cashflows_signs(self):
        """Buys are negative cashflows, sells are positive."""
        portfolio = build_portfolio(_make_df(BUY_AND_SELL))
        cashflows = portfolio["ETF_A"].cashflows
        assert cashflows[0][1] < 0  # first buy
        assert cashflows[1][1] < 0  # second buy
        assert cashflows[2][1] > 0  # sell

    def test_sell_all_shares(self):
        rows = [
            {"Date": "2025-01-01", "Type": "Buy", "Security": "X", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
            {"Date": "2025-02-01", "Type": "Sell", "Security": "X", "Shares": 10, "Quote": 110, "Net Transaction Value": 1100},
        ]
        portfolio = build_portfolio(_make_df(rows))
        p = portfolio["X"]
        assert p.shares_held == 0
        assert abs(p.realized_pnl - 100) < 0.01


# ── get_holdings_at ──

class TestGetHoldingsAt:
    def test_before_any_transaction(self):
        df = _make_df(SIMPLE_BUY)
        holdings = get_holdings_at(pd.Timestamp("2024-12-01"), df)
        assert len(holdings) == 0

    def test_after_buy(self):
        df = _make_df(SIMPLE_BUY)
        holdings = get_holdings_at(pd.Timestamp("2025-01-15"), df)
        assert holdings["ETF_A"] == 10

    def test_after_partial_sell(self):
        df = _make_df(BUY_AND_SELL)
        holdings = get_holdings_at(pd.Timestamp("2025-03-15"), df)
        assert holdings["ETF_A"] == 7


# ── get_cost_basis_at ──

class TestGetCostBasisAt:
    def test_after_single_buy(self):
        df = _make_df(SIMPLE_BUY)
        cost = get_cost_basis_at(pd.Timestamp("2025-01-15"), df)
        assert cost == 1000

    def test_after_two_buys(self):
        df = _make_df(TWO_BUYS)
        cost = get_cost_basis_at(pd.Timestamp("2025-02-15"), df)
        assert cost == 1600

    def test_after_sell_reduces_cost(self):
        df = _make_df(BUY_AND_SELL)
        cost = get_cost_basis_at(pd.Timestamp("2025-03-15"), df)
        avg_at_sell = 1600 / 15
        expected = 1600 - (avg_at_sell * 8)
        assert abs(cost - expected) < 0.01

    def test_before_any_transaction(self):
        df = _make_df(SIMPLE_BUY)
        cost = get_cost_basis_at(pd.Timestamp("2024-01-01"), df)
        assert cost == 0


# ── value_holdings ──

class TestValueHoldings:
    def test_single_holding(self):
        holdings = {"ETF_A": 10}
        prices = pd.Series([100, 105, 110], index=pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]))
        price_histories = {"ETF_A": prices}
        value = value_holdings(holdings, price_histories, pd.Timestamp("2025-01-02"))
        assert value == 10 * 105

    def test_missing_instrument(self):
        holdings = {"UNKNOWN": 10}
        value = value_holdings(holdings, {}, pd.Timestamp("2025-01-01"))
        assert value == 0

    def test_no_price_before_date(self):
        holdings = {"ETF_A": 10}
        prices = pd.Series([100], index=pd.to_datetime(["2025-06-01"]))
        price_histories = {"ETF_A": prices}
        value = value_holdings(holdings, price_histories, pd.Timestamp("2025-01-01"))
        assert value == 0


# ── get_cashflows_between ──

class TestGetCashflowsBetween:
    def test_filters_by_date(self):
        df = _make_df(BUY_AND_SELL)
        cashflows = get_cashflows_between(pd.Timestamp("2025-01-15"), pd.Timestamp("2025-02-15"), df)
        assert len(cashflows) == 1
        assert cashflows[0][1] < 0  # buy is negative

    def test_empty_period(self):
        df = _make_df(SIMPLE_BUY)
        cashflows = get_cashflows_between(pd.Timestamp("2025-06-01"), pd.Timestamp("2025-07-01"), df)
        assert len(cashflows) == 0

    def test_sell_is_positive(self):
        df = _make_df(BUY_AND_SELL)
        cashflows = get_cashflows_between(pd.Timestamp("2025-02-15"), pd.Timestamp("2025-03-15"), df)
        assert len(cashflows) == 1
        assert cashflows[0][1] > 0  # sell is positive


# ── get_net_new_money_between ──

class TestGetNetNewMoneyBetween:
    def test_buys_only(self):
        df = _make_df(TWO_BUYS)
        net = get_net_new_money_between(pd.Timestamp("2025-01-15"), pd.Timestamp("2025-02-15"), df)
        assert net == 600

    def test_sell_reduces_net(self):
        df = _make_df(BUY_AND_SELL)
        net = get_net_new_money_between(pd.Timestamp("2024-12-01"), pd.Timestamp("2025-03-15"), df)
        assert net == 1000 + 600 - 1040

    def test_empty_period(self):
        df = _make_df(SIMPLE_BUY)
        net = get_net_new_money_between(pd.Timestamp("2025-06-01"), pd.Timestamp("2025-07-01"), df)
        assert net == 0
