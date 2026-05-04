"""Web UI: Flask app creation and server launch."""

import webbrowser
import threading
import os
from flask import Flask, send_from_directory
from web.api import register_api_routes
from web.errors import register_error_handlers


def create_app(config_path, transactions_path):
    """Create and configure the Flask app."""
    import logging

    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["CONFIG_PATH"] = config_path
    app.config["TRANSACTIONS_PATH"] = transactions_path

    # Configure logging
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    templates_dir = os.path.join(os.path.dirname(__file__), "templates")

    @app.route("/")
    def index():
        return send_from_directory(templates_dir, "index.html")

    @app.route("/instruments")
    def instruments_page():
        return send_from_directory(templates_dir, "instruments.html")

    @app.route("/performance")
    def performance_page():
        return send_from_directory(templates_dir, "performance.html")

    @app.route("/rebalance")
    def rebalance_page():
        return send_from_directory(templates_dir, "rebalance.html")

    @app.route("/sell-simulator")
    def sell_simulator_page():
        return send_from_directory(templates_dir, "sell-simulator.html")

    @app.route("/transactions")
    def transactions_page():
        return send_from_directory(templates_dir, "transactions.html")

    register_api_routes(app)
    register_error_handlers(app)
    return app


def launch(config_path, transactions_path, port=5050):
    """Launch the web UI and open the browser."""
    app = create_app(config_path, transactions_path)

    def open_browser():
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=port, debug=False)
