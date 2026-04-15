# Portfolio Tracker

Personal portfolio tracker that calculates returns, P&L, tax estimates and allocation breakdowns from a CSV of financial transactions.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run.py                            # terminal output
python run.py --export report.json       # also export to JSON
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

`Type` must be `Buy` or `Sell`. `Security` must match a key in `config.json` instruments.

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
