"""Market price fetching from Yahoo Finance."""

import yfinance as yf
from datetime import timedelta


def fetch_current_price(ticker_symbol):
    """Fetch current price from Yahoo Finance. Returns None if unavailable."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            return None
        return hist["Close"].iloc[-1]
    except Exception as error:
        print(f"⚠️  Error fetching {ticker_symbol}: {error}")
        return None


def fetch_price_history(ticker_symbol, start_date, end_date):
    """Fetch historical prices from Yahoo Finance. Returns a Close price Series."""
    try:
        hist = yf.Ticker(ticker_symbol).history(
            start=start_date - timedelta(days=5),
            end=end_date + timedelta(days=1)
        )
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        return hist["Close"].dropna()
    except Exception as error:
        print(f"⚠️  Error fetching history for {ticker_symbol}: {error}")
        return None
