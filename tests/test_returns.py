"""Tests for portfolio.returns module."""

import pytest
from datetime import datetime
from portfolio.returns import (
    calc_xirr, calc_simple_return,
    calc_estimated_tax, calc_period_mwrr,
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


