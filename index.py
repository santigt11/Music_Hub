"""
Punto de entrada para Vercel
"""
import os

# Configurar variables de entorno para Vercel
os.environ['VERCEL'] = '1'

# Importar la aplicación Flask
from app import app

# Esta es la aplicación que Vercel ejecutará
# Vercel espera una variable llamada 'app' o 'application'
application = app

# Para desarrollo local
if __name__ == "__main__":
    # Configurar para desarrollo local
    os.environ['FLASK_ENV'] = 'development'
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
