"""Tests for portfolio.returns module."""

import pytest
from datetime import datetime
from portfolio.returns import (
    calc_xirr, calc_twr, calc_simple_return,
    calc_estimated_tax, calc_period_mwrr, calc_period_twr,
)


# ── calc_simple_return ──

class TestCalcSimpleReturn:
    def test_positive_return(self):
        assert calc_simple_return(100, 1000) == 10.0

    def test_negative_return(self):
        assert calc_simple_return(-50, 1000) == -5.0

    def test_zero_pnl(self):
        assert calc_simple_return(0, 1000) == 0.0

    def test_zero_cost_basis(self):
        assert calc_simple_return(100, 0) == 0

    def test_negative_cost_basis(self):
        assert calc_simple_return(100, -500) == 0


# ── calc_estimated_tax ──

class TestCalcEstimatedTax:
    def test_positive_gain(self):
        assert calc_estimated_tax(1000, 0.26) == 260.0

    def test_negative_gain_no_tax(self):
        assert calc_estimated_tax(-500, 0.26) == 0.0

    def test_zero_gain(self):
        assert calc_estimated_tax(0, 0.26) == 0.0

    def test_different_rate(self):
        assert calc_estimated_tax(1000, 0.125) == 125.0


# ── calc_xirr ──

class TestCalcXirr:
    def test_simple_investment(self):
        """Invest 1000, get back 1100 after 1 year -> ~10% return."""
        cashflows = [
            (datetime(2024, 1, 1), -1000),
            (datetime(2025, 1, 1), 1100),
        ]
        result = calc_xirr(cashflows)
        assert result is not None
        assert abs(result - 0.10) < 0.01

    def test_multiple_investments(self):
        """Multiple cashflows should return a valid rate."""
        cashflows = [
            (datetime(2024, 1, 1), -500),
            (datetime(2024, 7, 1), -500),
            (datetime(2025, 1, 1), 1100),
        ]
        result = calc_xirr(cashflows)
        assert result is not None
        assert result > 0

    def test_loss(self):
        """Invest 1000, get back 900 -> negative return."""
        cashflows = [
            (datetime(2024, 1, 1), -1000),
            (datetime(2025, 1, 1), 900),
        ]
        result = calc_xirr(cashflows)
        assert result is not None
        assert result < 0

    def test_too_few_cashflows(self):
        cashflows = [(datetime(2024, 1, 1), -1000)]
        assert calc_xirr(cashflows) is None

    def test_empty_cashflows(self):
        assert calc_xirr([]) is None

    def test_breakeven(self):
        """Invest 1000, get back 1000 -> ~0% return."""
        cashflows = [
            (datetime(2024, 1, 1), -1000),
            (datetime(2025, 1, 1), 1000),
        ]
        result = calc_xirr(cashflows)
        assert result is not None
        assert abs(result) < 0.01


# ── calc_twr ──

class TestCalcTwr:
    def test_single_transaction_price_up(self):
        """Buy at 100, now at 110 -> 10% TWR."""
        twr_txns = [(datetime(2024, 1, 1), "buy", 100)]
        result = calc_twr(twr_txns, 110)
        assert result is not None
        assert abs(result - 0.10) < 0.001

    def test_single_transaction_price_down(self):
        """Buy at 100, now at 90 -> -10% TWR."""
        twr_txns = [(datetime(2024, 1, 1), "buy", 100)]
        result = calc_twr(twr_txns, 90)
        assert result is not None
        assert abs(result - (-0.10)) < 0.001

    def test_multiple_transactions(self):
        """Multiple buys at different prices."""
        twr_txns = [
            (datetime(2024, 1, 1), "buy", 100),
            (datetime(2024, 6, 1), "buy", 110),
        ]
        result = calc_twr(twr_txns, 121)
        assert result is not None
        # (110/100) * (121/110) - 1 = 0.21
        assert abs(result - 0.21) < 0.001

    def test_empty_transactions(self):
        assert calc_twr([], 100) is None

    def test_flat_price(self):
        """Price unchanged -> 0% TWR."""
        twr_txns = [(datetime(2024, 1, 1), "buy", 100)]
        result = calc_twr(twr_txns, 100)
        assert result is not None
        assert abs(result) < 0.001


# ── calc_period_mwrr ──

class TestCalcPeriodMwrr:
    def test_simple_period(self):
        """Invest 1000, worth 1050 after 30 days."""
        cashflows = [
            (datetime(2025, 3, 1), -1000),
            (datetime(2025, 3, 31), 1050),
        ]
        result = calc_period_mwrr(cashflows, 30)
        assert result is not None
        assert result > 0

    def test_too_few_cashflows(self):
        cashflows = [(datetime(2025, 3, 1), -1000)]
        assert calc_period_mwrr(cashflows, 30) is None


# ── calc_period_twr ──

class TestCalcPeriodTwr:
    def test_no_cashflows_in_period(self):
        """Portfolio value goes from 1000 to 1100, no transactions."""
        eval_dates = [datetime(2025, 1, 1), datetime(2025, 2, 1)]

        def get_value_before(date):
            return 1100 if date == datetime(2025, 2, 1) else 1000

        def get_value_after(date):
            return 1000 if date == datetime(2025, 1, 1) else 1100

        result = calc_period_twr(eval_dates, get_value_before, get_value_after)
        assert abs(result - 0.10) < 0.001

    def test_with_cashflow(self):
        """Portfolio with a mid-period deposit."""
        eval_dates = [
            datetime(2025, 1, 1),
            datetime(2025, 1, 15),  # deposit day
            datetime(2025, 2, 1),
        ]

        values = {
            datetime(2025, 1, 1): (None, 1000),       # start: after = 1000
            datetime(2025, 1, 15): (1050, 1550),       # before deposit: 1050, after: 1550 (added 500)
            datetime(2025, 2, 1): (1600, 1600),         # end: before = after = 1600
        }

        def get_value_before(date):
            return values[date][0]

        def get_value_after(date):
            return values[date][1]

        result = calc_period_twr(eval_dates, get_value_before, get_value_after)
        # Sub-period 1: 1050/1000 = 1.05
        # Sub-period 2: 1600/1550 = 1.0323
        # TWR = 1.05 * 1.0323 - 1 = 0.0839
        assert result is not None
        assert abs(result - 0.0839) < 0.01
