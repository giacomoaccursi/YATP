"""Price caching layer. In-memory caches that persist while the server is running."""

from portfolio.market import fetch_current_price, fetch_price_history, clear_bond_price_cache

_price_cache = {}
_daily_change_cache = {}
_price_history_cache = {}
_price_fetch_time = None


def get_cached_price(ticker, isin=None, instrument_type=None):
    """Fetch current price with in-memory caching."""
    global _price_fetch_time
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
    global _price_fetch_time
    _price_cache.clear()
    _daily_change_cache.clear()
    _price_history_cache.clear()
    _price_fetch_time = None
    clear_bond_price_cache()


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
