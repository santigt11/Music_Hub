import json
import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path cuando se ejecuta este archivo directamente
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app_modules.services.qobuz import QobuzDownloader

if __name__ == "__main__":
    q = QobuzDownloader()
    phrase = 'y si te digo que es para toda la vida pero no como esos'
    res = q.search_by_lyrics(phrase, limit=1)
    out = {
        'count': len(res),
        'res': [
            {
                'id': r.get('id'),
                'title': r.get('title'),
                'artist': (r.get('performer') or {}).get('name',''),
                'source': r.get('source'),
                'genius_match': r.get('genius_match'),
                'genius_url': r.get('genius_url')
            } for r in res
        ]
    }
    print(json.dumps(out, ensure_ascii=False))
