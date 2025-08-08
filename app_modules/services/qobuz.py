"""Servicio principal para interacción con la API de Qobuz"""
from __future__ import annotations
import time
import hashlib
import re
import json
from typing import List, Dict, Any, Optional
import unicodedata
from bs4 import BeautifulSoup
import requests
from .spotify import SpotifyHandler
from ..config import QOBUZ_TOKEN

class QobuzDownloader:
    base_url = "https://www.qobuz.com/api.json/0.2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'application/json', 'Accept-Language': 'en-US,en;q=0.9'})
        self.token = QOBUZ_TOKEN
        self.app_id: Optional[str] = None
        self.app_secret: Optional[str] = None
        self.user_id: Optional[str] = None
        self.quality_map = {
            '5': {'name': 'MP3 320 kbps', 'ext': '.mp3'},
            '6': {'name': 'FLAC 16-bit/44.1kHz', 'ext': '.flac'},
            '7': {'name': 'FLAC 24-bit/96kHz', 'ext': '.flac'},
            '27': {'name': 'FLAC 24-bit/192kHz', 'ext': '.flac'}
        }
        self.spotify = SpotifyHandler()
        self.initialize_qobuz_session()

    # --- Inicialización ---
    def initialize_qobuz_session(self) -> bool:
        try:
            self.app_id = self.get_app_id()
            self.app_secret = self.get_app_secret(self.app_id, self.token)
            user_info = self.get_user_info(self.token)
            if user_info:
                self.user_id = str(user_info.get('id', '0'))
            return True
        except Exception:
            return False

    def get_app_id(self) -> str:
        try:
            url = "https://www.qobuz.com/api.json/0.2/app/config"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'app' in data and 'id' in data['app']:
                    return str(data['app']['id'])
            known_app_ids = ["285473059", "798273057", "950118473"]
            for app_id in known_app_ids:
                if self.test_app_id(app_id):
                    return app_id
            return "285473059"
        except Exception:
            return "285473059"

    def test_app_id(self, app_id: str) -> bool:
        try:
            params = {'query': 'test', 'type': 'tracks', 'limit': 1, 'app_id': app_id}
            response = self.session.get(f"{self.base_url}/catalog/search", params=params, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_app_secret(self, app_id: str, user_auth_token: str) -> str:
        try:
            url = f"{self.base_url}/app/getSecret"
            params = {'app_id': app_id, 'user_auth_token': user_auth_token}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'app_secret' in data:
                    return data['app_secret']
            return "abb21364945c0583309667d13ca3d93a"
        except Exception:
            return "abb21364945c0583309667d13ca3d93a"

    def get_user_info(self, user_auth_token: str) -> Optional[Dict[str, Any]]:
        try:
            endpoints = [f"{self.base_url}/user/login", f"{self.base_url}/user/info"]
            for endpoint in endpoints:
                try:
                    params = {'user_auth_token': user_auth_token, 'app_id': self.app_id}
                    response = self.session.get(endpoint, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        user_data = data.get('user', data)
                        if 'id' in user_data or 'email' in user_data:
                            return user_data
                except Exception:
                    continue
            return None
        except Exception:
            return None

    # --- Búsquedas ---
    def search_tracks(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            params = {'query': query, 'type': 'track', 'limit': limit, 'app_id': self.app_id, 'user_auth_token': self.token}
            r = self.session.get(f'{self.base_url}/track/search', params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get('tracks', {}).get('items', [])
            return []
        except Exception:
            return []

    # ---- Localización y corrección de metadatos ----
    def contains_non_latin_chars(self, text: str) -> bool:
        if not text:
            return False
        for char in text:
            code = ord(char)
            if 0x3040 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF or 0xAC00 <= code <= 0xD7AF or 0x0600 <= code <= 0x06FF or 0x0400 <= code <= 0x04FF:
                return True
        return False

    def search_tracks_with_locale(self, query: str, limit: int = 15, force_latin: bool = True) -> List[Dict[str, Any]]:
        try:
            params = {'query': query, 'type': 'track', 'limit': limit, 'app_id': self.app_id, 'user_auth_token': self.token}
            if force_latin:
                params.update({'locale': 'en_US', 'country': 'US', 'language': 'en'})
            r = self.session.get(f'{self.base_url}/track/search', params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get('tracks', {}).get('items', [])
            return []
        except Exception:
            return []

    def fix_qobuz_locale_metadata(self, track_info: Dict[str, Any]) -> Dict[str, Any]:
        try:
            track_id = track_info.get('id')
            if not track_id:
                return track_info
            attempts = [ {'locale': 'en_US', 'country': 'US'}, {'locale': 'en_GB', 'country': 'GB'}, {'locale': 'en_CA', 'country': 'CA'}, {} ]
            for cfg in attempts:
                try:
                    params = {'track_id': track_id, 'app_id': self.app_id, 'user_auth_token': self.token}
                    params.update(cfg)
                    r = self.session.get(f'{self.base_url}/track/get', params=params, timeout=8)
                    if r.status_code == 200:
                        data = r.json()
                        title = data.get('title', '')
                        artist = data.get('performer', {}).get('name', '')
                        if not self.contains_non_latin_chars(title) and not self.contains_non_latin_chars(artist):
                            return data
                except Exception:
                    continue
            return track_info
        except Exception:
            return track_info

    def get_track_info(self, track_id: str) -> Optional[Dict[str, Any]]:
        try:
            params = {'track_id': track_id, 'app_id': self.app_id, 'user_auth_token': self.token}
            r = self.session.get(f'{self.base_url}/track/get', params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None

    # --- Descarga ---
    def get_track_url(self, track_id: str, quality: str = '6') -> Optional[str]:
        try:
            track_info = self.get_track_info(track_id)
            if not track_info:
                return None
            unix_timestamp = int(time.time())
            ts = str(unix_timestamp)
            hash_string = f"trackgetFileUrlformat_id{quality}intentstreamtrack_id{track_id}{ts}{self.app_secret}"
            sig = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
            params = {'request_ts': ts, 'request_sig': sig, 'track_id': track_id, 'format_id': quality, 'intent': 'stream', 'app_id': self.app_id, 'user_auth_token': self.token}
            url = f"{self.base_url}/track/getFileUrl"
            r = self.session.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get('url')
            return None
        except Exception:
            return None

    # --- Matching desde Spotify ---
    def search_track_from_spotify_info(self, spotify_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        import unicodedata, re as _re
        def norm(s: str) -> str:
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            s = _re.sub(r'[\(\)\[\]\-_/]', ' ', s)
            s = _re.sub(r'\s+', ' ', s)
            return s.strip()
        artist = norm(spotify_info.get('artist', ''))
        title = norm(spotify_info.get('name', ''))
        base_queries = []
        if title and artist:
            base_queries.extend([
                f'"{title}" "{artist}"',
                f'{title} {artist}',
                f'{artist} {title}',
            ])
        if title:
            base_queries.append(f'"{title}"')
        # Eliminar palabras comunes muy cortas (stop-words simples)
        stop = {'the','and','feat','ft','with','vs'}
        significant = [w for w in title.split() if len(w) > 3 and w.lower() not in stop]
        if artist and significant:
            base_queries.append(f'{artist} {" ".join(significant[:3])}')
        # Añadir versión sin paréntesis
        simple_title = _re.sub(r'\s*\([^)]*\)', '', title).strip()
        if simple_title != title and artist:
            base_queries.append(f'{simple_title} {artist}')
        seen = set(); queries = []
        for q in base_queries:
            if q.lower() not in seen:
                queries.append(q); seen.add(q.lower())
        for query in queries:
            tracks = self.search_tracks_with_locale(query, limit=30, force_latin=True)
            if tracks:
                best = self.find_best_match(tracks, {'name': title, 'artist': artist, 'duration': spotify_info.get('duration',0)})
                if best:
                    return best
            time.sleep(0.25)
        return None

    def find_best_match(self, qobuz_tracks: List[Dict[str, Any]], spotify_info: Dict[str, Any]):
        def clean(s: str) -> str:
            import unicodedata
            s = unicodedata.normalize('NFKD', s)
            s = re.sub(r'[^\w\s]', '', s)
            s = re.sub(r'\s+', ' ', s)
            return s.lower().strip()
        s_title = clean(spotify_info.get('name', ''))
        s_artist = clean(spotify_info.get('artist', ''))
        s_duration = spotify_info.get('duration', 0)
        best_score = 0; best_track = None
        for t in qobuz_tracks:
            try:
                score = 0
                q_title = clean(t.get('title', ''))
                q_artist = clean(t.get('performer', {}).get('name', ''))
                q_duration = t.get('duration', 0)
                if s_title == q_title:
                    score += 50
                elif s_title and q_title and (s_title in q_title or q_title in s_title):
                    score += 35
                elif self.similar_strings(s_title, q_title):
                    score += 25
                if s_artist == q_artist:
                    score += 40
                elif s_artist and q_artist and (s_artist in q_artist or q_artist in s_artist):
                    score += 30
                elif self.similar_strings(s_artist, q_artist):
                    score += 20
                if s_duration and q_duration:
                    diff = abs(s_duration - q_duration)
                    if diff <= 5:
                        score += 10
                    elif diff <= 15:
                        score += 5
                    elif diff <= 30:
                        score += 2
                if t.get('streamable', False):
                    score += 2
                if score > best_score:
                    best_score = score; best_track = t
            except Exception:
                continue
        if best_track and best_score >= 60:
            return best_track
        if best_track and best_score > 45:
            return best_track
        return None

    def similar_strings(self, s1: str, s2: str, threshold: float = 0.6) -> bool:
        try:
            if not s1 or not s2:
                return False
            w1 = set(s1.split())
            w2 = set(s2.split())
            if not w1 or not w2:
                return False
            common = w1.intersection(w2)
            similarity = len(common) / max(len(w1), len(w2))
            return similarity >= threshold
        except Exception:
            return False

    # --- Lyrics (Genius) ---
    def _normalize_text(self, text: str) -> str:
        try:
            if not text:
                return ''
            # Quitar tildes/diacríticos
            text = unicodedata.normalize('NFKD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            # Lowercase
            text = text.lower()
            # Quitar puntuación
            text = re.sub(r'[^a-z0-9\s]', ' ', text)
            # Colapsar espacios
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception:
            return text or ''

    def _fetch_genius_lyrics(self, url: str) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = self.session.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                return ''
            html = r.text
            soup = BeautifulSoup(html, 'html.parser')
            # Estructura moderna: contenedores con data-lyrics-container="true"
            containers = soup.find_all(attrs={'data-lyrics-container': 'true'})
            parts: List[str] = []
            for c in containers:
                # Cada contenedor tiene múltiples <p> con fragmentos
                for p in c.find_all('p'):
                    parts.append(p.get_text(separator=' ', strip=True))
            if not parts:
                # Fallback antiguo: div.lyrics
                old = soup.select_one('div.lyrics')
                if old:
                    parts.append(old.get_text(separator=' ', strip=True))
            lyrics = '\n'.join(parts)
            return lyrics
        except Exception:
            return ''

    def search_lyrics_genius(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            url = "https://genius.com/api/search/multi"
            resp = self.session.get(url, params={'q': query}, headers=headers, timeout=10)
            songs: List[Dict[str, Any]] = []
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    for section in data.get('response', {}).get('sections', []):
                        if section.get('type') == 'song':
                            for hit in section.get('hits', []):
                                res = hit.get('result', {})
                                if res:
                                    songs.append({'title': res.get('title', ''), 'artist': res.get('primary_artist', {}).get('name', ''), 'url': res.get('url', ''), 'genius_id': res.get('id'), 'found_by_lyrics': True})
                                    if len(songs) >= limit:
                                        break
                        if len(songs) >= limit:
                            break
                except Exception:
                    pass
            # Fallback adicional usando endpoint simple si no hay resultados
            if not songs:
                simple_url = "https://genius.com/api/search"
                r2 = self.session.get(simple_url, params={'q': query}, headers=headers, timeout=10)
                if r2.status_code == 200:
                    try:
                        data2 = r2.json()
                        for hit in data2.get('response', {}).get('hits', []):
                            res = hit.get('result', {})
                            if res.get('type') == 'song' and res:
                                songs.append({'title': res.get('title', ''), 'artist': res.get('primary_artist', {}).get('name', ''), 'url': res.get('url', ''), 'genius_id': res.get('id'), 'found_by_lyrics': True})
                                if len(songs) >= limit:
                                    break
                    except Exception:
                        pass
            return songs[:limit]
        except Exception:
            return []

    def search_by_lyrics(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            # Normalizar el fragmento buscado (ignora tildes, puntuación, mayúsculas)
            normalized_phrase = self._normalize_text(query)
            if not normalized_phrase:
                return []
            # Buscar candidatos en Genius
            genius_songs = self.search_lyrics_genius(query, limit=min(limit, 8))
            if not genius_songs:
                return []
            # Verificar letra real contenga el fragmento normalizado
            for song in genius_songs:
                try:
                    url = song.get('url')
                    lyrics_raw = self._fetch_genius_lyrics(url) if url else ''
                    lyrics_norm = self._normalize_text(lyrics_raw)
                    if lyrics_norm and normalized_phrase in lyrics_norm:
                        artist = song.get('artist') or ''
                        title = song.get('title') or ''
                        q_track = None
                        if artist and title:
                            # Intento de mapeo a Qobuz
                            sp_like = {'name': title, 'artist': artist, 'duration': 0}
                            q_track = self.search_track_from_spotify_info(sp_like)
                            if not q_track:
                                # Fallback directo: queries simples en Qobuz
                                cand_queries = [
                                    f'"{title}" "{artist}"',
                                    f'{title} {artist}',
                                    f'{artist} {title}'
                                ]
                                simple_title = re.sub(r'\s*\([^)]*\)', '', title).strip()
                                if simple_title != title:
                                    cand_queries.append(f'{simple_title} {artist}')
                                for q in cand_queries:
                                    trks = self.search_tracks_with_locale(q, limit=10, force_latin=True)
                                    if trks:
                                        q_track = trks[0]
                                        break
                        if q_track:
                            q_track['found_by_lyrics'] = True
                            q_track['genius_match'] = True
                            q_track['genius_url'] = url
                            q_track['matched_fragment'] = query
                            return [q_track]  # Solo 1 resultado
                except Exception:
                    continue
            return []
        except Exception:
            return []

__all__ = ["QobuzDownloader"]
