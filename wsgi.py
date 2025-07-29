"""
WSGI entry point para Vercel
"""
import os

# Configurar variables de entorno
os.environ['VERCEL'] = '1'

# Importar la aplicación
from app import app

# Esta es la aplicación WSGI
application = app

if __name__ == "__main__":
    application.run()