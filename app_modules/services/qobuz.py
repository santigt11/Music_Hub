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

    def search_with_similarity(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca en Qobuz y ordena resultados por similitud con la consulta.

        Se usa para mapear resultados validados por Genius a pistas de Qobuz.
        """
        try:
            raw_tracks = self.search_tracks_with_locale(query, limit=20, force_latin=True)
            if not raw_tracks:
                return []

            q_clean = self._clean_lyrics_text(query)
            q_tokens = q_clean.split()

            def jaccard(a: List[str], b: List[str]) -> float:
                sa, sb = set(a), set(b)
                if not sa or not sb:
                    return 0.0
                inter = len(sa & sb)
                union = len(sa | sb)
                return inter / union if union else 0.0

            scored = []
            for t in raw_tracks:
                title = (t.get('title') or '')
                artist = (t.get('performer', {}) or {}).get('name', '')
                cand_clean = self._clean_lyrics_text(f"{title} {artist}")
                c_tokens = cand_clean.split()
                score = jaccard(q_tokens, c_tokens)

                # Pequeños boosts por inclusiones directas
                if q_clean and cand_clean:
                    if q_clean in cand_clean:
                        score += 0.2
                    elif cand_clean in q_clean:
                        score += 0.1

                scored.append((score, t))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [t for _, t in scored[:limit]]
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
    def _clean_lyrics_text(self, text: str) -> str:
        """Limpia texto removiendo símbolos, tildes y normalizando espacios"""
        try:
            if not text:
                return ''
            # Quitar tildes/diacríticos
            text = unicodedata.normalize('NFKD', text)
            text = ''.join(c for c in text if not unicodedata.combining(c))
            # Lowercase
            text = text.lower()
            # Quitar TODO excepto letras, números y espacios
            text = re.sub(r'[^a-z0-9\s]', ' ', text)
            # Colapsar múltiples espacios en uno
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception:
            return text or ''

    def _fetch_genius_lyrics(self, url: str) -> str:
        """Obtiene la letra completa de una página de Genius"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive'
            }
            
            print(f"[FETCH] Descargando letras de: {url}")
            
            r = self.session.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                print(f"[FETCH] Error HTTP {r.status_code}")
                return ''
            
            html = r.text
            soup = BeautifulSoup(html, 'html.parser')
            
            parts: List[str] = []
            
            # Método 1: Contenedores modernos con data-lyrics-container="true"
            containers = soup.find_all(attrs={'data-lyrics-container': 'true'})
            if containers:
                print(f"[FETCH] Encontrados {len(containers)} contenedores modernos")
                for container in containers:
                    # Preservar saltos de línea
                    for br in container.find_all('br'):
                        br.replace_with('\n')
                    
                    text = container.get_text(separator='\n', strip=True)
                    if text:
                        parts.append(text)
            
            # Método 2: Contenedores con clase específica de letras
            if not parts:
                lyrics_divs = soup.find_all('div', class_=re.compile(r'.*[Ll]yrics.*'))
                if lyrics_divs:
                    print(f"[FETCH] Encontrados {len(lyrics_divs)} divs de letras por clase")
                    for div in lyrics_divs:
                        for br in div.find_all('br'):
                            br.replace_with('\n')
                        text = div.get_text(separator='\n', strip=True)
                        if text and len(text) > 50:  # Solo textos sustanciales
                            parts.append(text)
            
            # Método 3: Fallback - buscar divs con mucho texto
            if not parts:
                all_divs = soup.find_all('div')
                print(f"[FETCH] Fallback: analizando {len(all_divs)} divs")
                for div in all_divs:
                    text = div.get_text(strip=True)
                    # Si el div tiene mucho texto y parece contener letras
                    if len(text) > 200 and '\n' in text and not div.find('script'):
                        for br in div.find_all('br'):
                            br.replace_with('\n')
                        clean_text = div.get_text(separator='\n', strip=True)
                        parts.append(clean_text)
                        break
            
            if parts:
                lyrics = '\n'.join(parts)
                print(f"[FETCH] Letras extraídas: {len(lyrics)} caracteres")
                return lyrics
            else:
                print("[FETCH] No se encontraron letras")
                return ''
                
        except Exception as e:
            print(f"[FETCH] Error obteniendo letras de {url}: {e}")
            return ''

    def search_lyrics_genius(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca canciones en Genius usando múltiples métodos"""
        try:
            print(f"[GENIUS] Iniciando búsqueda: '{query[:50]}...'")
            
            # Método 1: Intentar API oficial de Genius si está disponible
            songs = self._try_genius_api(query, limit)
            if songs:
                print(f"[GENIUS] API exitosa: {len(songs)} resultados")
                return songs
            
            # Método 2: Scraping web como fallback
            songs = self._try_genius_scraping(query, limit)
            if songs:
                print(f"[GENIUS] Scraping exitoso: {len(songs)} resultados")
                return songs
            
            print("[GENIUS] No se encontraron resultados")
            return []
            
        except Exception as e:
            print(f"[GENIUS] Error general: {e}")
            return []
    
    def _try_genius_api(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Intenta usar la API oficial de Genius con token"""
        try:
            import urllib.parse
            
            # Token oficial del API de Genius
            genius_token = "bOb0AM7TteQJ9J2t1JjQtHfSw2qlhp_U5oyFRenLmshiQw0jgrowXLyurdbda6Rt"
            
            headers = {
                'Authorization': f'Bearer {genius_token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Usar la API oficial de búsqueda
            encoded_query = urllib.parse.quote(query)
            api_url = f"https://api.genius.com/search?q={encoded_query}"
            
            print(f"[GENIUS API] Buscando en: {api_url}")
            
            resp = self.session.get(api_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[GENIUS API] Error HTTP: {resp.status_code}")
                return []
            
            data = resp.json()
            
            if 'response' not in data or 'hits' not in data['response']:
                print("[GENIUS API] Estructura de respuesta inesperada")
                return []
            
            hits = data['response']['hits']
            print(f"[GENIUS API] Encontrados {len(hits)} hits")
            
            songs = []
            for hit in hits[:limit]:
                try:
                    result = hit.get('result', {})
                    
                    title = result.get('title', '')
                    artist_info = result.get('primary_artist', {})
                    artist = artist_info.get('name', 'Unknown') if artist_info else 'Unknown'
                    url = result.get('url', '')
                    genius_id = result.get('id', '')
                    
                    if title and url:
                        song_data = {
                            'title': title,
                            'artist': artist,
                            'url': url,
                            'genius_id': str(genius_id),
                            'found_by_lyrics': True
                        }
                        songs.append(song_data)
                        print(f"[GENIUS API] ✓ {title} - {artist}")
                
                except Exception as e:
                    print(f"[GENIUS API] Error procesando hit: {e}")
                    continue
            
            return songs
                
        except Exception as e:
            print(f"[GENIUS API] Error general: {e}")
            return []
    
    def _try_genius_scraping(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Scraping como fallback"""
        try:
            import urllib.parse
            
            # Usar palabras clave si la query es muy larga
            words = query.split()
            if len(words) > 10:
                key_words = [w for w in words if len(w) > 3][:5]
                search_query = ' '.join(key_words)
            else:
                search_query = query
            
            print(f"[GENIUS SCRAPING] Buscando: '{search_query}'")
            
            url = f"https://genius.com/search?q={urllib.parse.quote_plus(search_query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            songs = []
            
            # Buscar enlaces de canciones
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'lyrics' in href and not href.startswith('#'):
                    title = link.get_text(strip=True)
                    
                    if not href.startswith('http'):
                        href = f"https://genius.com{href}"
                    
                    if title and len(title) > 2:
                        songs.append({
                            'title': title,
                            'artist': 'Unknown',
                            'url': href,
                            'genius_id': href.split('/')[-1],
                            'found_by_lyrics': True
                        })
                        
                        if len(songs) >= limit:
                            break
            
            return songs
            
        except Exception as e:
            print(f"[GENIUS SCRAPING] Error: {e}")
            return []

    def search_by_lyrics(self, query: str, limit: int = 1) -> List[Dict[str, Any]]:
        """Busca canciones por fragmento de letra usando únicamente resultados validados por Genius.

        Nota: si no hay un match claro en Qobuz para la canción validada por letras, NO devuelve
        un resultado por letra alternativo. En ese caso, la UI mostrará sólo la búsqueda normal.
        """
        try:
            print(f"[LYRICS] Buscando: '{query}'")
            
            # Limpiar la consulta
            clean_query = self._clean_lyrics_text(query)
            if len(clean_query.split()) < 3:
                return []
            
            # Intentar búsqueda real en Genius (con verificación de letras y mapeo estricto a Qobuz)
            results = self._search_genius_for_lyrics(clean_query, limit)
            
            # Marcar metadatos si hay resultados
            for result in results:
                result['found_by_lyrics'] = True
                result['lyrics_fragment'] = query[:100]
                result['matched_fragment'] = query[:100]
            
            print(f"[LYRICS] Retornando {len(results)} resultados")
            return results[:limit]
            
        except Exception as e:
            print(f"[LYRICS] Error en search_by_lyrics: {e}")
            return []
    
    def _search_genius_for_lyrics(self, clean_query: str, limit: int) -> List[Dict[str, Any]]:
        """Búsqueda real en Genius con verificación de letras usando API oficial y mapeo estricto a Qobuz."""
        try:
            # Buscar candidatos en Genius usando API oficial
            candidates = self._search_genius_api(clean_query, limit=10)

            def jaccard(a_tokens: List[str], b_tokens: List[str]) -> float:
                a_set, b_set = set(a_tokens), set(b_tokens)
                if not a_set or not b_set:
                    return 0.0
                inter = len(a_set & b_set)
                union = len(a_set | b_set)
                return inter / union if union else 0.0

            results: List[Dict[str, Any]] = []
            for candidate in candidates[:5]:  # Solo verificar los primeros 5
                try:
                    # Descargar letras
                    lyrics = self._fetch_genius_lyrics(candidate['url'])
                    if not lyrics:
                        continue

                    # Verificar coincidencia exacta del fragmento limpiado
                    clean_lyrics = self._clean_lyrics_text(lyrics)
                    if clean_query not in clean_lyrics:
                        continue

                    print(f"[LYRICS] ¡Coincidencia de letra en: {candidate['title']} - {candidate['artist']}!")

                    # Preparar términos limpios para matching
                    genius_title_clean = self._clean_lyrics_text(candidate['title'])
                    genius_artist_clean = self._clean_lyrics_text(candidate['artist'])
                    genius_title_tokens = [t for t in genius_title_clean.split() if t]
                    genius_artist_tokens = [t for t in genius_artist_clean.split() if t]

                    # Intentar diferentes queries en Qobuz para mejorar el mapeo
                    q_queries = [
                        f"{candidate['title']} {candidate['artist']}",
                        f"{candidate['artist']} {candidate['title']}"
                    ]

                    seen_ids = set()
                    q_matches: List[Dict[str, Any]] = []
                    for q in q_queries:
                        qobuz_results = self.search_with_similarity(q, limit=5)
                        for track in qobuz_results:
                            tid = track.get('id')
                            if tid in seen_ids:
                                continue
                            seen_ids.add(tid)

                            q_title = track.get('title', '')
                            q_artist = track.get('performer', {}).get('name', '')
                            q_title_clean = self._clean_lyrics_text(q_title)
                            q_artist_clean = self._clean_lyrics_text(q_artist)
                            q_title_tokens = [t for t in q_title_clean.split() if t]
                            q_artist_tokens = [t for t in q_artist_clean.split() if t]

                            # Reglas de matching estricto: artista debe coincidir claramente
                            artist_ratio = jaccard(genius_artist_tokens, q_artist_tokens)
                            artist_ok = (
                                genius_artist_clean == q_artist_clean or
                                genius_artist_clean in q_artist_clean or
                                q_artist_clean in genius_artist_clean or
                                artist_ratio >= 0.6
                            )

                            # Matching de título: permitir exacto, inclusión o jaccard alto
                            title_ratio = jaccard(genius_title_tokens, q_title_tokens)
                            title_ok = (
                                genius_title_clean == q_title_clean or
                                genius_title_clean in q_title_clean or
                                q_title_clean in genius_title_clean or
                                title_ratio >= 0.6
                            )

                            if artist_ok and title_ok:
                                print(f"[LYRICS]  ✅ Match Qobuz: {q_title} - {q_artist} (artist_ratio={artist_ratio:.2f}, title_ratio={title_ratio:.2f})")
                                q_matches.append(track)
                            else:
                                print(f"[LYRICS]  ❌ Descarta: {q_title} - {q_artist} (artist_ratio={artist_ratio:.2f}, title_ratio={title_ratio:.2f})")

                    # Ordenar matches por suma de ratios y elegir los primeros
                    def score_track(track: Dict[str, Any]) -> float:
                        q_title = self._clean_lyrics_text(track.get('title', ''))
                        q_artist = self._clean_lyrics_text(track.get('performer', {}).get('name', ''))
                        t_ratio = jaccard(genius_title_clean.split(), q_title.split())
                        a_ratio = jaccard(genius_artist_clean.split(), q_artist.split())
                        return t_ratio + a_ratio

                    q_matches.sort(key=score_track, reverse=True)
                    for track in q_matches:
                        t_copy = track.copy()
                        t_copy['genius_match'] = True
                        t_copy['genius_url'] = candidate.get('url')
                        results.append(t_copy)
                        if len(results) >= limit:
                            break

                    if len(results) >= limit:
                        break

                except Exception as e:
                    print(f"[LYRICS] Error verificando {candidate.get('title')}: {e}")
                    continue

            return results

        except Exception as e:
            print(f"[LYRICS] Error en búsqueda Genius: {e}")
            return []

    def _search_genius_api(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca canciones usando el API oficial de Genius"""
        try:
            import urllib.parse
            
            # Tu token de Genius
            genius_token = "bOb0AM7TteQJ9J2t1JjQtHfSw2qlhp_U5oyFRenLmshiQw0jgrowXLyurdbda6Rt"
            
            headers = {
                'Authorization': f'Bearer {genius_token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Codificar la query
            encoded_query = urllib.parse.quote(query)
            api_url = f"https://api.genius.com/search?q={encoded_query}"
            
            print(f"[GENIUS API] Buscando: {api_url}")
            
            response = self.session.get(api_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"[GENIUS API] Error {response.status_code}: {response.text}")
                return []
            
            data = response.json()
            
            if 'response' not in data or 'hits' not in data['response']:
                print("[GENIUS API] Formato de respuesta inesperado")
                return []
            
            hits = data['response']['hits']
            songs = []
            
            for hit in hits[:limit]:
                try:
                    result = hit.get('result', {})
                    
                    title = result.get('title', 'Unknown')
                    artist = result.get('primary_artist', {}).get('name', 'Unknown')
                    url = result.get('url', '')
                    
                    if title and url:
                        songs.append({
                            'title': title,
                            'artist': artist,
                            'url': url,
                            'genius_id': result.get('id'),
                            'found_by_lyrics': True
                        })
                        
                except Exception as e:
                    print(f"[GENIUS API] Error procesando hit: {e}")
                    continue
            
            print(f"[GENIUS API] Encontradas {len(songs)} canciones")
            return songs
            
        except Exception as e:
            print(f"[GENIUS API] Error: {e}")
            return []
    
    def _search_by_keywords(self, clean_query: str, limit: int) -> List[Dict[str, Any]]:
        """Búsqueda alternativa por palabras clave directamente en Qobuz"""
        try:
            # Extraer palabras significativas
            words = clean_query.split()
            
            # Filtrar palabras comunes y muy cortas
            stop_words = {'que', 'para', 'con', 'por', 'una', 'este', 'como', 'son', 'las', 'los', 'del', 'de', 'la', 'el', 'en', 'y', 'es', 'no', 'me', 'te', 'se', 'si'}
            significant_words = [w for w in words if len(w) > 2 and w not in stop_words]
            
            # Estrategias de búsqueda
            search_strategies = []
            
            # 1. Frases distintivas (secuencias de 3-4 palabras)
            for i in range(len(significant_words) - 2):
                phrase = ' '.join(significant_words[i:i+3])
                search_strategies.append(phrase)
            
            # 2. Palabras individuales más largas (probablemente más únicas)
            long_words = [w for w in significant_words if len(w) > 5]
            search_strategies.extend(long_words[:3])
            
            # 3. Combinaciones de palabras clave
            if len(significant_words) >= 2:
                search_strategies.append(' '.join(significant_words[:2]))
                search_strategies.append(' '.join(significant_words[-2:]))
            
            print(f"[KEYWORDS] Probando {len(search_strategies)} estrategias")
            
            results = []
            seen_ids = set()
            
            for strategy in search_strategies[:5]:  # Máximo 5 estrategias
                try:
                    print(f"[KEYWORDS] Buscando: '{strategy}'")
                    
                    tracks = self.search_tracks_with_locale(strategy, limit=5, force_latin=True)
                    
                    for track in tracks:
                        track_id = track.get('id')
                        if track_id not in seen_ids:
                            seen_ids.add(track_id)
                            
                            # Calcular relevancia basada en coincidencias
                            title = track.get('title', '').lower()
                            artist = track.get('performer', {}).get('name', '').lower()
                            
                            score = 0
                            for word in significant_words:
                                if word in title:
                                    score += 3
                                if word in artist:
                                    score += 2
                            
                            # Solo incluir si tiene cierta relevancia
                            if score >= 3:
                                track['keyword_score'] = score
                                results.append(track)
                                print(f"[KEYWORDS] Agregado: {title} (score: {score})")
                                
                                if len(results) >= limit:
                                    break
                    
                    if len(results) >= limit:
                        break
                        
                except Exception as e:
                    print(f"[KEYWORDS] Error con estrategia '{strategy}': {e}")
                    continue
            
            # Ordenar por puntuación
            results.sort(key=lambda x: x.get('keyword_score', 0), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            print(f"[KEYWORDS] Error: {e}")
            return []

__all__ = ["QobuzDownloader"]
