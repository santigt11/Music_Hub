"""
Aplicación Flask optimizada para Vercel
"""
import os
import sys

# Configurar entorno para Vercel
os.environ['VERCEL'] = '1'
os.environ['FLASK_ENV'] = 'production'

# Importar la aplicación principal
from app import app

# Esta es la aplicación que Vercel usará
application = app

# Para compatibilidad con diferentes formatos de handler
def handler(request):
    return app

# Para desarrollo local
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)