"""API blueprints registration."""

from web.api.portfolio import portfolio_bp
from web.api.performance import performance_bp
from web.api.transactions import transactions_bp
from web.api.rebalance import rebalance_bp


def register_api_routes(app):
    """Register all API blueprints on the Flask app."""
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(rebalance_bp)
