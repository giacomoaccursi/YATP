"""Transaction summary: offline overview without market data."""

from dataclasses import dataclass
from portfolio.models import InstrumentData


@dataclass
class InstrumentSummary:
    """Transaction summary for a single instrument."""
    security: str
    total_buys: int
    total_sells: int
    total_dividends: int
    total_coupons: int
    total_invested: float
    total_sold: float
    total_income: float
    net_invested: float
    shares_held: float
    avg_cost_per_share: float
    first_transaction: object
    last_transaction: object


@dataclass
class PortfolioTransactionSummary:
    """Aggregate transaction summary for the entire portfolio."""
    total_transactions: int
    total_invested: float
    total_sold: float
    total_income: float
    net_invested: float
    instruments: list


def build_summary(df):
    """Build a transaction summary from the DataFrame. No market data needed."""
    df = df.sort_values("Date")
    instrument_summaries = []

    for security, group in df.groupby("Security"):
        group = group.sort_values("Date")

        buys = group[group["Type"].str.strip().str.lower() == "buy"]
        sells = group[group["Type"].str.strip().str.lower() == "sell"]
        dividends = group[group["Type"].str.strip().str.lower() == "dividend"]
        coupons = group[group["Type"].str.strip().str.lower() == "coupon"]

        total_invested = buys["Net Transaction Value"].sum()
        total_sold = sells["Net Transaction Value"].sum()
        total_income = dividends["Net Transaction Value"].sum() + coupons["Net Transaction Value"].sum()

        # Replay for shares and avg cost
        shares_held = 0.0
        total_cost = 0.0
        for _, row in group.iterrows():
            tx_type = row["Type"].strip().lower()
            if tx_type == "buy":
                shares_held += row["Shares"]
                total_cost += row["Net Transaction Value"]
            elif tx_type == "sell":
                avg = total_cost / shares_held if shares_held > 0 else 0
                total_cost -= avg * row["Shares"]
                shares_held -= row["Shares"]

        avg_cost = total_cost / shares_held if shares_held > 0 else 0

        instrument_summaries.append(InstrumentSummary(
            security=security,
            total_buys=len(buys),
            total_sells=len(sells),
            total_dividends=len(dividends),
            total_coupons=len(coupons),
            total_invested=total_invested,
            total_sold=total_sold,
            total_income=total_income,
            net_invested=total_invested - total_sold,
            shares_held=shares_held,
            avg_cost_per_share=avg_cost,
            first_transaction=group["Date"].min(),
            last_transaction=group["Date"].max(),
        ))

    total_transactions = len(df)
    total_invested = sum(s.total_invested for s in instrument_summaries)
    total_sold = sum(s.total_sold for s in instrument_summaries)
    total_income = sum(s.total_income for s in instrument_summaries)

    return PortfolioTransactionSummary(
        total_transactions=total_transactions,
        total_invested=total_invested,
        total_sold=total_sold,
        total_income=total_income,
        net_invested=total_invested - total_sold,
        instruments=instrument_summaries,
    )
