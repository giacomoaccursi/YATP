"""Tests for web.data module — portfolio history, instrument history, daily change."""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from web.history_service import load_portfolio_history, load_instrument_history, load_portfolio_daily_change
from web.cache import clear_all_caches as clear_price_cache
from portfolio.portfolio import value_holdings
from portfolio.engine import PortfolioEngine


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before each test."""
    clear_price_cache()
    yield
    clear_price_cache()


# ── Helpers ──

def _make_df(rows):
    """Create a transactions DataFrame from a list of dicts."""
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Shares"] = pd.to_numeric(df["Shares"])
    df["Quote"] = pd.to_numeric(df.get("Quote", 0))
    df["Net Transaction Value"] = pd.to_numeric(df["Net Transaction Value"])
    return df


def _make_price_series(prices_dict):
    """Create a price Series from {date_str: price}."""
    dates = pd.to_datetime(list(prices_dict.keys()))
    return pd.Series(list(prices_dict.values()), index=dates)


SIMPLE_BUY = [
    {"Date": "2025-01-02", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
]

TWO_BUYS = [
    {"Date": "2025-01-02", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-01-15", "Type": "Buy", "Security": "ETF_A", "Shares": 5, "Quote": 120, "Net Transaction Value": 600},
]

BUY_AND_SELL_ALL = [
    {"Date": "2025-01-02", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-01-10", "Type": "Sell", "Security": "ETF_A", "Shares": 10, "Quote": 110, "Net Transaction Value": 1100},
]

TWO_INSTRUMENTS = [
    {"Date": "2025-01-02", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
    {"Date": "2025-01-02", "Type": "Buy", "Security": "GOLD", "Shares": 5, "Quote": 80, "Net Transaction Value": 400},
]


# ── PortfolioEngine ──

class TestPortfolioEngine:
    def test_buy_tracks_holdings(self):
        engine = PortfolioEngine(_make_df(SIMPLE_BUY), {}, market_dates=[pd.Timestamp("2025-01-02")])
        assert engine.holdings_at(0)["ETF_A"] == 10

    def test_sell_removes_shares(self):
        engine = PortfolioEngine(_make_df(BUY_AND_SELL_ALL), {}, market_dates=[pd.Timestamp("2025-01-10")])
        assert len(engine.holdings_at(0)) == 0

    def test_cost_basis_tracked(self):
        engine = PortfolioEngine(_make_df(SIMPLE_BUY), {}, market_dates=[pd.Timestamp("2025-01-02")])
        assert engine.cost_basis_at(0) == 1000.0

    def test_realized_pnl(self):
        engine = PortfolioEngine(_make_df(BUY_AND_SELL_ALL), {}, market_dates=[pd.Timestamp("2025-01-10")])
        assert engine.realized_pnl() == 100.0  # sold at 110, cost was 100

    def test_dividend_tracked_as_income(self):
        rows = SIMPLE_BUY + [{"Date": "2025-06-01", "Type": "Dividend", "Security": "ETF_A", "Shares": 0, "Quote": 0, "Net Transaction Value": 50}]
        engine = PortfolioEngine(_make_df(rows), {}, market_dates=[pd.Timestamp("2025-06-01")])
        assert engine.total_income() == 50.0


# ── value_holdings ──

class TestValueHoldingsAt:
    def test_single_holding(self):
        holdings = {"ETF_A": 10}
        prices = {"ETF_A": _make_price_series({"2025-01-02": 100, "2025-01-03": 105})}
        assert value_holdings(holdings, prices, pd.Timestamp("2025-01-03")) == 1050

    def test_uses_latest_available_price(self):
        holdings = {"ETF_A": 10}
        prices = {"ETF_A": _make_price_series({"2025-01-02": 100})}
        # Date after last price — should use last available
        assert value_holdings(holdings, prices, pd.Timestamp("2025-01-05")) == 1000

    def test_no_price_available(self):
        holdings = {"ETF_A": 10}
        prices = {"ETF_A": _make_price_series({"2025-06-01": 100})}
        assert value_holdings(holdings, prices, pd.Timestamp("2025-01-01")) == 0

    def test_empty_holdings(self):
        assert value_holdings({}, {}, pd.Timestamp("2025-01-01")) == 0

    def test_multiple_holdings(self):
        holdings = {"ETF_A": 10, "GOLD": 5}
        prices = {
            "ETF_A": _make_price_series({"2025-01-02": 100}),
            "GOLD": _make_price_series({"2025-01-02": 80}),
        }
        assert value_holdings(holdings, prices, pd.Timestamp("2025-01-02")) == 1400


# ── load_portfolio_history (mocked) ──

class TestLoadPortfolioHistory:
    """Test with mocked config, transactions, and price fetching."""

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_simple_buy_history(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 105, "2025-01-06": 110,
        })

        result = load_portfolio_history("config.json", "transactions.csv")

        assert len(result["dates"]) == 3
        assert result["values"][0] == 1000.0  # 10 * 100
        assert result["values"][1] == 1050.0  # 10 * 105
        assert result["values"][2] == 1100.0  # 10 * 110
        assert result["costs"] == [1000.0, 1000.0, 1000.0]

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_return_pcts_calculated(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 110,
        })

        result = load_portfolio_history("config.json", "transactions.csv")

        assert result["return_pcts"][0] == 0.0  # (1000-1000)/1000 = 0%
        assert result["return_pcts"][1] == 10.0  # (1100-1000)/1000 = 10%

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_sell_all_shows_zero(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(BUY_AND_SELL_ALL)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-06": 105,
            "2025-01-10": 110, "2025-01-13": 112,
        })

        result = load_portfolio_history("config.json", "transactions.csv")

        # After selling all on Jan 10, values should be 0
        idx_after_sell = result["dates"].index("2025-01-13")
        assert result["values"][idx_after_sell] == 0.0
        assert result["costs"][idx_after_sell] == 0.0

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_cost_tracks_buys(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(TWO_BUYS)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-06": 105,
            "2025-01-15": 120, "2025-01-16": 125,
        })

        result = load_portfolio_history("config.json", "transactions.csv")

        # Before second buy: cost = 1000
        idx_before = result["dates"].index("2025-01-06")
        assert result["costs"][idx_before] == 1000.0

        # After second buy: cost = 1600
        idx_after = result["dates"].index("2025-01-16")
        assert result["costs"][idx_after] == 1600.0

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_empty_prices_returns_empty(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = None

        result = load_portfolio_history("config.json", "transactions.csv")
        assert result == {"dates": [], "values": [], "costs": [], "return_pcts": [], "total_return_pcts": [], "twr_pcts": [], "drawdown_pcts": []}


# ── load_instrument_history (mocked) ──

class TestLoadInstrumentHistory:
    @patch("web.history_service.load_config")
    @patch("web.history_service.load_transactions")
    @patch("web.history_service.get_cached_price_history")
    def test_price_and_cost_avg(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 110,
        })

        result = load_instrument_history("config.json", "transactions.csv", "ETF_A")

        assert result["prices"] == [100.0, 110.0]
        assert result["cost_avg"] == [100.0, 100.0]  # avg cost stays 100
        assert result["pnl"][0] == 0.0  # (10*100 - 1000) = 0
        assert result["pnl"][1] == 100.0  # (10*110 - 1000) = 100

    @patch("web.history_service.load_config")
    @patch("web.history_service.load_transactions")
    @patch("web.history_service.get_cached_price_history")
    def test_two_buys_avg_cost_changes(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(TWO_BUYS)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-06": 105,
            "2025-01-15": 120, "2025-01-16": 125,
        })

        result = load_instrument_history("config.json", "transactions.csv", "ETF_A")

        # Before second buy: avg = 100
        idx_before = result["dates"].index("2025-01-06")
        assert result["cost_avg"][idx_before] == 100.0

        # After second buy: avg = 1600/15 = 106.6667
        idx_after = result["dates"].index("2025-01-16")
        assert abs(result["cost_avg"][idx_after] - 106.6667) < 0.01

    @patch("web.history_service.load_config")
    @patch("web.history_service.load_transactions")
    @patch("web.history_service.get_cached_price_history")
    def test_sell_all_skips_zero_holding_days(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(BUY_AND_SELL_ALL)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-06": 105,
            "2025-01-10": 110, "2025-01-13": 115,
        })

        result = load_instrument_history("config.json", "transactions.csv", "ETF_A")

        # Days after sell should not appear
        assert "2025-01-13" not in result["dates"]

    @patch("web.history_service.load_config")
    def test_unknown_instrument_returns_none(self, mock_config):
        mock_config.return_value = {"instruments": {}}
        result = load_instrument_history("config.json", "transactions.csv", "UNKNOWN")
        assert result is None

    @patch("web.history_service.load_config")
    @patch("web.history_service.load_transactions")
    @patch("web.history_service.get_cached_price_history")
    def test_no_transactions_returns_empty(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        # Filter will find no transactions for GOLD
        mock_fetch.return_value = _make_price_series({"2025-01-02": 80})

        result = load_instrument_history("config.json", "transactions.csv", "GOLD")
        # GOLD not in config instruments, so returns None
        assert result is None


# ── load_portfolio_daily_change (mocked) ──

class TestLoadPortfolioDailyChange:
    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_positive_change(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 110,
        })

        result = load_portfolio_daily_change("config.json", "transactions.csv")

        assert result is not None
        assert result["amount"] == 100.0  # 10 * (110-100)
        assert result["pct"] == 10.0

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_negative_change(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 95,
        })

        result = load_portfolio_daily_change("config.json", "transactions.csv")

        assert result is not None
        assert result["amount"] == -50.0  # 10 * (95-100)
        assert result["pct"] == -5.0

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_no_prices_returns_none(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = None

        result = load_portfolio_daily_change("config.json", "transactions.csv")
        assert result is None

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_single_day_returns_none(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({"2025-01-02": 100})

        result = load_portfolio_daily_change("config.json", "transactions.csv")
        assert result is None

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    def test_empty_transactions_returns_none(self, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {}}
        mock_txns.return_value = pd.DataFrame(columns=["Date", "Type", "Security", "Shares", "Quote", "Net Transaction Value"])

        result = load_portfolio_daily_change("config.json", "transactions.csv")
        assert result is None


# ── Serializer tests ──

class TestSerializers:
    def test_period_to_dict_available(self):
        from web.serializers import period_to_dict
        from portfolio.models import PeriodPerformance
        p = PeriodPerformance(period="1 month", available=True, market_gain=100, simple_return=5.0, twr=0.05, mwrr=4.8)
        d = period_to_dict(p)
        assert d["period"] == "1 month"
        assert d["available"] is True
        assert d["twr"] == 5.0  # 0.05 * 100
        assert d["mwrr"] == 4.8  # already percentage

    def test_period_to_dict_unavailable(self):
        from web.serializers import period_to_dict
        from portfolio.models import PeriodPerformance
        p = PeriodPerformance(period="1 year", available=False)
        d = period_to_dict(p)
        assert d["available"] is False
        assert d["twr"] is None

    def test_instrument_to_dict_with_daily_change(self):
        from web.serializers import instrument_to_dict
        from portfolio.models import InstrumentResult, InstrumentData, InstrumentAnalysis
        data = InstrumentData(shares_held=10, avg_cost_per_share=100, cost_basis=1000, realized_pnl=0)
        analysis = InstrumentAnalysis(
            market_value=1100, unrealized_pnl=100, total_pnl=100,
            simple_return=10, twr=0.1, xirr=0.12, estimated_tax=26, net_after_tax=1074,
        )
        r = InstrumentResult(security="ETF_A", ticker="ETF.A", isin="IE000", capital_gains_rate=0.26, data=data, analysis=analysis)
        d = instrument_to_dict(r, daily_change=1.5)
        assert d["daily_change"] == 1.5

    def test_instrument_to_dict_without_daily_change(self):
        from web.serializers import instrument_to_dict
        from portfolio.models import InstrumentResult, InstrumentData, InstrumentAnalysis
        data = InstrumentData(shares_held=10, avg_cost_per_share=100, cost_basis=1000, realized_pnl=0)
        analysis = InstrumentAnalysis(
            market_value=1100, unrealized_pnl=100, total_pnl=100,
            simple_return=10, twr=0.1, xirr=0.12, estimated_tax=26, net_after_tax=1074,
        )
        r = InstrumentResult(security="ETF_A", ticker="ETF.A", isin="IE000", capital_gains_rate=0.26, data=data, analysis=analysis)
        d = instrument_to_dict(r)
        assert d["daily_change"] is None


# ── Additional edge cases ──

class TestPortfolioEngineEdgeCases:
    def test_multiple_instruments_same_day(self):
        engine = PortfolioEngine(_make_df(TWO_INSTRUMENTS), {}, market_dates=[pd.Timestamp("2025-01-02")])
        h = engine.holdings_at(0)
        assert h["ETF_A"] == 10
        assert h["GOLD"] == 5

    def test_two_buys_cost_basis(self):
        engine = PortfolioEngine(_make_df(TWO_BUYS), {}, market_dates=[pd.Timestamp("2025-01-15")])
        assert engine.cost_basis_at(0) == 1600.0


class TestLoadPortfolioHistoryEdgeCases:
    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_two_instruments(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {
            "instruments": {"ETF_A": {"ticker": "ETF.A"}, "GOLD": {"ticker": "GOLD.X"}}
        }
        mock_txns.return_value = _make_df(TWO_INSTRUMENTS)

        def side_effect(ticker, start, end, instrument_type=None, isin=None):
            if ticker == "ETF.A":
                return _make_price_series({"2025-01-02": 100, "2025-01-03": 110})
            return _make_price_series({"2025-01-02": 80, "2025-01-03": 85})

        mock_fetch.side_effect = side_effect

        result = load_portfolio_history("config.json", "transactions.csv")

        # Day 1: 10*100 + 5*80 = 1400
        assert result["values"][0] == 1400.0
        # Day 2: 10*110 + 5*85 = 1525
        assert result["values"][1] == 1525.0
        # Cost stays 1400
        assert result["costs"][0] == 1400.0
        assert result["costs"][1] == 1400.0

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_partial_sell_cost_tracking(self, mock_fetch, mock_txns, mock_config):
        rows = [
            {"Date": "2025-01-02", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
            {"Date": "2025-01-10", "Type": "Sell", "Security": "ETF_A", "Shares": 4, "Quote": 120, "Net Transaction Value": 480},
        ]
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(rows)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-06": 110,
            "2025-01-10": 120, "2025-01-13": 125,
        })

        result = load_portfolio_history("config.json", "transactions.csv")

        # After selling 4 of 10 shares: cost = 1000 - (1000/10)*4 = 600
        idx_after = result["dates"].index("2025-01-13")
        assert result["costs"][idx_after] == 600.0
        # Value: 6 * 125 = 750
        assert result["values"][idx_after] == 750.0

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_return_pct_negative(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 90,
        })

        result = load_portfolio_history("config.json", "transactions.csv")

        # (900 - 1000) / 1000 = -10%
        assert result["return_pcts"][1] == -10.0


class TestLoadInstrumentHistoryEdgeCases:
    @patch("web.history_service.load_config")
    @patch("web.history_service.load_transactions")
    @patch("web.history_service.get_cached_price_history")
    def test_partial_sell_recalculates_avg(self, mock_fetch, mock_txns, mock_config):
        rows = [
            {"Date": "2025-01-02", "Type": "Buy", "Security": "ETF_A", "Shares": 10, "Quote": 100, "Net Transaction Value": 1000},
            {"Date": "2025-01-10", "Type": "Sell", "Security": "ETF_A", "Shares": 4, "Quote": 120, "Net Transaction Value": 480},
        ]
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(rows)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-06": 110,
            "2025-01-10": 120, "2025-01-13": 125,
        })

        result = load_instrument_history("config.json", "transactions.csv", "ETF_A")

        # After sell: avg cost stays 100 (sell doesn't change avg cost per share)
        idx_after = result["dates"].index("2025-01-13")
        assert result["cost_avg"][idx_after] == 100.0
        # P&L: 6 * 125 - 600 = 150
        assert result["pnl"][idx_after] == 150.0

    @patch("web.history_service.load_config")
    @patch("web.history_service.load_transactions")
    @patch("web.history_service.get_cached_price_history")
    def test_instrument_in_config_no_transactions(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"GOLD": {"ticker": "GOLD.X"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)  # Only ETF_A transactions
        mock_fetch.return_value = _make_price_series({"2025-01-02": 80})

        result = load_instrument_history("config.json", "transactions.csv", "GOLD")

        assert result == {
            "dates": [], "prices": [], "cost_avg": [], "pnl": [],
            "values": [], "costs": [], "return_pcts": [],
            "total_return_pcts": [], "twr_pcts": [],
            "drawdown_pcts": [],
        }


class TestLoadPortfolioDailyChangeEdgeCases:
    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_two_instruments(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {
            "instruments": {"ETF_A": {"ticker": "ETF.A"}, "GOLD": {"ticker": "GOLD.X"}}
        }
        mock_txns.return_value = _make_df(TWO_INSTRUMENTS)

        def side_effect(ticker, start, end, instrument_type=None, isin=None):
            if ticker == "ETF.A":
                return _make_price_series({"2025-01-02": 100, "2025-01-03": 105})
            return _make_price_series({"2025-01-02": 80, "2025-01-03": 82})

        mock_fetch.side_effect = side_effect

        result = load_portfolio_daily_change("config.json", "transactions.csv")

        # Day 1: 10*100 + 5*80 = 1400, Day 2: 10*105 + 5*82 = 1460
        assert result is not None
        assert result["amount"] == 60.0
        assert abs(result["pct"] - (60 / 1400 * 100)) < 0.01

    @patch("web.portfolio_service.load_config")
    @patch("web.portfolio_service.load_transactions")
    @patch("web.portfolio_service.get_cached_price_history")
    def test_zero_change(self, mock_fetch, mock_txns, mock_config):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A"}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_fetch.return_value = _make_price_series({
            "2025-01-02": 100, "2025-01-03": 100,
        })

        result = load_portfolio_daily_change("config.json", "transactions.csv")

        assert result is not None
        assert result["amount"] == 0.0
        assert result["pct"] == 0.0


# ── Serializer edge cases ──

class TestSerializerEdgeCases:
    def test_rebalance_to_dict_includes_values(self):
        from web.serializers import rebalance_to_dict
        from portfolio.models import RebalanceAction
        action = RebalanceAction(
            asset_class="ETF", current_weight=60.0, target_weight=80.0,
            current_value=6000.0, target_value=8000.0, difference=2000.0,
        )
        d = rebalance_to_dict(action)
        assert d["current_value"] == 6000.0
        assert d["target_value"] == 8000.0
        assert d["difference"] == 2000.0

    def test_summary_to_dict_with_none_xirr(self):
        from web.serializers import summary_to_dict
        from portfolio.models import PortfolioSummary
        s = PortfolioSummary(
            cost=1000, market_value=1100, unrealized=100, realized=0,
            tax=26, total_pnl=100, simple_return=10, xirr=None,
            net_after_tax=1074, allocations={"ETF_A": 100.0},
            allocations_by_asset_class={"ETF": 100.0},
        )
        d = summary_to_dict(s)
        assert d["xirr"] is None
        assert d["market_value"] == 1100.0
        assert d["allocations"] == {"ETF_A": 100.0}

    def test_summary_to_dict_with_xirr(self):
        from web.serializers import summary_to_dict
        from portfolio.models import PortfolioSummary
        s = PortfolioSummary(
            cost=1000, market_value=1100, unrealized=100, realized=0,
            tax=26, total_pnl=100, simple_return=10, xirr=0.12,
            net_after_tax=1074, allocations={}, allocations_by_asset_class={},
        )
        d = summary_to_dict(s)
        assert d["xirr"] == 12.0  # 0.12 * 100


# ── simulate_rebalance and compute_net_transaction_value ──

from web.rebalance_service import simulate_rebalance
from web.transaction_service import compute_net_transaction_value


class TestComputeNetTransactionValue:
    def test_buy(self):
        assert compute_net_transaction_value("Buy", 10, 100, 5, 0) == 1005.0

    def test_sell(self):
        assert compute_net_transaction_value("Sell", 10, 110, 5, 26) == 1069.0

    def test_zero_shares(self):
        assert compute_net_transaction_value("Buy", 0, 100, 5, 0) == 5.0

    def test_dividend_returns_zero(self):
        assert compute_net_transaction_value("Dividend", 0, 0, 0, 0) == 0.0


class TestSimulateRebalance:
    @patch("web.rebalance_service.load_portfolio_data")
    def test_with_new_investment(self, mock_load):
        from portfolio.models import InstrumentResult, InstrumentData, InstrumentAnalysis
        data = InstrumentData(shares_held=10, avg_cost_per_share=100, cost_basis=1000, realized_pnl=0)
        analysis = InstrumentAnalysis(
            market_value=1000, unrealized_pnl=0, total_pnl=0,
            simple_return=0, twr=None, xirr=None, estimated_tax=0, net_after_tax=1000,
        )
        r = InstrumentResult(security="ETF_A", ticker="ETF.A", isin=None, capital_gains_rate=0.26, data=data, analysis=analysis)
        mock_load.return_value = ([r], {}, None, {"instruments": {"ETF_A": {"type": "ETF"}}}, [])

        actions = simulate_rebalance("c.json", "t.csv", 500, {"ETF": 100})

        assert len(actions) == 1
        assert actions[0].asset_class == "ETF"
        assert actions[0].current_value == 1000.0
        # Total = 1000 + 500 = 1500, target 100% = 1500
        assert actions[0].target_value == 1500.0
        assert actions[0].difference == 500.0

    @patch("web.rebalance_service.load_portfolio_data")
    def test_empty_portfolio(self, mock_load):
        mock_load.return_value = ([], {}, None, {"instruments": {}}, [])
        actions = simulate_rebalance("c.json", "t.csv", 0, {"ETF": 100})
        assert actions == []


from web.transaction_service import simulate_sell


class TestSimulateSell:
    @patch("web.transaction_service.get_cached_price")
    @patch("web.transaction_service.load_transactions")
    @patch("web.transaction_service.load_config")
    def test_sell_with_gain(self, mock_config, mock_txns, mock_price):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A", "capital_gains_rate": 0.26}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_price.return_value = 120.0

        result = simulate_sell("c.json", "t.csv", "ETF_A", 5)

        assert result is not None
        assert result.shares_to_sell == 5
        assert result.current_price == 120.0
        assert result.avg_cost_per_share == 100.0
        assert result.gross_proceeds == 600.0
        assert result.cost_of_sold == 500.0
        assert result.gain == 100.0
        assert result.estimated_tax == 26.0
        assert result.net_proceeds == 574.0

    @patch("web.transaction_service.get_cached_price")
    @patch("web.transaction_service.load_transactions")
    @patch("web.transaction_service.load_config")
    def test_sell_with_loss_no_tax(self, mock_config, mock_txns, mock_price):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A", "capital_gains_rate": 0.26}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_price.return_value = 80.0

        result = simulate_sell("c.json", "t.csv", "ETF_A", 5)

        assert result.gain == -100.0
        assert result.estimated_tax == 0.0
        assert result.net_proceeds == 400.0

    @patch("web.transaction_service.get_cached_price")
    @patch("web.transaction_service.load_transactions")
    @patch("web.transaction_service.load_config")
    def test_sell_more_than_held_returns_none(self, mock_config, mock_txns, mock_price):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A", "capital_gains_rate": 0.26}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_price.return_value = 120.0

        result = simulate_sell("c.json", "t.csv", "ETF_A", 999)
        assert result is None

    @patch("web.transaction_service.load_config")
    def test_unknown_instrument_returns_none(self, mock_config):
        mock_config.return_value = {"instruments": {}}
        result = simulate_sell("c.json", "t.csv", "UNKNOWN", 5)
        assert result is None

    @patch("web.transaction_service.get_cached_price")
    @patch("web.transaction_service.load_transactions")
    @patch("web.transaction_service.load_config")
    def test_no_market_data_returns_none(self, mock_config, mock_txns, mock_price):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A", "capital_gains_rate": 0.26}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_price.return_value = None

        result = simulate_sell("c.json", "t.csv", "ETF_A", 5)
        assert result is None

    @patch("web.transaction_service.get_cached_price")
    @patch("web.transaction_service.load_transactions")
    @patch("web.transaction_service.load_config")
    def test_sell_zero_returns_none(self, mock_config, mock_txns, mock_price):
        mock_config.return_value = {"instruments": {"ETF_A": {"ticker": "ETF.A", "capital_gains_rate": 0.26}}}
        mock_txns.return_value = _make_df(SIMPLE_BUY)
        mock_price.return_value = 120.0

        result = simulate_sell("c.json", "t.csv", "ETF_A", 0)
        assert result is None
