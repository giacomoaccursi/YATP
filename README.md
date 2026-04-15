# Simple Portfolio Tracker

Personal portfolio tracker that calculates returns, P&L, tax estimates and allocation breakdowns from a CSV of financial transactions.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run.py                            # terminal output
python run.py --export report.json       # also export to JSON
python run.py --rebalance                # show rebalancing suggestions
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
  "instruments": {
    "SECURITY NAME": {
      "ticker": "VWCE.DE",
      "isin": "IE00BK5BQT80",
      "type": "ETF",
      "capital_gains_rate": 0.26,
      "notes": "optional"
    }
  }
}
```

## Transactions CSV

Required columns:

```
Date,Type,Security,Shares,Quote,Amount,Fees,Taxes,Net Transaction Value
```

`Security` must match a key in `config.json` instruments.

Supported transaction types:

| Type | Description | Required fields |
|---|---|---|
| `Buy` | Purchase shares | Shares, Quote, Net Transaction Value |
| `Sell` | Sell shares (also used for bond maturity/redemption) | Shares, Quote, Net Transaction Value |
| `Dividend` | Dividend payment from distributing funds | Net Transaction Value (Shares/Quote can be empty) |
| `Coupon` | Coupon payment from bonds | Net Transaction Value (Shares/Quote can be empty) |

Empty numeric fields are treated as zero. For dividends and coupons, only `Date`, `Type`, `Security` and `Net Transaction Value` are needed.

## Tests

```bash
pytest tests/ -v
```

## What it calculates

- Simple return, TWR, XIRR (MWRR) per instrument and portfolio
- Unrealized and realized P&L
- Tax estimates per instrument (configurable rate)
- Allocation by instrument and asset class
- Historical performance: 1 month, 6 months, 1 year, since inception
- Rebalancing suggestions by asset class

## Rebalancing

Add a `target_allocation` to `config.json` with target percentages by asset class:

```json
{
  "target_allocation": {
    "ETF": 80,
    "ETC": 20
  }
}
```

Asset classes are defined by the `type` field of each instrument. Run with `--rebalance` to see how much to buy or sell per class to reach your target.

## Market Data

Current and historical prices are fetched from [Yahoo Finance](https://finance.yahoo.com/) via the `yfinance` library. The `ticker` field in `config.json` must match a valid Yahoo Finance symbol (e.g. `VWCE.DE` for Xetra, `VWRL.AS` for Amsterdam).
