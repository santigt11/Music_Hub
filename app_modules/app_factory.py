"""Factory para crear la aplicación Flask y exponer singletons.

El 500 en '/' provenía de TemplateNotFound porque al instanciar Flask con
``Flask(__name__)`` dentro de ``app_modules`` buscaba ``app_modules/templates``.
Las plantillas reales viven en ``../templates`` y los estáticos en ``../static``.
Se ajustan las rutas explícitamente.
"""
from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, send_from_directory
import logging
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

    # Base del proyecto (carpeta que contiene app_modules)
    base_dir = Path(__file__).resolve().parent.parent
    templates_dir = base_dir / 'templates'
    static_dir = base_dir / 'static'

    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir)
    )
    CORS(app)

    # Registro de blueprints API
    from .routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        from flask import render_template
        try:
            return render_template('index.html')
        except Exception as e:
            logging.getLogger(__name__).exception("Error renderizando index.html")
            # Fallback mínimo para no responder 500
            return ('<html><head><title>Music Hub</title></head>'
                    '<body><h1>Music Hub</h1><p>No se pudo cargar la interfaz.'
                    ' Verifica que la carpeta templates esté desplegada.</p></body></html>', 200)

    @app.route('/favicon.ico')
    def favicon():
        """Intentar servir favicon si existe; si no, 204 para evitar spam de 404."""
        ico_path = static_dir / 'favicon.ico'
        if ico_path.exists():
            # send_from_directory necesita ruta absoluta y filename
            return send_from_directory(static_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
        return ('', 204)

    @app.route('/favicon.png')
    def favicon_png():
        png_path = static_dir / 'favicon.png'
        if png_path.exists():
            return send_from_directory(static_dir, 'favicon.png', mimetype='image/png')
        return ('', 204)

    _app = app
    return app

__all__ = ["create_app", "get_downloader"]
