from flask import Flask
import sys
import os

# Agregar el directorio padre al path para importar app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Handler para Vercel
def handler(request):
    return app