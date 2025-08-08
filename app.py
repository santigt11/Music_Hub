"""Bootstrap de la aplicación.

Se mantiene el nombre y exportaciones originales para compatibilidad (tests, Vercel, etc.).
La lógica se ha movido a módulos dentro de app_modules.
"""
import os
from app_modules.app_factory import create_app, get_downloader
from app_modules.config import PORT, FLASK_DEBUG, QOBUZ_TOKEN
import os  # Añadido para usar variables de entorno en el guard del main

# Crear instancia de la app y del downloader (lazy en factory)
app = create_app()
downloader = get_downloader()

# Alias para despliegues (wsgi, vercel)
application = app

def handler(request):  # Compatibilidad Vercel
    return app

if __name__ == '__main__':
    if not (os.environ.get('FUNCTIONS_WORKER_RUNTIME') or os.environ.get('VERCEL')):
        app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=PORT)
