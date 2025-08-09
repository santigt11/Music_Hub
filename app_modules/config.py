import os

# Configuración general y constantes
QOBUZ_TOKEN = os.environ.get('QOBUZ_TOKEN', "wGhVEBhBrpMHmQ1TnZ7njn0_WuGUUeujgHP-KBerx1DRiYeKcgO0Czm8_Us6W9WvxPWmJd0IEnEBi75FE0qE1w")

# Token de Genius API - usar variable de entorno o fallback
GENIUS_TOKEN = os.environ.get('GENIUS_TOKEN', "bOb0AM7TteQJ9J2t1JjQtHfSw2qlhp_U5oyFRenLmshiQw0jgrowXLyurdbda6Rt")

# Flask settings
FLASK_DEBUG = os.environ.get('FLASK_ENV') == 'development'
PORT = int(os.environ.get('PORT', 5000))

__all__ = ["QOBUZ_TOKEN", "GENIUS_TOKEN", "FLASK_DEBUG", "PORT"]
