"""Servicio para manejo de scraping básico de Spotify"""
from __future__ import annotations
import re
import json
import requests
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

@dataclass
class SpotifyTrackInfo:
    name: str
    artist: str
    album: str = ''
    duration: int = 0

class SpotifyHandler:
    def extract_spotify_id(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            if '?' in url:
                url = url.split('?')[0]
            patterns = {
                'track': [r'spotify\.com/(?:intl-[a-z-]+/)?track/([a-zA-Z0-9]+)', r'open\.spotify\.com/(?:intl-[a-z-]+/)?track/([a-zA-Z0-9]+)'],
                'playlist': [r'spotify\.com/(?:intl-[a-z-]+/)?playlist/([a-zA-Z0-9]+)', r'open\.spotify\.com/(?:intl-[a-z-]+/)?playlist/([a-zA-Z0-9]+)']
            }
            for type_name, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, url)
                    if match:
                        return type_name, match.group(1)
            if url.startswith('spotify:'):
                parts = url.split(':')
                if len(parts) >= 3:
                    return parts[1], parts[2]
            return None, None
        except Exception:
            return None, None

    def get_track_info_by_scraping(self, track_id: str) -> Optional[Dict[str, Any]]:
        # Intento 1: __NEXT_DATA__ JSON del embed (MÁS CONFIABLE)
        try:
            embed_url = f"https://open.spotify.com/embed/track/{track_id}"
            embed_response = requests.get(embed_url, headers=HEADERS, timeout=15)
            if embed_response.status_code == 200:
                embed_html = embed_response.text
                next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', embed_html)
                if next_data_match:
                    next_data = json.loads(next_data_match.group(1))
                    entity = next_data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
                    if entity.get('type') == 'track':
                        title = entity.get('name', '')
                        artists_list = entity.get('artists', [])
                        if artists_list and isinstance(artists_list, list):
                            artist = artists_list[0].get('name', '')
                            all_artists = [a.get('name', '') for a in artists_list if a.get('name')]
                            duration_ms = entity.get('duration', 0)
                            if title and artist:
                                print(f"[SPOTIFY] ✅ Found via embed: '{title}' by '{artist}'")
                                return {
                                    'name': title, 
                                    'artist': artist, 
                                    'album': '', 
                                    'duration': int(duration_ms/1000) if duration_ms else 0, 
                                    'artists': all_artists
                                }
        except Exception as e:
            print(f"[SPOTIFY] ❌ Embed parsing failed: {e}")
            pass

        # Fallback: Métodos anteriores
        urls = [
            f"https://open.spotify.com/track/{track_id}",
            f"https://open.spotify.com/intl-es/track/{track_id}",
            f"https://spotify.com/track/{track_id}"
        ]
        for url in urls:
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                html = response.text
                # Intento 2: Bloque JavaScript con Spotify.Entity que contiene JSON completo
                try:
                    entity_match = re.search(r'Spotify\\.Entity\\s*=\\s*({.*?});', html, re.DOTALL)
                    if entity_match:
                        raw_json = entity_match.group(1)
                        entity = json.loads(raw_json)
                        if entity.get('type') == 'track':
                            title = entity.get('name', '')
                            artists_list = entity.get('artists', []) or []
                            artist = ''
                            if artists_list and isinstance(artists_list, list):
                                artist = artists_list[0].get('name', '')
                            album = entity.get('album', {}).get('name', '') if isinstance(entity.get('album'), dict) else ''
                            duration_ms = entity.get('duration_ms', 0)
                            if title and artist:
                                return {'name': title, 'artist': artist, 'album': album, 'duration': int(duration_ms/1000) if duration_ms else 0, 'artists': [a.get('name','') for a in artists_list if isinstance(a, dict)]}
                except Exception:
                    pass
                json_ld_matches = re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
                for match in json_ld_matches:
                    try:
                        json_data = json.loads(match.group(1).strip())
                        if isinstance(json_data, list):
                            json_data = next((i for i in json_data if i.get('@type') == 'MusicRecording'), json_data[0])
                        if json_data.get('@type') == 'MusicRecording':
                            title = json_data.get('name', '')
                            artist = ''
                            album = ''
                            by_artist = json_data.get('byArtist', {})
                            if isinstance(by_artist, list) and by_artist:
                                artist = by_artist[0].get('name', '')
                            elif isinstance(by_artist, dict):
                                artist = by_artist.get('name', '')
                            in_album = json_data.get('inAlbum', {})
                            if isinstance(in_album, dict):
                                album = in_album.get('name', '')
                            if title and artist:
                                return {'name': title, 'artist': artist, 'album': album, 'duration': 0, 'artists': [artist]}
                    except json.JSONDecodeError:
                        continue
                og_title = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
                og_description = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"', html)
                if og_title:
                    title = og_title.group(1).strip()
                    artist = 'Unknown'
                    album = 'Unknown'
                    if og_description:
                        desc = og_description.group(1).strip()
                        if ' · ' in desc:
                            parts = desc.split(' · ')
                            if len(parts) >= 2:
                                artist = parts[1].strip()
                                if len(parts) >= 3:
                                    album = parts[2].strip()
                        elif ' - ' in desc:
                            parts = desc.split(' - ', 1)
                            if len(parts) == 2:
                                artist = parts[0].strip(); title = parts[1].strip()
                        elif ' by ' in desc:
                            m = re.search(r'(.+?) by (.+)', desc)
                            if m:
                                title = m.group(1).strip(); artist = m.group(2).strip()
                    if artist == 'Unknown' and ' - ' in title:
                        parts = title.split(' - ', 1)
                        if len(parts) == 2:
                            artist = parts[0].strip(); title = parts[1].strip()
                    if title and artist != 'Unknown':
                        return {'name': title, 'artist': artist, 'album': album, 'duration': 0, 'artists': [artist]}
                # Intento 3: __NEXT_DATA__ JSON del embed (más confiable)
                try:
                    embed_url = f"https://open.spotify.com/embed/track/{track_id}"
                    embed_response = requests.get(embed_url, headers=HEADERS, timeout=15)
                    if embed_response.status_code == 200:
                        embed_html = embed_response.text
                        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', embed_html)
                        if next_data_match:
                            next_data = json.loads(next_data_match.group(1))
                            entity = next_data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
                            if entity.get('type') == 'track':
                                title = entity.get('name', '')
                                artists_list = entity.get('artists', [])
                                if artists_list and isinstance(artists_list, list):
                                    artist = artists_list[0].get('name', '')
                                    all_artists = [a.get('name', '') for a in artists_list if a.get('name')]
                                    duration_ms = entity.get('duration', 0)
                                    if title and artist:
                                        print(f"[SPOTIFY] ✅ Found via embed: '{title}' by '{artist}'")
                                        return {
                                            'name': title, 
                                            'artist': artist, 
                                            'album': '', 
                                            'duration': int(duration_ms/1000) if duration_ms else 0, 
                                            'artists': all_artists
                                        }
                except Exception as e:
                    print(f"[SPOTIFY] ❌ Embed parsing failed: {e}")
                    pass
                
                # Intento 4: oEmbed de Spotify (estable y ligero)
                try:
                    oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
                    oresp = requests.get(oembed_url, headers=HEADERS, timeout=10)
                    if oresp.status_code == 200:
                        meta = oresp.json()
                        # title suele venir como "Artist - Track" o "Track"
                        t = meta.get('title', '').strip()
                        o_title, o_artist = '', ''
                        if ' - ' in t:
                            parts = t.split(' - ', 1)
                            if len(parts) == 2:
                                o_artist, o_title = parts[0].strip(), parts[1].strip()
                        else:
                            o_title = t
                        # author_name a veces contiene el artista
                        if not o_artist:
                            o_artist = (meta.get('author_name') or '').strip()
                        if o_title and o_artist:
                            return {'name': o_title, 'artist': o_artist, 'album': '', 'duration': 0, 'artists': [o_artist]}
                except Exception:
                    pass
            except Exception:
                continue
        return None

__all__ = ["SpotifyHandler", "SpotifyTrackInfo"]
