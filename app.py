"""
Qobuz/Spotify Downloader Web API
Backend Flask para la página web
"""

from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
import requests
import json
import re
import os
import sys
import subprocess
import base64
import unicodedata
import traceback
from urllib.parse import urlparse, parse_qs, unquote
import zipfile
import hashlib
import time
from datetime import datetime, timedelta
import tempfile

# Importaciones opcionales para metadatos de música
try:
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC
    from mutagen import File
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("Mutagen no disponible - funcionalidad de metadatos deshabilitada")

from bs4 import BeautifulSoup
import threading
import logging
import shutil
import string

app = Flask(__name__)
CORS(app)

# Configuración del token (SOLO TU PUEDES CAMBIAR ESTO)
QOBUZ_TOKEN = "wGhVEBhBrpMHmQ1TnZ7njn0_WuGUUeujgHP-KBerx1DRiYeKcgO0Czm8_Us6W9WvxPWmJd0IEnEBi75FE0qE1w"

def get_token_info(token=None):
    """
    Obtiene información del token de Qobuz incluyendo información de suscripción
    """
    if not token:
        token = QOBUZ_TOKEN
    
    try:
        # Crear una instancia temporal del downloader para verificar la cuenta
        temp_downloader = QobuzDownloader()
        
        # Intentar obtener información del usuario
        try:
            user_info = temp_downloader.get_user_info(token)
            if user_info:
                info = {
                    'token_valido': True,
                    'tipo': 'Token de Qobuz activo',
                    'usuario': {
                        'id': user_info.get('id'),
                        'email': user_info.get('email', 'No disponible'),
                        'nombre': user_info.get('display_name', user_info.get('firstname', 'No disponible')),
                        'apellido': user_info.get('lastname', ''),
                        'pais': user_info.get('country_code', 'No disponible'),
                        'zona_horaria': user_info.get('zone', 'No disponible')
                    }
                }
                
                # Información de suscripción
                subscription = user_info.get('subscription', {})
                if subscription:
                    info['suscripcion'] = {
                        'tipo': subscription.get('offer', 'No disponible'),
                        'estado': subscription.get('status', 'No disponible'),
                        'inicio': subscription.get('start_date'),
                        'fin': subscription.get('end_date'),
                        'periodo': subscription.get('periodicity', 'No disponible'),
                        'renovacion_automatica': subscription.get('is_recurring', False)
                    }
                    
                    # Calcular días restantes si hay fecha de fin
                    if subscription.get('end_date'):
                        try:
                            # La fecha puede venir en diferentes formatos
                            end_date_str = subscription['end_date']
                            if isinstance(end_date_str, (int, float)):
                                # Si es timestamp
                                end_date = datetime.fromtimestamp(end_date_str)
                            else:
                                # Si es string, intentar parsear
                                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y']:
                                    try:
                                        end_date = datetime.strptime(end_date_str, fmt)
                                        break
                                    except:
                                        continue
                                else:
                                    end_date = None
                            
                            if end_date:
                                now = datetime.now()
                                dias_restantes = (end_date - now).days
                                info['suscripcion']['fecha_expiracion_legible'] = end_date.strftime('%Y-%m-%d %H:%M:%S')
                                info['suscripcion']['dias_restantes'] = dias_restantes
                                info['suscripcion']['expirado'] = now > end_date
                                
                                # Determinar estado de la suscripción
                                if dias_restantes < 0:
                                    info['suscripcion']['estado_detallado'] = 'Expirada'
                                elif dias_restantes <= 7:
                                    info['suscripcion']['estado_detallado'] = 'Próxima a expirar'
                                elif dias_restantes <= 30:
                                    info['suscripcion']['estado_detallado'] = 'Expira pronto'
                                else:
                                    info['suscripcion']['estado_detallado'] = 'Activa'
                        except Exception as e:
                            info['suscripcion']['error_fecha'] = f"Error procesando fecha: {str(e)}"
                
                # Información de calidad disponible
                credential = user_info.get('credential', {})
                if credential:
                    info['calidad'] = {
                        'nivel': credential.get('parameters', {}).get('lossy_streaming', 'No disponible'),
                        'calidad_maxima': credential.get('parameters', {}).get('lossless_streaming', 'No disponible'),
                        'hires_disponible': credential.get('parameters', {}).get('hires_streaming', False)
                    }
                
                return info
            else:
                raise Exception("No se pudo obtener información del usuario")
                
        except Exception as api_error:
            # Si falla la API, hacer análisis básico del token
            info = {
                'token_valido': False,
                'tipo': 'Error en consulta API',
                'error_api': str(api_error),
                'longitud': len(token),
                'primeros_chars': token[:20] + '...' if len(token) > 20 else token,
                'nota': 'El token existe pero no se pudo verificar la suscripción. Puede que esté expirado o inválido.'
            }
            
            # Intentar decodificar el token si está en base64
            try:
                decoded_bytes = base64.b64decode(token + '==')
                decoded_str = decoded_bytes.decode('utf-8')
                if decoded_str.startswith('{'):
                    token_data = json.loads(decoded_str)
                    info['tipo'] = 'Token decodificado (pero API falló)'
                    info['datos_token'] = token_data
            except:
                pass
            
            return info
        
    except Exception as e:
        return {
            'token_valido': False,
            'error': str(e),
            'nota': 'Error crítico al verificar el token'
        }

def add_metadata_to_file(file_path, track_info, cover_url=None):
    """Agregar metadatos a un archivo de audio"""
    if not MUTAGEN_AVAILABLE:
        print("Mutagen no disponible - saltando metadatos")
        return True
    
    try:
        # Detectar el tipo de archivo
        audio_file = File(file_path)
        if audio_file is None:
            print(f"No se pudo cargar el archivo: {file_path}")
            return False
        
        # Obtener información del track (sin transliteración)
        title = track_info.get('title', '')
        artist = track_info.get('artist', '')
        album = track_info.get('album', '')
        year = track_info.get('year', '')
        track_number = track_info.get('track_number', '')
        
        print(f"Aplicando metadatos - Título: '{title}', Artista: '{artist}', Álbum: '{album}'")
        
        # Descargar cover art si está disponible
        cover_data = None
        if cover_url:
            try:
                cover_response = requests.get(cover_url, timeout=10)
                if cover_response.status_code == 200:
                    cover_data = cover_response.content
                    print("Cover descargado correctamente")
            except Exception as e:
                print(f"Error descargando cover: {e}")
        
        # Agregar metadatos según el tipo de archivo
        if isinstance(audio_file, MP3):
            # Archivo MP3
            if audio_file.tags is None:
                audio_file.add_tags()
            
            audio_file.tags.add(TIT2(encoding=3, text=title))
            audio_file.tags.add(TPE1(encoding=3, text=artist))
            audio_file.tags.add(TALB(encoding=3, text=album))
            if year:
                audio_file.tags.add(TDRC(encoding=3, text=str(year)))
            if track_number:
                audio_file.tags.add(TRCK(encoding=3, text=str(track_number)))
            
            # Agregar cover art
            if cover_data:
                audio_file.tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,  # Cover (front)
                    desc='Cover',
                    data=cover_data
                ))
        
        elif isinstance(audio_file, FLAC):
            # Archivo FLAC
            audio_file['TITLE'] = title
            audio_file['ARTIST'] = artist
            audio_file['ALBUM'] = album
            if year:
                audio_file['DATE'] = str(year)
            if track_number:
                audio_file['TRACKNUMBER'] = str(track_number)
            
            # Agregar cover art para FLAC
            if cover_data and MUTAGEN_AVAILABLE:
                try:
                    from mutagen.flac import Picture
                    picture = Picture()
                    picture.type = 3  # Cover (front)
                    picture.mime = 'image/jpeg'
                    picture.desc = 'Cover'
                    picture.data = cover_data
                    audio_file.add_picture(picture)
                except ImportError:
                    print("No se pudo importar Picture de mutagen")
        
        # Guardar cambios
        audio_file.save()
        print("Metadatos agregados correctamente")
        return True
        
    except Exception as e:
        print(f"Error agregando metadatos: {e}")
        import traceback
        traceback.print_exc()
        return False

class SpotifyHandler:
    def __init__(self):
        self.sp = None
    
    def extract_spotify_id(self, url):
        """Extraer ID de Spotify desde URL"""
        try:
            print(f"🔍 Extrayendo ID de Spotify de: {url}")
            
            # Limpiar URL
            if '?' in url:
                url = url.split('?')[0]
            
            patterns = {
                'track': [
                    r'spotify\.com/(?:intl-[a-z-]+/)?track/([a-zA-Z0-9]+)',
                    r'open\.spotify\.com/(?:intl-[a-z-]+/)?track/([a-zA-Z0-9]+)',
                ],
                'playlist': [
                    r'spotify\.com/(?:intl-[a-z-]+/)?playlist/([a-zA-Z0-9]+)',
                    r'open\.spotify\.com/(?:intl-[a-z-]+/)?playlist/([a-zA-Z0-9]+)',
                ]
            }
            
            for type_name, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, url)
                    if match:
                        spotify_id = match.group(1)
                        print(f"✅ Encontrado {type_name} ID: {spotify_id}")
                        return type_name, spotify_id
            
            # URI format: spotify:track:id
            if url.startswith('spotify:'):
                parts = url.split(':')
                if len(parts) >= 3:
                    type_name = parts[1]
                    spotify_id = parts[2]
                    print(f"✅ Encontrado {type_name} ID (URI): {spotify_id}")
                    return type_name, spotify_id
            
            print("❌ No se pudo extraer ID de Spotify")
            return None, None
            
        except Exception as e:
            print(f"❌ Error extrayendo ID: {e}")
            return None, None
    
    def get_track_info_by_scraping(self, track_id):
        """Obtener información del track por scraping mejorado"""
        try:
            print(f"🎵 Obteniendo info de Spotify para track: {track_id}")
            
            # URLs a probar
            urls = [
                f"https://open.spotify.com/track/{track_id}",
                f"https://open.spotify.com/intl-es/track/{track_id}",
                f"https://spotify.com/track/{track_id}"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            for url in urls:
                try:
                    print(f"📡 Intentando: {url}")
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    html = response.text
                    
                    # Método 1: Buscar JSON-LD estructurado
                    json_ld_matches = re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
                    for match in json_ld_matches:
                        try:
                            json_text = match.group(1).strip()
                            json_data = json.loads(json_text)
                            
                            # Puede ser una lista o un objeto
                            if isinstance(json_data, list):
                                for item in json_data:
                                    if item.get('@type') == 'MusicRecording':
                                        json_data = item
                                        break
                            
                            if json_data.get('@type') == 'MusicRecording':
                                title = json_data.get('name', '')
                                artist = ''
                                album = ''
                                
                                # Extraer artista
                                by_artist = json_data.get('byArtist', {})
                                if isinstance(by_artist, list) and by_artist:
                                    artist = by_artist[0].get('name', '')
                                elif isinstance(by_artist, dict):
                                    artist = by_artist.get('name', '')
                                
                                # Extraer álbum
                                in_album = json_data.get('inAlbum', {})
                                if isinstance(in_album, dict):
                                    album = in_album.get('name', '')
                                
                                if title and artist:
                                    print(f"✅ JSON-LD: {title} - {artist}")
                                    return {
                                        'name': title,
                                        'artist': artist,
                                        'album': album,
                                        'duration': 0,
                                        'artists': [artist]
                                    }
                        except json.JSONDecodeError:
                            continue
                    
                    # Método 2: Open Graph meta tags
                    og_title = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
                    og_description = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"', html)
                    
                    if og_title:
                        title = og_title.group(1).strip()
                        artist = "Unknown"
                        album = "Unknown"
                        
                        # Parsear descripción
                        if og_description:
                            desc = og_description.group(1).strip()
                            print(f"📋 Descripción OG: {desc}")
                            
                            # Patrón: "Song · Artist · Album"
                            if " · " in desc:
                                parts = desc.split(" · ")
                                if len(parts) >= 2:
                                    artist = parts[1].strip()
                                    if len(parts) >= 3:
                                        album = parts[2].strip()
                            # Patrón: "Artist - Song"
                            elif " - " in desc:
                                parts = desc.split(" - ", 1)
                                if len(parts) == 2:
                                    artist = parts[0].strip()
                                    title = parts[1].strip()
                            # Patrón: "Song by Artist"
                            elif " by " in desc:
                                match = re.search(r'(.+?) by (.+)', desc)
                                if match:
                                    title = match.group(1).strip()
                                    artist = match.group(2).strip()
                        
                        # Si no se obtuvo artista, buscar en el título
                        if artist == "Unknown" and " - " in title:
                            parts = title.split(" - ", 1)
                            if len(parts) == 2:
                                artist = parts[0].strip()
                                title = parts[1].strip()
                        
                        if title and artist != "Unknown":
                            print(f"✅ Open Graph: {title} - {artist}")
                            return {
                                'name': title,
                                'artist': artist,
                                'album': album,
                                'duration': 0,
                                'artists': [artist]
                            }
                    
                    # Método 3: Buscar en el HTML directo
                    # Buscar patrones de datos estructurados en el HTML
                    patterns = [
                        r'"name":"([^"]+)".*?"artists":\[.*?"name":"([^"]+)"',
                        r'data-testid="entity-title"[^>]*>([^<]+)<.*?data-testid="creator-link"[^>]*>([^<]+)<',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                        if match:
                            title = match.group(1).strip()
                            artist = match.group(2).strip()
                            
                            if title and artist:
                                print(f"✅ Patrón HTML: {title} - {artist}")
                                return {
                                    'name': title,
                                    'artist': artist,
                                    'album': 'Unknown',
                                    'duration': 0,
                                    'artists': [artist]
                                }
                
                except requests.RequestException as e:
                    print(f"❌ Error con {url}: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Error general con {url}: {e}")
                    continue
            
            print("❌ No se pudo obtener información de ninguna URL")
            return None
            
        except Exception as e:
            print(f"❌ Error en scraping: {e}")
            return None

class QobuzDownloader:
    def __init__(self):
        self.base_url = "https://www.qobuz.com/api.json/0.2"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        
        self.token = QOBUZ_TOKEN
        self.app_id = None
        self.app_secret = None
        self.user_id = None
        
        self.quality_map = {
            '5': {'name': 'MP3 320 kbps', 'ext': '.mp3'},
            '6': {'name': 'FLAC 16-bit/44.1kHz', 'ext': '.flac'},
            '7': {'name': 'FLAC 24-bit/96kHz', 'ext': '.flac'},
            '27': {'name': 'FLAC 24-bit/192kHz', 'ext': '.flac'}
        }
        
        self.spotify = SpotifyHandler()
        self.initialize_qobuz_session()
    
    def initialize_qobuz_session(self):
        """Inicializar sesión de Qobuz"""
        try:
            print("🔧 Inicializando sesión de Qobuz...")
            self.app_id = self.get_app_id()
            print(f"📱 App ID: {self.app_id}")
            
            self.app_secret = self.get_app_secret(self.app_id, self.token)
            print(f"🔐 App Secret obtenido: {'✅' if self.app_secret else '❌'}")
            
            user_info = self.get_user_info(self.token)
            if user_info:
                self.user_id = str(user_info.get('id', '0'))
                print(f"👤 Usuario ID: {self.user_id}")
                print(f"📧 Email: {user_info.get('email', 'No disponible')}")
                
                # Verificar suscripción
                subscription = user_info.get('subscription', {})
                if subscription:
                    offer = subscription.get('offer', 'No disponible')
                    status = subscription.get('status', 'No disponible')
                    print(f"🎵 Suscripción: {offer} (Estado: {status})")
                    
                    # Verificar permisos
                    credential = user_info.get('credential', {})
                    if credential:
                        params = credential.get('parameters', {})
                        lossy = params.get('lossy_streaming', False)
                        lossless = params.get('lossless_streaming', False)
                        hires = params.get('hires_streaming', False)
                        
                        print(f"🔊 Permisos de streaming:")
                        print(f"   - MP3: {'✅' if lossy else '❌'}")
                        print(f"   - FLAC: {'✅' if lossless else '❌'}")
                        print(f"   - Hi-Res: {'✅' if hires else '❌'}")
                else:
                    print("⚠️  No se encontró información de suscripción")
                    
            else:
                print("❌ No se pudo obtener información del usuario")
                
            return True
        except Exception as e:
            print(f"❌ Error inicializando sesión: {e}")
            return False
    
    def get_app_id(self):
        """Obtener App ID"""
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
        except:
            return "285473059"
    
    def test_app_id(self, app_id):
        """Probar App ID"""
        try:
            params = {'query': 'test', 'type': 'tracks', 'limit': 1, 'app_id': app_id}
            response = self.session.get(f"{self.base_url}/catalog/search", params=params, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_app_secret(self, app_id, user_auth_token):
        """Obtener App Secret"""
        try:
            url = f"{self.base_url}/app/getSecret"
            params = {'app_id': app_id, 'user_auth_token': user_auth_token}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'app_secret' in data:
                    return data['app_secret']
            return "abb21364945c0583309667d13ca3d93a"
        except:
            return "abb21364945c0583309667d13ca3d93a"
    
    def get_user_info(self, user_auth_token):
        """Obtener información del usuario"""
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
                except:
                    continue
            return None
        except:
            return None
    
    def contains_non_latin_chars(self, text):
        """Verificar si el texto contiene caracteres no latinos"""
        if not text:
            return False
        
        for char in text:
            # Verificar rangos de caracteres no latinos
            code = ord(char)
            # Japonés (Hiragana, Katakana, Kanji)
            if 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FAF:
                return True
            # Chino
            if 0x4E00 <= code <= 0x9FFF:
                return True
            # Coreano
            if 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
                return True
            # Árabe
            if 0x0600 <= code <= 0x06FF:
                return True
            # Cirílico (ruso, etc.)
            if 0x0400 <= code <= 0x04FF:
                return True
        
        return False
    
    def search_tracks_with_locale(self, query, limit=15, force_latin=True):
        """Buscar tracks forzando metadatos en caracteres latinos"""
        try:
            # Parámetros base de búsqueda
            params = {
                'query': query,
                'type': 'track',
                'limit': limit,
                'app_id': self.app_id,
                'user_auth_token': self.token
            }
            
            # Forzar idioma inglés/latino si se solicita
            if force_latin:
                params.update({
                    'locale': 'en_US',  # Forzar inglés americano
                    'country': 'US',    # Forzar país US para metadatos en inglés
                    'language': 'en'    # Idioma inglés
                })
            
            print(f"🌍 Buscando con configuración regional forzada: {params.get('locale', 'default')}")
            
            response = self.session.get(
                'https://www.qobuz.com/api.json/0.2/track/search',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = data.get('tracks', {}).get('items', [])
                
                # Verificar si los metadatos siguen en caracteres no latinos
                non_latin_count = 0
                for track in tracks:
                    title = track.get('title', '')
                    artist = track.get('performer', {}).get('name', '')
                    if self.contains_non_latin_chars(title) or self.contains_non_latin_chars(artist):
                        non_latin_count += 1
                
                if non_latin_count > 0:
                    print(f"⚠️  {non_latin_count}/{len(tracks)} tracks aún tienen caracteres no latinos")
                    print("   Esto indica que Qobuz está devolviendo metadatos localizados")
                else:
                    print(f"✅ Todos los metadatos están en caracteres latinos")
                    
                return tracks
            else:
                print(f"❌ Error en búsqueda: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error en búsqueda con locale: {e}")
            return []

    def search_tracks(self, query, limit=15):
        """Buscar tracks en Qobuz"""
        try:
            # Parámetros de búsqueda
            params = {
                'query': query,
                'type': 'track',
                'limit': limit,
                'app_id': self.app_id,
                'user_auth_token': self.token
            }
            
            print(f"🔍 Buscando tracks en Qobuz...")
            
            response = self.session.get(
                'https://www.qobuz.com/api.json/0.2/track/search',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = data.get('tracks', {}).get('items', [])
                
                print(f"✅ Encontrados {len(tracks)} tracks")
                return tracks
            else:
                print(f"❌ Error en búsqueda: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"❌ Detalles del error: {error_data}")
                except:
                    print(f"❌ Error sin detalles: {response.text[:200]}")
                return []
                
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            return []

    def search_tracks_original(self, query, limit=15):
        """Método de búsqueda original (sin modificación de locale)"""
        try:
            params = {
                'query': query,
                'type': 'track',
                'limit': limit,
                'app_id': self.app_id,
                'user_auth_token': self.token
            }
            
            response = self.session.get(
                'https://www.qobuz.com/api.json/0.2/track/search',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = data.get('tracks', {}).get('items', [])
                
                # Verificar si los metadatos siguen en caracteres no latinos
                non_latin_count = 0
                for track in tracks:
                    title = track.get('title', '')
                    artist = track.get('performer', {}).get('name', '')
                    if self.contains_non_latin_chars(title) or self.contains_non_latin_chars(artist):
                        non_latin_count += 1
                
                if non_latin_count > 0:
                    print(f"⚠️  {non_latin_count}/{len(tracks)} tracks aún tienen caracteres no latinos")
                    print("   Esto indica que Qobuz está devolviendo metadatos localizados")
                else:
                    print(f"✅ Todos los metadatos están en caracteres latinos")
                    
                return tracks
            else:
                print(f"❌ Error en búsqueda: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error en búsqueda con locale: {e}")
            return []

    def fix_qobuz_locale_metadata(self, track_info):
        """Intentar obtener metadatos en inglés para un track específico"""
        try:
            track_id = track_info.get('id')
            if not track_id:
                return track_info
            
            # Intentar obtener información del track con diferentes configuraciones
            locale_attempts = [
                {'locale': 'en_US', 'country': 'US'},
                {'locale': 'en_GB', 'country': 'GB'},
                {'locale': 'en_CA', 'country': 'CA'},
                {}  # Sin forzar locale
            ]
            
            for locale_config in locale_attempts:
                try:
                    params = {
                        'track_id': track_id,
                        'app_id': self.app_id,
                        'user_auth_token': self.token
                    }
                    params.update(locale_config)
                    
                    response = self.session.get(
                        'https://www.qobuz.com/api.json/0.2/track/get',
                        params=params,
                        timeout=8
                    )
                    
                    if response.status_code == 200:
                        track_data = response.json()
                        title = track_data.get('title', '')
                        artist = track_data.get('performer', {}).get('name', '')
                        
                        # Si encontramos metadatos en caracteres latinos, usar esos
                        if not self.contains_non_latin_chars(title) and not self.contains_non_latin_chars(artist):
                            print(f"✅ Metadatos en latino encontrados con locale: {locale_config}")
                            return track_data
                            
                except:
                    continue
            
            print("⚠️  No se pudieron obtener metadatos en caracteres latinos")
            return track_info
            
        except Exception as e:
            print(f"❌ Error corrigiendo locale: {e}")
            return track_info

    def get_track_info(self, track_id):
        """Obtener información completa de un track"""
        try:
            params = {
                'track_id': track_id,
                'app_id': self.app_id,
                'user_auth_token': self.token
            }
            
            response = self.session.get(
                f'{self.base_url}/track/get',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                track_data = response.json()
                
                # Log información relevante para debugging
                title = track_data.get('title', 'Unknown')
                artist = track_data.get('performer', {}).get('name', 'Unknown')
                streamable = track_data.get('streamable', False)
                downloadable = track_data.get('downloadable', False)
                
                print(f"📊 Track: {title} - {artist}")
                print(f"🔊 Streamable: {streamable}")
                print(f"💾 Downloadable: {downloadable}")
                
                # Verificar restricciones
                restrictions = track_data.get('restrictions', [])
                if restrictions:
                    print(f"⚠️  Restricciones: {restrictions}")
                
                return track_data
            else:
                print(f"❌ Error obteniendo track info: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"❌ Detalles del error: {error_data}")
                except:
                    print(f"❌ Error sin detalles: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Error en get_track_info: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_track_url(self, track_id, quality='6'):
        """Obtener URL de descarga de un track con firma de seguridad"""
        try:
            # Primero obtener información del track para verificar disponibilidad
            track_info = self.get_track_info(track_id)
            if not track_info:
                print(f"❌ No se pudo obtener información del track {track_id}")
                return None
            
            # Verificar si el track tiene streaming/descarga disponible
            streamable = track_info.get('streamable', False)
            downloadable = track_info.get('downloadable', False)
            
            print(f"📊 Track info - Streamable: {streamable}, Downloadable: {downloadable}")
            
            if not streamable and not downloadable:
                print(f"❌ Track no disponible para streaming/descarga")
                return None
            
            # Generar timestamp actual (requerido por la API de Qobuz)
            unix_timestamp = int(time.time())
            timestamp_str = str(unix_timestamp)
            print(f"🕐 Timestamp generado: {timestamp_str}")
            
            # Crear string para hash MD5 (exacto del código fuente de Qobuz)
            # Formato: "trackgetFileUrlformat_id{format_id}intentstreamtrack_id{track_id}{timestamp}{app_secret}"
            hash_string = f"trackgetFileUrlformat_id{quality}intentstreamtrack_id{track_id}{timestamp_str}{self.app_secret}"
            
            # Generar MD5 hash (firma de seguridad requerida)
            request_signature = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
            
            print(f"🔐 Hash string: {hash_string[:50]}...{hash_string[-20:]}")
            print(f"🔐 Signature: {request_signature}")
            
            # Parámetros con firma de seguridad
            params = {
                'request_ts': timestamp_str,
                'request_sig': request_signature,
                'track_id': track_id,
                'format_id': quality,
                'intent': 'stream',
                'app_id': self.app_id,
                'user_auth_token': self.token
            }
            
            # URL para obtener enlace de descarga
            url = f"{self.base_url}/track/getFileUrl"
            
            print(f"🔗 Intentando descarga con firma de seguridad...")
            print(f"� URL: {url}")
            print(f"📋 Parámetros: {params}")
            
            response = self.session.get(url, params=params, timeout=10)
            print(f"📊 Respuesta: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Datos recibidos: {list(data.keys())}")
                
                # Buscar URL en la respuesta
                stream_url = data.get('url')
                if stream_url:
                    print(f"🎵 URL de descarga obtenida exitosamente")
                    return stream_url
                else:
                    print(f"⚠️  Respuesta exitosa pero sin URL: {data}")
                    return None
            
            elif response.status_code == 401:
                print(f"❌ Error 401: Token inválido o expirado")
                try:
                    error_data = response.json()
                    print(f"❌ Detalles del error: {error_data}")
                except:
                    print(f"❌ Error sin detalles: {response.text[:200]}")
                return None
            
            elif response.status_code == 403:
                print(f"❌ Error 403: Sin permisos para descargar este track")
                try:
                    error_data = response.json()
                    print(f"❌ Detalles del error: {error_data}")
                except:
                    print(f"❌ Error sin detalles: {response.text[:200]}")
                return None
            
            elif response.status_code == 404:
                print(f"❌ Error 404: Track no encontrado")
                return None
            
            else:
                try:
                    error_data = response.json()
                    print(f"❌ Error {response.status_code}: {error_data}")
                except:
                    print(f"❌ Error {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Error general en get_track_url: {e}")
            import traceback
            traceback.print_exc()
            return None

    def search_track_from_spotify_info(self, spotify_info):
        """Buscar track en Qobuz usando información de Spotify"""
        try:
            print(f"🔍 Buscando en Qobuz: {spotify_info.get('name')} - {spotify_info.get('artist')}")
            
            artist = spotify_info.get('artist', '')
            title = spotify_info.get('name', '')
            
            # Crear diferentes queries de búsqueda
            queries = []
            
            # Query 1: Título y artista con comillas (búsqueda exacta)
            if title and artist:
                queries.append(f'"{title}" "{artist}"')
                queries.append(f'{title} {artist}')
                queries.append(f'{artist} {title}')
            
            # Query 2: Solo título si es muy específico
            if title and len(title) > 10:
                queries.append(f'"{title}"')
            
            # Query 3: Solo artista + palabras clave del título
            if title and artist:
                # Extraer palabras importantes del título (más de 3 caracteres)
                title_words = [word for word in title.split() if len(word) > 3]
                if title_words:
                    queries.append(f'{artist} {" ".join(title_words[:3])}')
            
            for i, query in enumerate(queries, 1):
                try:
                    print(f"   🔍 Intento {i}/{len(queries)}: {query}")
                    
                    tracks = self.search_tracks(query, limit=20)
                    
                    if tracks:
                        # Buscar mejor coincidencia
                        best_match = self.find_best_match(tracks, spotify_info)
                        if best_match:
                            print(f"   ✅ Coincidencia encontrada!")
                            return best_match
                    
                    if i < len(queries):
                        time.sleep(0.5)  # Pausa entre búsquedas
                        
                except Exception as e:
                    print(f"   ❌ Error en intento {i}: {e}")
                    continue
            
            print(f"   ❌ No se encontró coincidencia en Qobuz")
            return None
            
        except Exception as e:
            print(f"❌ Error buscando en Qobuz: {e}")
            return None
    
    def find_best_match(self, qobuz_tracks, spotify_info):
        """Encontrar la mejor coincidencia entre tracks de Qobuz y Spotify"""
        try:
            spotify_title = spotify_info.get('name', '').lower().strip()
            spotify_artist = spotify_info.get('artist', '').lower().strip()
            spotify_duration = spotify_info.get('duration', 0)
            
            # Limpiar strings para comparación
            def clean_string(s):
                # Remover caracteres especiales y normalizar
                import unicodedata
                s = unicodedata.normalize('NFKD', s)
                s = re.sub(r'[^\w\s]', '', s)
                s = re.sub(r'\s+', ' ', s)
                return s.lower().strip()
            
            spotify_title_clean = clean_string(spotify_title)
            spotify_artist_clean = clean_string(spotify_artist)
            
            best_score = 0
            best_track = None
            
            print(f"   🎯 Buscando coincidencia para: '{spotify_title}' - '{spotify_artist}'")
            
            for track in qobuz_tracks:
                try:
                    score = 0
                    
                    qobuz_title = track.get('title', '').lower().strip()
                    qobuz_artist = track.get('performer', {}).get('name', '').lower().strip()
                    qobuz_duration = track.get('duration', 0)
                    
                    qobuz_title_clean = clean_string(qobuz_title)
                    qobuz_artist_clean = clean_string(qobuz_artist)
                    
                    # Puntuación por coincidencia de título (50 puntos máximo)
                    if spotify_title_clean == qobuz_title_clean:
                        score += 50
                    elif spotify_title_clean in qobuz_title_clean or qobuz_title_clean in spotify_title_clean:
                        score += 35
                    elif self.similar_strings(spotify_title_clean, qobuz_title_clean):
                        score += 25
                    
                    # Puntuación por coincidencia de artista (40 puntos máximo)
                    if spotify_artist_clean == qobuz_artist_clean:
                        score += 40
                    elif spotify_artist_clean in qobuz_artist_clean or qobuz_artist_clean in spotify_artist_clean:
                        score += 30
                    elif self.similar_strings(spotify_artist_clean, qobuz_artist_clean):
                        score += 20
                    
                    # Puntuación por duración similar (10 puntos máximo)
                    if spotify_duration > 0 and qobuz_duration > 0:
                        duration_diff = abs(spotify_duration - qobuz_duration)
                        if duration_diff <= 5:  # ±5 segundos
                            score += 10
                        elif duration_diff <= 15:  # ±15 segundos
                            score += 5
                        elif duration_diff <= 30:  # ±30 segundos
                            score += 2
                    
                    # Bonus por disponibilidad
                    if track.get('downloadable', False):
                        score += 5
                    if track.get('streamable', False):
                        score += 2
                    
                    # Debug info para los mejores candidatos
                    if score > 50:
                        print(f"      📊 Candidato (score: {score}): '{qobuz_title}' - '{qobuz_artist}'")
                    
                    if score > best_score:
                        best_score = score
                        best_track = track
                        
                except Exception as e:
                    print(f"      ❌ Error evaluando track: {e}")
                    continue
            
            # Solo devolver si la coincidencia es suficientemente buena
            if best_track and best_score >= 60:  # Umbral de 60%
                print(f"   ✅ Mejor coincidencia (score: {best_score}): {best_track.get('title')} - {best_track.get('performer', {}).get('name')}")
                return best_track
            elif best_track:
                print(f"   ⚠️  Coincidencia débil (score: {best_score}): {best_track.get('title')} - {best_track.get('performer', {}).get('name')}")
                # Devolver de todas formas si el score es > 40
                return best_track if best_score > 40 else None
            else:
                print(f"   ❌ No se encontró coincidencia suficiente")
                return None
                
        except Exception as e:
            print(f"❌ Error en find_best_match: {e}")
            return None
    
    def similar_strings(self, s1, s2, threshold=0.6):
        """Verificar si dos strings son similares usando palabras en común"""
        try:
            if not s1 or not s2:
                return False
                
            words1 = set(s1.split())
            words2 = set(s2.split())
            
            if len(words1) == 0 or len(words2) == 0:
                return False
            
            # Calcular similitud basada en palabras comunes
            common_words = words1.intersection(words2)
            similarity = len(common_words) / max(len(words1), len(words2))
            
            return similarity >= threshold
            
        except:
            return False

    def search_lyrics_genius(self, query, limit=10):
        """Buscar letra de canción usando Genius (método simplificado)"""
        try:
            print(f"🎤 Buscando letras para: {query}")
            
            # Headers para Genius
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Buscar en Genius usando la API pública (sin key)
            search_url = "https://genius.com/api/search/multi"
            params = {
                'q': query
            }
            
            response = self.session.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Buscar resultados de canciones
                songs = []
                sections = data.get('response', {}).get('sections', [])
                
                for section in sections:
                    if section.get('type') == 'song':
                        hits = section.get('hits', [])
                        for hit in hits:
                            result = hit.get('result', {})
                            if result:
                                song_info = {
                                    'title': result.get('title', ''),
                                    'artist': result.get('primary_artist', {}).get('name', ''),
                                    'url': result.get('url', ''),
                                    'genius_id': result.get('id', ''),
                                    'found_by_lyrics': True
                                }
                                songs.append(song_info)
                                
                                if len(songs) >= limit:
                                    break
                    
                    if len(songs) >= limit:
                        break
                
                print(f"✅ Encontradas {len(songs)} canciones por letra")
                return songs
            else:
                print(f"❌ Error buscando en Genius: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error en búsqueda de letras: {e}")
            return []
    
    def search_by_lyrics(self, query, limit=15):
        """Buscar canciones por letra y luego en Qobuz"""
        try:
            print(f"🎤 Búsqueda por letra: {query}")
            
            # Buscar en Genius
            genius_songs = self.search_lyrics_genius(query, limit=min(limit, 10))
            
            if not genius_songs:
                print("❌ No se encontraron canciones por letra")
                return []
            
            # Buscar cada canción encontrada en Qobuz
            qobuz_matches = []
            
            for song in genius_songs:
                try:
                    # Crear query para Qobuz
                    artist = song.get('artist', '')
                    title = song.get('title', '')
                    
                    if not artist or not title:
                        continue
                    
                    print(f"   🔍 Buscando en Qobuz: {title} - {artist}")
                    
                    # Buscar en Qobuz
                    spotify_info = {
                        'name': title,
                        'artist': artist,
                        'album': '',
                        'duration': 0
                    }
                    
                    qobuz_track = self.search_track_from_spotify_info(spotify_info)
                    
                    if qobuz_track:
                        # Agregar información de que fue encontrado por letra
                        qobuz_track['found_by_lyrics'] = True
                        qobuz_track['genius_match'] = True
                        qobuz_track['genius_url'] = song.get('url', '')
                        qobuz_track['matched_fragment'] = query
                        
                        qobuz_matches.append(qobuz_track)
                        
                        print(f"   ✅ Encontrado en Qobuz: {qobuz_track.get('title')}")
                    else:
                        print(f"   ❌ No encontrado en Qobuz")
                    
                    # Límite de matches
                    if len(qobuz_matches) >= limit:
                        break
                        
                    time.sleep(0.3)  # Pausa entre búsquedas
                    
                except Exception as e:
                    print(f"   ❌ Error procesando {song}: {e}")
                    continue
            
            print(f"✅ Encontrados {len(qobuz_matches)} tracks por letra en Qobuz")
            return qobuz_matches
            
        except Exception as e:
            print(f"❌ Error en búsqueda por letra: {e}")
            return []

# Inicializar downloader global
print("Inicializando downloader...")
downloader = QobuzDownloader()
print(f"Downloader inicializado. App ID: {downloader.app_id}")

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/token-info')
def token_info():
    """API para obtener información del token"""
    try:
        info = get_token_info()
        return jsonify({
            'success': True,
            'token_info': info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search', methods=['POST'])
def search():
    """API para buscar canciones"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        source = data.get('source', 'qobuz')  # 'qobuz' o 'spotify'
        
        print(f"Búsqueda recibida - Query: {query}, Source: {source}")
        
        if not query:
            return jsonify({'success': False, 'error': 'Query vacío'}), 400
        
        if source == 'qobuz':
            # Búsqueda mejorada en Qobuz que incluye corrección de metadatos japoneses
            print("Buscando en Qobuz...")
            tracks = downloader.search_tracks(query, limit=15)
            print(f"Encontrados {len(tracks)} tracks")
            results = []
            
            for track in tracks:
                result_data = {
                    'id': track.get('id'),
                    'title': track.get('title'),
                    'artist': track.get('performer', {}).get('name', 'Unknown'),
                    'album': track.get('album', {}).get('title', 'Unknown'),
                    'duration': track.get('duration', 0),
                    'downloadable': track.get('downloadable', False),
                    'cover': track.get('album', {}).get('image', {}).get('small', ''),
                    'source': 'qobuz'
                }
                
                # Agregar propiedades de búsqueda por letra si existen
                if track.get('found_by_lyrics'):
                    result_data['found_by_lyrics'] = True
                if track.get('genius_match'):
                    result_data['genius_match'] = True
                if track.get('matched_fragment'):
                    result_data['matched_fragment'] = track.get('matched_fragment')
                if track.get('genius_url'):
                    result_data['genius_url'] = track.get('genius_url')
                
                results.append(result_data)
            
        elif source == 'spotify':
            # Si es URL de Spotify
            if 'spotify.com' in query or query.startswith('spotify:'):
                url_type, spotify_id = downloader.spotify.extract_spotify_id(query)
                
                if url_type == 'track' and spotify_id:
                    # Buscar track individual
                    spotify_info = downloader.spotify.get_track_info_by_scraping(spotify_id)
                    if spotify_info:
                        print(f"Información de Spotify obtenida: {spotify_info}")
                        # Aquí buscaríamos en Qobuz basado en la info de Spotify
                        # qobuz_track = downloader.search_track_from_spotify_info(spotify_info)
                        # Por ahora simplificado
                        results = []
                    else:
                        print("No se pudo obtener información de Spotify")
                        results = []
                else:
                    results = []
            else:
                # Búsqueda de texto en Spotify (simplificado - buscar en Qobuz)
                print(f"Búsqueda de texto en Spotify, redirigiendo a Qobuz...")
                tracks = downloader.search_tracks(query, limit=15)
                results = []
                
                for track in tracks:
                    results.append({
                        'id': track.get('id'),
                        'title': track.get('title'),
                        'artist': track.get('performer', {}).get('name', 'Unknown'),
                        'album': track.get('album', {}).get('title', 'Unknown'),
                        'duration': track.get('duration', 0),
                        'downloadable': track.get('downloadable', False),
                        'cover': track.get('album', {}).get('image', {}).get('small', ''),
                        'source': 'qobuz'
                    })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        print(f"Error en búsqueda: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download():
    """API para descargar canciones"""
    try:
        data = request.get_json()
        track_id = data.get('track_id')
        quality = data.get('quality', '6')
        
        print(f"🎵 Solicitud de descarga - Track ID: {track_id}, Quality: {quality}")
        
        if not track_id:
            return jsonify({'error': 'Track ID requerido'}), 400
        
        # Verificar que el track existe primero
        track_info = downloader.get_track_info(track_id)
        if not track_info:
            print(f"❌ No se pudo obtener información del track {track_id}")
            return jsonify({'error': 'Track no encontrado'}), 404
        
        print(f"✅ Track encontrado: {track_info.get('title')} - {track_info.get('performer', {}).get('name')}")
        
        # Verificar si el track es descargable
        if not track_info.get('downloadable', False):
            print(f"⚠️  Track no descargable: {track_id}")
            return jsonify({'error': 'Este track no está disponible para descarga'}), 403
        
        # Obtener URL de descarga
        print(f"🔗 Obteniendo URL de descarga...")
        download_url = downloader.get_track_url(track_id, quality)
        
        if download_url:
            print(f"✅ URL de descarga obtenida exitosamente")
            return jsonify({
                'download_url': download_url,
                'quality': downloader.quality_map[quality]['name'],
                'track_info': {
                    'title': track_info.get('title'),
                    'artist': track_info.get('performer', {}).get('name'),
                    'album': track_info.get('album', {}).get('title'
                    )
                }
            })
        else:
            print(f"❌ No se pudo obtener URL de descarga para track {track_id}")
            return jsonify({'error': 'No se pudo obtener enlace de descarga. Posible problema de suscripción o permisos.'}), 400
            
    except Exception as e:
        print(f"❌ Error en descarga: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy-download')
def proxy_download():
    """Proxy para descargar archivos (evitar CORS) con metadatos"""
    try:
        url = request.args.get('url')
        filename = request.args.get('filename', 'track')
        track_id = request.args.get('track_id')
        
        if not url:
            return jsonify({'error': 'URL requerida'}), 400
        
        print(f"Descargando: {filename}")
        
        # Descargar archivo
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
        
        # Escribir contenido del archivo
        total_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
                total_size += len(chunk)
        
        temp_file.close()
        print(f"Archivo descargado: {total_size} bytes")
        
        # Agregar metadatos si tenemos track_id
        if track_id:
            try:
                # Obtener información del track desde Qobuz
                track_info = downloader.get_track_info(track_id)
                if track_info:
                    print(f"Track info obtenida: {json.dumps(track_info, indent=2)}")
                    
                    # Obtener URL de cover en alta resolución
                    cover_url = None
                    album_info = track_info.get('album', {})
                    if isinstance(album_info, dict) and 'image' in album_info:
                        images = album_info['image']
                        if isinstance(images, dict):
                            cover_url = images.get('large') or images.get('small')
                    
                    # Preparar información de metadatos
                    performer = track_info.get('performer', {})
                    artist_name = performer.get('name', '') if isinstance(performer, dict) else ''
                    album_title = album_info.get('title', '') if isinstance(album_info, dict) else ''
                    released_at = album_info.get('released_at', '') if isinstance(album_info, dict) else ''
                    
                    # Manejar released_at que puede ser int (timestamp) o string
                    year = ''
                    if released_at:
                        if isinstance(released_at, int):
                            # Si es timestamp, convertir a fecha
                            try:
                                from datetime import datetime
                                year = str(datetime.fromtimestamp(released_at).year)
                                print(f"Converted timestamp {released_at} to year {year}")
                            except Exception as e:
                                print(f"Error converting timestamp: {e}")
                                year = ''
                        elif isinstance(released_at, str) and len(released_at) >= 4:
                            year = released_at[:4]
                            print(f"Extracted year from string: {year}")
                        else:
                            print(f"Unable to extract year from: {released_at} (type: {type(released_at)})")
                    
                    metadata = {
                        'title': track_info.get('title', ''),
                        'artist': artist_name,
                        'album': album_title,
                        'year': year,
                        'track_number': str(track_info.get('track_number', '')) if track_info.get('track_number') else ''
                    }
                    
                    print(f"Metadatos preparados: {metadata}")
                    print(f"Cover URL: {cover_url}")
                    
                    # Agregar metadatos
                    success = add_metadata_to_file(temp_file.name, metadata, cover_url)
                    if success:
                        print("Metadatos agregados al archivo exitosamente")
                    else:
                        print("Falló al agregar metadatos")
                else:
                    print("No se pudo obtener información del track")
            except Exception as e:
                print(f"Error agregando metadatos: {e}")
                import traceback
                traceback.print_exc()
                # Continuar sin metadatos si hay error
        
        # Enviar archivo
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        print(f"Error en proxy_download: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview', methods=['POST'])
def get_preview():
    """API para obtener URL de preview de 30 segundos"""
    try:
        data = request.get_json()
        track_id = data.get('track_id')
        
        if not track_id:
            return jsonify({'error': 'Track ID requerido'}), 400
        
        print(f"🎵 Solicitando preview para track ID: {track_id}")
        
        # Obtener información del track
        track_info = downloader.get_track_info(track_id)
        if not track_info:
            return jsonify({'error': 'Track no encontrado'}), 404
        
        print(f"📊 Track info obtenida: {track_info.get('title')} - {track_info.get('performer', {}).get('name')}")
        
        # Buscar URL de preview en la información del track
        preview_url = None
        
        # 1. Buscar preview directo en el track info
        preview_fields = ['preview_url', 'preview', 'sample_url', 'stream_url']
        for field in preview_fields:
            if field in track_info and track_info[field]:
                preview_url = track_info[field]
                print(f"✅ Preview encontrado en campo '{field}': {preview_url[:50]}...")
                break
        
        # 2. Si no hay preview directo, intentar múltiples métodos
        if not preview_url:
            print("🔍 No hay preview directo, intentando métodos alternativos...")
            
            # Método 1: Intentar obtener sample con la API oficial
            try:
                print("🔍 Método 1: Sample API con signature...")
                unix_timestamp = int(time.time())
                timestamp_str = str(unix_timestamp)
                
                # Crear hash para sample (método usado por Qobuz)
                hash_string = f"trackgetFileUrlformat_id5intentstreamtrack_id{track_id}{timestamp_str}{downloader.app_secret}"
                request_signature = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
                
                params = {
                    'request_ts': timestamp_str,
                    'request_sig': request_signature,
                    'track_id': track_id,
                    'format_id': '5',  # MP3 para preview
                    'intent': 'stream',
                    'sample': 'true',  # Obtener sample de 30 segundos
                    'app_id': downloader.app_id,
                    'user_auth_token': downloader.token
                }
                
                response = downloader.session.get(
                    f"{downloader.base_url}/track/getFileUrl",
                    params=params,
                    timeout=10
                )
                
                print(f"📊 Respuesta API sample: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    preview_url = data.get('url')
                    if preview_url:
                        print(f"✅ Sample URL obtenida por método 1: {preview_url[:50]}...")
                    else:
                        print(f"⚠️ Respuesta exitosa pero sin URL: {data}")
                else:
                    print(f"❌ Error en sample API: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"❌ Detalles: {error_data}")
                    except:
                        print(f"❌ Error sin detalles: {response.text[:200]}")
                
            except Exception as e:
                print(f"❌ Error en método 1: {e}")
            
            # Método 2: Intentar con parámetros simplificados
            if not preview_url:
                try:
                    print("🔍 Método 2: Parámetros simplificados...")
                    params = {
                        'track_id': track_id,
                        'format_id': '5',
                        'app_id': downloader.app_id,
                        'user_auth_token': downloader.token,
                        'sample': 'true'
                    }
                    
                    response = downloader.session.get(
                        f"{downloader.base_url}/track/getFileUrl",
                        params=params,
                        timeout=10
                    )
                    
                    print(f"📊 Respuesta método 2: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        preview_url = data.get('url')
                        if preview_url:
                            print(f"✅ Sample URL obtenida por método 2: {preview_url[:50]}...")
                
                except Exception as e:
                    print(f"❌ Error en método 2: {e}")
            
            # Método 3: Usar el URL de streaming normal pero limitado a 30 segundos en el frontend
            if not preview_url:
                try:
                    print("🔍 Método 3: URL de streaming normal...")
                    stream_url = downloader.get_track_url(track_id, '5')  # MP3 de menor calidad
                    if stream_url:
                        print(f"✅ Using stream URL as preview: {stream_url[:50]}...")
                        preview_url = stream_url
                        
                except Exception as e:
                    print(f"❌ Error en método 3: {e}")
        
        # Preparar respuesta
        if preview_url:
            track_response = {
                'success': True,
                'preview_url': preview_url,
                'track_info': {
                    'title': track_info.get('title', 'Unknown'),
                    'artist': track_info.get('performer', {}).get('name', 'Unknown'),
                    'album': track_info.get('album', {}).get('title', 'Unknown'),
                    'cover': track_info.get('album', {}).get('image', {}).get('small', '')
                }
            }
            print(f"✅ Preview exitoso para: {track_response['track_info']['title']}")
            return jsonify(track_response)
        else:
            print(f"❌ No se pudo obtener preview para track {track_id}")
            return jsonify({
                'success': False,
                'error': 'Preview no disponible para este track. Esto puede deberse a restricciones del proveedor.',
                'track_info': {
                    'title': track_info.get('title', 'Unknown'),
                    'artist': track_info.get('performer', {}).get('name', 'Unknown'),
                    'album': track_info.get('album', {}).get('title', 'Unknown')
                }
            }), 404
            
    except Exception as e:
        print(f"❌ Error general en preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🎵 Iniciando Music Downloader...")
    
    # Configuración para desarrollo local y Azure App Service
    # Para Azure Functions, este bloque no se ejecutará
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Solo ejecutar si no estamos en Azure Functions
    if not os.environ.get('FUNCTIONS_WORKER_RUNTIME'):
        app.run(debug=debug_mode, host='0.0.0.0', port=port)
