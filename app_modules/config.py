import os

# Configuración general y constantes
QOBUZ_TOKEN = os.environ.get('QOBUZ_TOKEN', "wGhVEBhBrpMHmQ1TnZ7njn0_WuGUUeujgHP-KBerx1DRiYeKcgO0Czm8_Us6W9WvxPWmJd0IEnEBi75FE0qE1w")

# Flask settings
FLASK_DEBUG = os.environ.get('FLASK_ENV') == 'development'
PORT = int(os.environ.get('PORT', 5000))

__all__ = ["QOBUZ_TOKEN", "FLASK_DEBUG", "PORT"]
