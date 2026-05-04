"""Application configuration helpers.

Provides a single access point for config and transactions paths,
avoiding repetitive current_app.config lookups in every endpoint.
"""

from flask import current_app


def get_paths():
    """Return (config_path, transactions_path) from the current Flask app context.

    Usage in endpoints:
        config_path, transactions_path = get_paths()
    """
    return current_app.config["CONFIG_PATH"], current_app.config["TRANSACTIONS_PATH"]
