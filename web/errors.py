"""Centralized error handling for the Flask app.

All API errors follow a consistent format:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable description"
    }
}
"""

from flask import jsonify


class APIError(Exception):
    """Base API error with status code and error code."""

    def __init__(self, message, code="INTERNAL_ERROR", status=500):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(message)


class ValidationError(APIError):
    """Input validation failed."""

    def __init__(self, message):
        super().__init__(message, code="VALIDATION_ERROR", status=400)


class NotFoundError(APIError):
    """Resource not found."""

    def __init__(self, message):
        super().__init__(message, code="NOT_FOUND", status=404)


class ConflictError(APIError):
    """Resource already exists."""

    def __init__(self, message):
        super().__init__(message, code="CONFLICT", status=409)


class MarketDataError(APIError):
    """Failed to fetch market data."""

    def __init__(self, message):
        super().__init__(message, code="MARKET_DATA_ERROR", status=502)


def register_error_handlers(app):
    """Register global error handlers on the Flask app."""

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle all custom API errors."""
        response = jsonify({
            "error": {
                "code": error.code,
                "message": error.message,
            }
        })
        response.status_code = error.status
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle Flask 404."""
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
            }
        }), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle unexpected errors."""
        app.logger.exception("Unhandled exception")
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            }
        }), 500
