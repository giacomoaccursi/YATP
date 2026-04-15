"""Fetch prezzi di mercato da Yahoo Finance."""

import yfinance as yf
from datetime import timedelta


def fetch_current_price(ticker_symbol):
    """Scarica il prezzo corrente da Yahoo Finance. Ritorna None se non disponibile."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            return None
        return hist["Close"].iloc[-1]
    except Exception as error:
        print(f"⚠️  Errore nel fetch di {ticker_symbol}: {error}")
        return None


def fetch_price_history(ticker_symbol, start_date, end_date):
    """Scarica lo storico prezzi da Yahoo Finance. Ritorna una Series di Close prices."""
    try:
        hist = yf.Ticker(ticker_symbol).history(
            start=start_date - timedelta(days=5),
            end=end_date + timedelta(days=1)
        )
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        return hist["Close"]
    except Exception as error:
        print(f"⚠️  Errore nel fetch storico di {ticker_symbol}: {error}")
        return None
