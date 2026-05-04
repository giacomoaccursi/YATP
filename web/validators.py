"""Input validation for API requests.

Each validator function raises ValidationError if input is invalid.
Returns the cleaned/parsed data if valid.
"""

from web.errors import ValidationError


def validate_transaction_input(data):
    """Validate and clean transaction input data.

    Args:
        data: Raw JSON dict from request

    Returns:
        Cleaned dict with validated fields

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    if not data:
        raise ValidationError("Request body is required")

    required = ["date", "type", "security"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    tx_type = data["type"].strip()
    if tx_type not in ("Buy", "Sell", "Dividend", "Coupon"):
        raise ValidationError(f"Invalid transaction type: {tx_type}. Must be Buy, Sell, Dividend, or Coupon.")

    return {
        "date": data["date"].strip(),
        "type": tx_type,
        "security": data["security"].strip(),
        "shares": _parse_numeric(data.get("shares"), "shares"),
        "quote": _parse_numeric(data.get("quote"), "quote"),
        "amount": _parse_numeric(data.get("amount"), "amount"),
        "fees": _parse_numeric(data.get("fees"), "fees"),
        "taxes": _parse_numeric(data.get("taxes"), "taxes"),
        "accrued_interest": _parse_numeric(data.get("accrued_interest"), "accrued_interest"),
        "net_transaction_value": _parse_numeric(data.get("net_transaction_value"), "net_transaction_value"),
    }


def validate_instrument_input(data):
    """Validate and clean new instrument input data.

    Args:
        data: Raw JSON dict from request

    Returns:
        Cleaned dict with validated fields

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    if not data:
        raise ValidationError("Request body is required")

    security = (data.get("security") or "").strip()
    ticker = (data.get("ticker") or "").strip()
    instrument_type = (data.get("type") or "ETF").strip()
    isin = (data.get("isin") or "").strip() or None

    if not security:
        raise ValidationError("Security name is required")
    if not ticker:
        raise ValidationError("Ticker is required")

    try:
        capital_gains_rate = float(data.get("capital_gains_rate", 0.26) or 0.26)
    except (ValueError, TypeError):
        raise ValidationError("Capital gains rate must be a number")

    if capital_gains_rate < 0 or capital_gains_rate > 1:
        raise ValidationError("Capital gains rate must be between 0 and 1")

    return {
        "security": security,
        "ticker": ticker,
        "type": instrument_type,
        "capital_gains_rate": capital_gains_rate,
        "isin": isin,
    }


def validate_sell_simulation_input(data):
    """Validate sell simulation input.

    Args:
        data: Raw JSON dict from request

    Returns:
        Tuple of (security, shares)

    Raises:
        ValidationError: If input is invalid
    """
    if not data:
        raise ValidationError("Request body is required")

    security = (data.get("security") or "").strip()
    if not security:
        raise ValidationError("Security is required")

    try:
        shares = float(data.get("shares", 0) or 0)
    except (ValueError, TypeError):
        raise ValidationError("Shares must be a number")

    if shares <= 0:
        raise ValidationError("Shares must be greater than zero")

    return security, shares


def validate_rebalance_input(data):
    """Validate rebalance simulation input.

    Args:
        data: Raw JSON dict from request

    Returns:
        Tuple of (new_investment, targets)

    Raises:
        ValidationError: If input is invalid
    """
    if not data:
        raise ValidationError("Request body is required")

    try:
        new_investment = float(data.get("new_investment", 0) or 0)
    except (ValueError, TypeError):
        raise ValidationError("New investment must be a number")

    if new_investment < 0:
        raise ValidationError("New investment cannot be negative")

    targets = data.get("targets", {})
    if not isinstance(targets, dict):
        raise ValidationError("Targets must be an object with asset class percentages")

    return new_investment, targets


def _parse_numeric(value, field_name):
    """Parse a numeric field, returning empty string if blank/None."""
    if value is None or value == "":
        return ""
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Field '{field_name}' must be a number")
