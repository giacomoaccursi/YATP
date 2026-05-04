"""Price caching layer. In-memory caches that persist while the server is running."""

import time
import requests
from portfolio.market import fetch_current_price, fetch_price_history, clear_bond_price_cache

PRICE_CACHE_TTL = 300  # 5 minutes

_price_cache = {}
_price_cache_time = 0
_daily_change_cache = {}
_price_history_cache = {}
_price_fetch_time = None
_risk_free_rate = None
_common_cache = None


def get_cached_price(ticker, isin=None, instrument_type=None):
    """Fetch current price with in-memory caching. Expires after PRICE_CACHE_TTL seconds."""
    global _price_fetch_time, _price_cache_time
    if time.time() - _price_cache_time > PRICE_CACHE_TTL:
        _price_cache.clear()
        _daily_change_cache.clear()
        _price_cache_time = time.time()
        _price_fetch_time = None
    if ticker not in _price_cache:
        _price_cache[ticker] = fetch_current_price(ticker, isin=isin, instrument_type=instrument_type)
        if _price_fetch_time is None:
            from datetime import datetime
            _price_fetch_time = datetime.now().strftime("%H:%M")
    return _price_cache[ticker]


def get_cached_daily_change(ticker, instrument_type=None):
    """Fetch daily price change percentage with caching."""
    if ticker not in _daily_change_cache:
        if instrument_type == "Bond":
            _daily_change_cache[ticker] = None  # Bonds don't have daily change from Yahoo
        else:
            _daily_change_cache[ticker] = _calc_daily_change(ticker)
    return _daily_change_cache[ticker]


def get_cached_price_history(ticker, start_date, end_date, instrument_type=None, isin=None):
    """Fetch price history with in-memory caching."""
    if ticker not in _price_history_cache:
        _price_history_cache[ticker] = fetch_price_history(
            ticker, start_date, end_date,
            instrument_type=instrument_type, isin=isin,
        )
    return _price_history_cache[ticker]


def get_price_fetch_time():
    """Return the time when prices were last fetched, or None."""
    return _price_fetch_time


def clear_all_caches():
    """Clear all price caches to force re-fetch."""
    global _price_fetch_time, _common_cache
    _price_cache.clear()
    _daily_change_cache.clear()
    _price_history_cache.clear()
    _price_fetch_time = None
    _common_cache = None
    clear_bond_price_cache()


def invalidate_transaction_cache():
    """Invalidate caches that depend on transaction data. Called after add/edit/delete."""
    global _common_cache
    _common_cache = None


def get_common_cache():
    """Return cached load_common() result, or None if not cached."""
    return _common_cache


def set_common_cache(value):
    """Store load_common() result in cache."""
    global _common_cache
    _common_cache = value


def get_risk_free_rate():
    """Get the ECB deposit facility rate (risk-free proxy for EUR).

    Fetched once and cached for the server lifetime.
    Returns float as decimal (e.g. 0.025 for 2.5%).
    Falls back to 0.025 if the API is unreachable.
    """
    global _risk_free_rate
    if _risk_free_rate is not None:
        return _risk_free_rate

    try:
        response = requests.get(
            "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV",
            params={"lastNObservations": "1", "format": "csvdata"},
            timeout=5,
        )
        if response.status_code == 200:
            lines = response.text.strip().split("\n")
            if len(lines) >= 2:
                # OBS_VALUE is the 10th field (index 9)
                data_line = lines[1]
                fields = data_line.split(",")
                obs_value = float(fields[9])
                _risk_free_rate = obs_value / 100  # Convert from percentage to decimal
                return _risk_free_rate
    except Exception:
        pass

    # Fallback: 2.5% (reasonable EUR risk-free estimate)
    _risk_free_rate = 0.025
    return _risk_free_rate


def _calc_daily_change(ticker):
    """Calculate daily price change percentage from Yahoo Finance."""
    try:
        import yfinance as yf
        price_history = yf.Ticker(ticker).history(period="5d")
        if price_history is None or len(price_history) < 2:
            return None
        closes = price_history["Close"].dropna()
        if len(closes) < 2:
            return None
        prev = closes.iloc[-2]
        curr = closes.iloc[-1]
        return ((curr - prev) / prev) * 100 if prev > 0 else None
    except Exception:
        return None
