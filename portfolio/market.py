"""Market price fetching: Yahoo Finance + Borsa Italiana for bonds."""

import re
import yfinance as yf
from datetime import timedelta


def fetch_current_price(ticker_symbol, isin=None):
    """Fetch current price. Tries Yahoo Finance first, then Borsa Italiana for bonds.

    Args:
        ticker_symbol: Yahoo Finance ticker (e.g. VWCE.DE)
        isin: Optional ISIN code for Borsa Italiana bond fallback

    Returns float price or None.
    """
    price = _fetch_yahoo_price(ticker_symbol)
    if price is not None:
        return price

    if isin:
        price = _fetch_bond_price(isin)
        if price is not None:
            return price

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

_BI_LIST_CATEGORIES = [
    "mot/btp/lista.html",
    "mot/cct/lista.html",
    "mot/bot/lista.html",
    "mot/euro-obbligazioni/lista.html",
    "mot/obbligazioni-euro/lista.html",
    "extramot/lista.html",
]

_BI_SINGLE_CATEGORIES = [
    "mot/btp/scheda",
    "mot/cct/scheda",
    "mot/euro-obbligazioni/scheda",
    "mot/obbligazioni-euro/scheda",
]

_LIST_PRICE_PATTERN = re.compile(
    r'([A-Z]{2}[A-Z0-9]{10})\s*-.*?Ultimo:\s*([0-9]+,[0-9]+)', re.DOTALL
)
_SINGLE_PRICE_PATTERN = re.compile(
    r'-formatPrice[^>]*>\s*<strong>([0-9]+[.,][0-9]+)</strong>'
)


def _fetch_bond_price(isin):
    """Fetch bond price by ISIN from Borsa Italiana.

    1. Try individual bond page first (fast, single request)
    2. Fall back to bulk list pages if single page fails
    """
    if isin in _bond_cache:
        return _bond_cache[isin]

    # Fast path: single page scrape
    price = _fetch_single(isin)
    if price is not None:
        _bond_cache[isin] = price
        return price

    # Slow path: bulk load all bonds, then check cache
    if not _bond_cache.get("__loaded__"):
        _load_bulk()
        if isin in _bond_cache:
            return _bond_cache[isin]

    return None


def _load_bulk():
    """Load bond prices from Borsa Italiana list pages in bulk."""
    try:
        import requests
        import time
    except ImportError:
        _bond_cache["__loaded__"] = True
        return

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    for category in _BI_LIST_CATEGORIES:
        for page in range(1, 100):
            url = f"https://www.borsaitaliana.it/borsa/obbligazioni/{category}?&page={page}"
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200:
                    break
                pairs = _LIST_PRICE_PATTERN.findall(response.text)
                if not pairs:
                    break
                new_count = 0
                for found_isin, price_str in pairs:
                    if found_isin not in _bond_cache:
                        _bond_cache[found_isin] = _parse_price(price_str)
                        new_count += 1
                if new_count == 0:
                    break
                time.sleep(0.2)
            except Exception:
                break

    count = len([k for k in _bond_cache if not k.startswith("__")])
    print(f"📊 Borsa Italiana: loaded {count} bond prices")
    _bond_cache["__loaded__"] = True


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
