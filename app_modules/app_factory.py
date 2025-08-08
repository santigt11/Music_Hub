"""Factory para crear la aplicación Flask y exponer singletons"""
from __future__ import annotations
from flask import Flask
from flask_cors import CORS
from .services.qobuz import QobuzDownloader

_downloader: QobuzDownloader | None = None
_app: Flask | None = None


def get_downloader() -> QobuzDownloader:
    global _downloader
    if _downloader is None:
        _downloader = QobuzDownloader()
    return _downloader


def create_app() -> Flask:
    global _app
    if _app is not None:
        return _app
    app = Flask(__name__)
    CORS(app)
    # Registro de blueprints
    from .routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    _app = app
    return app

__all__ = ["create_app", "get_downloader"]
