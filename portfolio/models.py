"""Data models for the portfolio tracker."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InstrumentData:
    """Raw portfolio state for a single instrument."""
    shares_held: float
    avg_cost_per_share: float
    cost_basis: float
    realized_pnl: float
    total_income: float = 0.0
    cashflows: list = field(default_factory=list)


@dataclass
class InstrumentAnalysis:
    """Calculated returns for a single instrument."""
    market_value: float
    unrealized_pnl: float
    total_pnl: float
    simple_return: float
    twr: Optional[float]
    xirr: Optional[float]
    estimated_tax: float
    net_after_tax: float
    total_income: float = 0.0


@dataclass
class InstrumentResult:
    """Combined data, analysis and config for a single instrument."""
    security: str
    ticker: str
    isin: Optional[str]
    capital_gains_rate: float
    data: InstrumentData
    analysis: InstrumentAnalysis


@dataclass
class PortfolioSummary:
    """Aggregate portfolio returns and allocations."""
    cost: float
    market_value: float
    unrealized: float
    realized: float
    tax: float
    total_pnl: float
    simple_return: float
    xirr: Optional[float]
    net_after_tax: float
    allocations: dict = field(default_factory=dict)
    allocations_by_asset_class: dict = field(default_factory=dict)


@dataclass
class PeriodPerformance:
    """Performance metrics for a single time period."""
    period: str
    available: bool
    past_date: object = None
    market_gain: float = 0
    simple_return: float = 0
    twr: Optional[float] = None
    mwrr: Optional[float] = None


@dataclass
class RebalanceAction:
    """Rebalancing suggestion for a single asset class."""
    asset_class: str
    current_weight: float
    target_weight: float
    current_value: float
    target_value: float
    difference: float


@dataclass
class OfflineSummary:
    """Portfolio summary from CSV only (no market data)."""
    cost_basis: float
    transaction_count: int
    total_income: float
    instruments_count: int


@dataclass
class SellSimulation:
    """Result of a sell simulation."""
    security: str
    shares_to_sell: float
    shares_held: float
    current_price: float
    avg_cost_per_share: float
    gross_proceeds: float
    cost_of_sold: float
    gain: float
    capital_gains_rate: float
    estimated_tax: float
    net_proceeds: float
