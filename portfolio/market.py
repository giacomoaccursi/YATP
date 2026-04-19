"""Market price fetching: Yahoo Finance + Borsa Italiana for bonds."""

import re
import yfinance as yf
from datetime import timedelta


def fetch_current_price(ticker_symbol, isin=None, instrument_type=None):
    """Fetch current price. Tries Yahoo Finance first, then Borsa Italiana for bonds.

    For bonds (instrument_type='Bond'), skips Yahoo and goes directly to Borsa Italiana.

    Args:
        ticker_symbol: Yahoo Finance ticker (e.g. VWCE.DE)
        isin: Optional ISIN code for Borsa Italiana bond fallback
        instrument_type: Optional instrument type from config (e.g. 'Bond', 'ETF')

    Returns float price or None.
    """
    # Bonds: skip Yahoo, go directly to Borsa Italiana
    if instrument_type == "Bond" and isin:
        price = _fetch_bond_price(isin)
        if price is not None:
            return price

    price = _fetch_yahoo_price(ticker_symbol)
    if price is not None:
        return price

    if isin:
        price = _fetch_bond_price(isin)
        if price is not None:
            return price

    return None


def fetch_price_history(ticker_symbol, start_date, end_date, instrument_type=None):
    """Fetch historical prices. Returns a Close price Series or None.

    Bonds have no Yahoo history — returns None immediately for instrument_type='Bond'.
    """
    if instrument_type == "Bond":
        return None

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


# ── Yahoo Finance ──

def _fetch_yahoo_price(ticker_symbol):
    """Fetch current price from Yahoo Finance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            return None
        return hist["Close"].iloc[-1]
    except Exception as error:
        print(f"⚠️  Yahoo Finance error for {ticker_symbol}: {error}")
        return None


# ── Borsa Italiana bond prices ──

_bond_cache = {}

_BI_SINGLE_CATEGORIES = [
    "mot/btp/scheda",
    "mot/cct/scheda",
    "mot/euro-obbligazioni/scheda",
    "mot/obbligazioni-euro/scheda",
]

_SINGLE_PRICE_PATTERN = re.compile(
    r'-formatPrice[^>]*>\s*<strong>([0-9]+[.,][0-9]+)</strong>'
)


def _fetch_bond_price(isin):
    """Fetch bond price by ISIN from its Borsa Italiana page."""
    if isin in _bond_cache:
        return _bond_cache[isin]

    price = _fetch_single(isin)
    if price is not None:
        _bond_cache[isin] = price
    return price


def _fetch_single(isin):
    """Fetch a single bond price from its Borsa Italiana page."""
    try:
        import requests
    except ImportError:
        return None

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    for category in _BI_SINGLE_CATEGORIES:
        url = f"https://www.borsaitaliana.it/borsa/obbligazioni/{category}/{isin}.html"
        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                continue
            match = _SINGLE_PRICE_PATTERN.search(response.text)
            if match:
                price = _parse_price(match.group(1))
                print(f"📊 Borsa Italiana single: {isin} = {price}")
                return price
        except Exception:
            continue

    return None


def _parse_price(price_str):
    """Parse Italian-format price string (e.g. '102,20') to float."""
    return float(price_str.replace(".", "").replace(",", "."))


def clear_bond_price_cache():
    """Clear the bond price cache to force re-fetch."""
    _bond_cache.clear()
