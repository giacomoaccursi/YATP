"""Borsa Italiana data provider for bonds.

Usage mirrors yfinance:

    from portfolio.borsa_italiana import Bond

    bond = Bond("IT0005517195")
    price = bond.current_price()          # float or None
    history = bond.history()              # pandas Series or None
    history = bond.history(period="1Y")   # last year only
"""

import re
import requests
import pandas as pd

_BASE_URL = "https://grafici.borsaitaliana.it"
_CHART_URL = _BASE_URL + "/interactive-chart/{isin}-MOTX?lang=it"
_API_URL = _BASE_URL + "/api"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

_SINGLE_CATEGORIES = [
    "mot/btp/scheda",
    "mot/cct/scheda",
    "mot/euro-obbligazioni/scheda",
    "mot/obbligazioni-euro/scheda",
]
_SINGLE_PRICE_PATTERN = re.compile(
    r'-formatPrice[^>]*>\s*<strong>([0-9]+[.,][0-9]+)</strong>'
)

# Module-level cache for JWT tokens and prices
_token_cache = {}
_price_cache = {}


class Bond:
    """Borsa Italiana bond data provider. Interface mirrors yfinance.Ticker."""

    def __init__(self, isin):
        """Initialize with ISIN code (e.g. 'IT0005517195')."""
        self.isin = isin

    def current_price(self):
        """Fetch current bond price from Borsa Italiana.

        Scrapes the individual bond page. Returns float or None.
        """
        if self.isin in _price_cache:
            return _price_cache[self.isin]

        price = _scrape_current_price(self.isin)
        if price is not None:
            _price_cache[self.isin] = price
        return price

    def history(self, period="MAX", start=None, end=None):
        """Fetch historical close prices from Borsa Italiana chart API.

        Args:
            period: One of '1W', '1M', '3M', '6M', '1Y', '3Y', '5Y', 'MAX'
            start: Optional start date (pandas Timestamp or datetime). Overrides period.
            end: Optional end date (pandas Timestamp or datetime).

        Returns pandas Series with DatetimeIndex and close prices, or None.
        """
        token = _get_token(self.isin)
        if token is None:
            return None

        history_data = _fetch_history(self.isin, token, period)
        if history_data is None:
            return None

        series = _parse_history(history_data)
        if series is None or series.empty:
            return None

        # Apply date filters
        if start is not None:
            series = series[series.index >= pd.Timestamp(start)]
        if end is not None:
            series = series[series.index <= pd.Timestamp(end)]

        return series if not series.empty else None


def clear_cache():
    """Clear all cached data."""
    _token_cache.clear()
    _price_cache.clear()


# ── Current price (scraping) ──

def _scrape_current_price(isin):
    """Scrape current price from the individual bond page on Borsa Italiana."""
    for category in _SINGLE_CATEGORIES:
        url = f"https://www.borsaitaliana.it/borsa/obbligazioni/{category}/{isin}.html"
        try:
            response = requests.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                continue
            match = _SINGLE_PRICE_PATTERN.search(response.text)
            if match:
                price = _parse_italian_price(match.group(1))
                return price
        except Exception:
            continue
    return None


# ── Historical prices (chart API) ──

def _get_token(isin):
    """Get JWT token for the chart API. Cached per ISIN."""
    if isin in _token_cache:
        return _token_cache[isin]

    try:
        url = _CHART_URL.format(isin=isin)
        response = requests.get(url, headers=_HEADERS, timeout=10)
        match = re.search(r'token="([^"]+)"', response.text)
        if match:
            token = match.group(1)
            _token_cache[isin] = token
            return token
    except Exception:
        pass
    return None


def _fetch_history(isin, token, period):
    """Fetch historical data from the chart API."""
    url = f"{_API_URL}/instruments/{isin},XMIL,ISIN/history/period"
    auth_headers = {
        **_HEADERS,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    try:
        response = requests.get(url, headers=auth_headers, params={"period": period}, timeout=15)
        if response.status_code != 200:
            return None
        data = response.json()
        return data.get("history", {}).get("historyDt")
    except Exception:
        return None


def _parse_history(history_data):
    """Parse chart API history response into a pandas Series."""
    dates = []
    prices = []
    for point in history_data:
        close_price = point.get("closePx")
        date_str = point.get("dt")
        if close_price is not None and date_str:
            try:
                dates.append(pd.Timestamp(date_str))
                prices.append(float(close_price))
            except (ValueError, TypeError):
                continue

    if not dates:
        print("⚠️  Borsa Italiana: no valid price data in API response")
        return None

    return pd.Series(prices, index=pd.DatetimeIndex(dates))


# ── Helpers ──

def _parse_italian_price(price_str):
    """Parse Italian-format price string (e.g. '102,20') to float."""
    return float(price_str.replace(".", "").replace(",", "."))
