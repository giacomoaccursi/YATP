"""Market price fetching: Yahoo Finance for stocks/ETFs, Borsa Italiana for bonds.

Each provider has a consistent interface:
    - Yahoo Finance: yfinance.Ticker(symbol).history(...)
    - Borsa Italiana: borsa_italiana.Bond(isin).history(...) / .current_price()
"""

import yfinance as yf
from datetime import timedelta
from portfolio.borsa_italiana import Bond, clear_cache as clear_bi_cache


def fetch_current_price(ticker_symbol, isin=None, instrument_type=None):
    """Fetch current price.

    Bonds go directly to Borsa Italiana. Everything else uses Yahoo Finance,
    with Borsa Italiana as fallback when ISIN is available.
    """
    if instrument_type == "Bond" and isin:
        return Bond(isin).current_price()

    price = _fetch_yahoo_price(ticker_symbol)
    if price is not None:
        return price

    if isin:
        return Bond(isin).current_price()

    return None


def fetch_price_history(ticker_symbol, start_date, end_date, instrument_type=None, isin=None):
    """Fetch historical close prices. Returns a pandas Series or None.

    Bonds use Borsa Italiana chart API. Everything else uses Yahoo Finance.
    """
    if instrument_type == "Bond" and isin:
        return Bond(isin).history(start=start_date, end=end_date)

    try:
        hist = yf.Ticker(ticker_symbol).history(
            start=start_date - timedelta(days=5),
            end=end_date + timedelta(days=1),
        )
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        return hist["Close"].dropna()
    except Exception as error:
        print(f"⚠️  Error fetching history for {ticker_symbol}: {error}")
        return None


def clear_bond_price_cache():
    """Clear the Borsa Italiana cache."""
    clear_bi_cache()


# ── Yahoo Finance ──

def _fetch_yahoo_price(ticker_symbol):
    """Fetch current price from Yahoo Finance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5d")
        if hist.empty:
            return None
        return hist["Close"].iloc[-1]
    except Exception as error:
        print(f"⚠️  Yahoo Finance error for {ticker_symbol}: {error}")
        return None
