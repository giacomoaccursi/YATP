"""Web UI: Flask app creation and server launch."""

import webbrowser
import threading
import os
from flask import Flask, render_template
from web.api import register_api_routes


def create_app(config_path, transactions_path):
    """Create and configure the Flask app."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["CONFIG_PATH"] = config_path
    app.config["TRANSACTIONS_PATH"] = transactions_path

    @app.route("/")
    def index():
        return render_template("index.html")

    register_api_routes(app)
    return app


def launch(config_path, transactions_path, port=5000):
    """Launch the web UI and open the browser."""
    app = create_app(config_path, transactions_path)

    def open_browser():
        webbrowser.open(f"http://localhost:{port}")

    threading.Timer(1.0, open_browser).start()
    app.run(port=port, debug=False)
