"""Web data layer: builds portfolio data for the API. Handles price caching."""

from portfolio.loader import load_config, load_transactions
from portfolio.portfolio import build_portfolio
from portfolio.analysis import analyze_instrument, analyze_portfolio
from portfolio.market import fetch_current_price
from portfolio.models import InstrumentResult
from portfolio.summary import build_summary
from portfolio.rebalance import calc_rebalance

# In-memory price cache (persists while server is running)
_price_cache = {}


def get_cached_price(ticker):
    """Fetch price with in-memory caching."""
    if ticker not in _price_cache:
        _price_cache[ticker] = fetch_current_price(ticker)
    return _price_cache[ticker]


def clear_price_cache():
    """Clear the price cache to force re-fetch."""
    _price_cache.clear()


def load_portfolio_data(config_path, transactions_path):
    """Load and analyze the full portfolio. Returns (results, summary, config)."""
    config = load_config(config_path)
    instruments = config["instruments"]
    df = load_transactions(transactions_path)
    portfolio = build_portfolio(df)

    results = []
    for security, data in portfolio.items():
        instrument = instruments.get(security.strip())
        if not instrument:
            continue

        current_price = get_cached_price(instrument["ticker"])
        if current_price is None:
            continue

        capital_gains_rate = instrument.get("capital_gains_rate", 0.26)
        analysis = analyze_instrument(data, current_price, capital_gains_rate)
        results.append(InstrumentResult(
            security=security,
            ticker=instrument["ticker"],
            isin=instrument.get("isin"),
            capital_gains_rate=capital_gains_rate,
            data=data,
            analysis=analysis,
        ))

    summary = analyze_portfolio(results, instruments) if results else None
    return results, summary, config
