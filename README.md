# YAPT — Yet Another Portfolio Tracker

A personal portfolio tracker with a web dashboard and CLI. Tracks returns, P&L, taxes, allocation, historical performance and rebalancing from a CSV of transactions.

Prices from Yahoo Finance. Bond prices from Borsa Italiana. Risk-free rate from ECB.

## Features

**Dashboard**
- Portfolio value over time with gradient chart
- Cards: Invested, Market Value, P&L (with unrealized/realized split), Income, XIRR
- Monthly income chart (dividends & coupons)
- Allocation doughnuts (by instrument and asset class)
- Daily change indicator with animated arrow

**Instruments**
- Table with all metrics: shares, avg cost, weight, market value, P&L, return, XIRR, income, estimated tax
- Click to expand: Price vs Avg Cost, Unrealized P&L, Value vs Cost, TWR Return — all with buy point markers

**Performance**
- Risk metrics: Volatility, Sharpe Ratio, Sortino Ratio, Max Drawdown (using ECB deposit rate as risk-free)
- Period returns table: 1M, 6M, 1Y, Since Start — with TWR and MWRR
- Cumulative return chart with period filters (1M, 3M, 6M, 1Y, YTD, All, custom range)
- Value vs Cost Basis chart
- Drawdown from peak chart
- Monthly returns heatmap
- Filter by instrument (multi-select chips)

**Rebalance**
- Simulate new investment amount
- Adjust target allocation with sliders
- Current vs target doughnut charts
- Action table: what to buy/sell to reach target

**Sell Simulator**
- Select instrument and shares to sell
- Shows: gross proceeds, cost of sold, gain/loss, tax rate, estimated tax, net proceeds

**Transactions**
- Full CRUD: add, edit, delete
- Sortable columns (date, shares, quote, fees, taxes, net value)
- Filters: instrument, type, date range
- Sticky header on scroll
- Add new instruments on the fly (with type-specific fields: ticker for stocks/ETFs, ISIN for bonds)

**General**
- Dark/light theme with toggle
- Multi-language: English, Italiano, Español (vue-i18n, live switch)
- Offline fallback: shows CSV-only data when market is unreachable
- Alert banner for failed instruments
- Refresh prices button with timestamp

## Quick Start

```bash
pip install -r requirements.txt
python run.py --ui
```

Opens the web dashboard at `http://127.0.0.1:5050`.

## CLI

```bash
python run.py                            # terminal report
python run.py --export report.json       # export to JSON
python run.py --rebalance                # rebalancing suggestions
python run.py --summary                  # offline transaction summary
python run.py --ui                       # web dashboard
python run.py --transactions my.csv --config my.json
```

## Configuration

Create a `config.json`:

```json
{
  "tax": {
    "country": "IT",
    "regime": "amministrato"
  },
  "target_allocation": {
    "ETF": 80,
    "ETC": 20
  },
  "instruments": {
    "VANG FTSE AW USDA": {
      "ticker": "VWCE.DE",
      "isin": "IE00BK5BQT80",
      "type": "ETF",
      "capital_gains_rate": 0.26
    },
    "BTP ITALIA 2028": {
      "ticker": "BTP28.MI",
      "isin": "IT0005517195",
      "type": "Bond",
      "capital_gains_rate": 0.125
    }
  }
}
```

- `ticker`: Yahoo Finance symbol (required for all except bonds)
- `isin`: required for bonds (used for Borsa Italiana fallback)
- `type`: ETF, ETC, ETN, Stock, Bond, REIT, Crypto, Other
- `capital_gains_rate`: defaults to 0.26 if omitted
- `target_allocation`: keys must match instrument `type` values

## Transactions CSV

```
Date,Type,Security,Shares,Quote,Amount,Fees,Taxes,Accrued Interest,Net Transaction Value
```

| Type | Effect |
|---|---|
| `Buy` | Increases shares and cost basis |
| `Sell` | Decreases shares, realizes P&L |
| `Dividend` | Income (no effect on shares/cost) |
| `Coupon` | Income from bonds (no effect on shares/cost) |

`Security` must match a key in `config.json` instruments.

## Return Calculations

| Metric | What it measures |
|---|---|
| Simple Return | (Market Value - Cost) / Cost |
| TWR | Time-Weighted Return — portfolio strategy performance, independent of cash flows |
| XIRR / MWRR | Money-Weighted Return — your actual return considering timing of investments |
| Sharpe Ratio | Return per unit of risk (uses ECB deposit rate as risk-free) |
| Sortino Ratio | Like Sharpe but only penalizes downside volatility |

## Market Data

- **Stocks, ETFs, ETCs**: Yahoo Finance via `yfinance`
- **Bonds**: Yahoo Finance first, then Borsa Italiana scraping (bulk list + single ISIN fallback)
- **Risk-free rate**: ECB Deposit Facility Rate (fetched automatically from ECB Data API)

## Tech Stack

- Python 3.9+, Flask, pandas, yfinance, scipy, requests, beautifulsoup4
- Vue 3 (CDN), vue-i18n, Chart.js, Tailwind CSS (CDN)
- No build step, no node_modules

## Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
