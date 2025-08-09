"""Blueprint de rutas de la API.

Endpoints principales extraídos del monolito original. Se busca mantener compatibilidad
con la semántica previa mientras se simplifica la implementación. Falta todavía portar
funcionalidades avanzadas (lyrics, locale forcing, matching extendido)."""
from __future__ import annotations
from flask import Blueprint, request, jsonify, send_file
import os, tempfile, time, hashlib, logging
import requests
from ..app_factory import get_downloader
from ..utils.metadata import add_metadata_to_file
from ..utils.token import get_token_info

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

downloader = get_downloader()

@api_bp.route('/test')
def api_test():
    """Endpoint de test conservado para script de pruebas locales."""
    return jsonify({"status": "ok"})

@api_bp.route('/token-info')
def token_info():
    try:
        info = get_token_info()
        return jsonify({'success': True, 'token_info': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json() or {}
        query = data.get('query', '')
        source = data.get('source', 'qobuz')
        mode = data.get('mode')  # permite 'lyrics'
        logger.info("/search IN -> q='%s' src=%s mode=%s", query, source, mode)
        if not query:
            return jsonify({'success': False, 'error': 'Query vacío'}), 400
        
        results: list[dict] = []
        lyrics_results: list[dict] = []
        
        if source == 'qobuz':
            # Primero buscar por letra si hay modo lyrics
            if mode == 'lyrics':
                lyrics_results = downloader.search_by_lyrics(query, limit=1)
                logger.info("/search LYRICS mode: frase='%s' -> lyrics_results=%d", query, len(lyrics_results))
                for t in lyrics_results:
                    item = {
                        'id': t.get('id'),
                        'title': t.get('title'),
                        'artist': t.get('performer', {}).get('name', 'Unknown'),
                        'album': t.get('album', {}).get('title', 'Unknown'),
                        'duration': t.get('duration', 0),
                        'cover': t.get('album', {}).get('image', {}).get('small', ''),
                        'source': t.get('source') or 'qobuz'
                    }
                    for extra in ['found_by_lyrics','genius_match','genius_url','matched_fragment','lyrics_fragment']:
                        if t.get(extra):
                            item[extra] = t.get(extra)
                    results.append(item)
                if lyrics_results:
                    logger.info("/search LYRICS first item: title='%s' source=%s genius=%s", results[0]['title'], results[0].get('source'), results[0].get('genius_match'))
            
            # Luego búsqueda normal
            tracks = downloader.search_tracks_with_locale(query, limit=15, force_latin=True)
            for t in tracks:
                # Evitar duplicados con resultados por letra
                if any(existing.get('id') == t.get('id') for existing in results):
                    continue
                item = {
                    'id': t.get('id'),
                    'title': t.get('title'),
                    'artist': t.get('performer', {}).get('name', 'Unknown'),
                    'album': t.get('album', {}).get('title', 'Unknown'),
                    'duration': t.get('duration', 0),
                    'cover': t.get('album', {}).get('image', {}).get('small', ''),
                    'source': 'qobuz'
                }
                results.append(item)

        elif source == 'spotify':
            if 'spotify.com' in query or query.startswith('spotify:'):
                t_type, s_id = downloader.spotify.extract_spotify_id(query)
                if t_type == 'track' and s_id:
                    sp_info = downloader.spotify.get_track_info_by_scraping(s_id)
                    if sp_info:
                        mapped = downloader.search_track_from_spotify_info(sp_info)
                        if mapped:
                            results.append({
                                'id': mapped.get('id'),
                                'title': mapped.get('title'),
                                'artist': mapped.get('performer', {}).get('name','Unknown'),
                                'album': mapped.get('album', {}).get('title','Unknown'),
                                'duration': mapped.get('duration',0),
                                'cover': mapped.get('album', {}).get('image', {}).get('small',''),
                                'source': 'qobuz',
                                'mapped_from_spotify': True
                            })
                        else:
                            # Fallback: buscar directamente usando título + artista si se obtuvo info
                            artist = sp_info.get('artist','')
                            title = sp_info.get('name','')
                            simple_query = f"{title} {artist}".strip()
                            if simple_query:
                                for t in downloader.search_tracks_with_locale(simple_query, limit=10, force_latin=True):
                                    results.append({
                                        'id': t.get('id'),
                                        'title': t.get('title'),
                                        'artist': t.get('performer', {}).get('name','Unknown'),
                                        'album': t.get('album', {}).get('title','Unknown'),
                                        'duration': t.get('duration',0),
                                        'cover': t.get('album', {}).get('image', {}).get('small',''),
                                        'source': 'qobuz',
                                        'spotify_fallback': True
                                    })
            else:
                tracks = downloader.search_tracks_with_locale(query, limit=15, force_latin=True)
                for track in tracks:
                    results.append({
                        'id': track.get('id'),
                        'title': track.get('title'),
                        'artist': track.get('performer', {}).get('name', 'Unknown'),
                        'album': track.get('album', {}).get('title', 'Unknown'),
                        'duration': track.get('duration', 0),
                        'cover': track.get('album', {}).get('image', {}).get('small', ''),
                        'source': 'qobuz'
                    })
        # Poner resultados por letra primero por claridad en UI
        if results:
            lyrics_first = [r for r in results if r.get('found_by_lyrics')] + [r for r in results if not r.get('found_by_lyrics')]
            results = lyrics_first

        # Log básico de conteos para depuración
        try:
            logger.info(
                "/search q='%s' mode=%s src=%s -> lyrics=%d, normal=%d, total=%d",
                query,
                mode,
                source,
                len(lyrics_results),
                len([r for r in results if not r.get('found_by_lyrics')]),
                len(results),
            )
            if results:
                logger.info("/search OUT first item: title='%s' found_by_lyrics=%s source=%s", results[0].get('title'), results[0].get('found_by_lyrics'), results[0].get('source'))
        except Exception:
            pass

        return jsonify({'success': True, 'results': results, 'total': len(results)})
    except Exception as e:
        logger.exception("Error en /search")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json() or {}
        track_id = data.get('track_id')
        quality = data.get('quality', '6')
        if not track_id:
            return jsonify({'success': False, 'error': 'Track ID requerido'}), 400
        track_info = downloader.get_track_info(track_id)
        if not track_info:
            return jsonify({'success': False, 'error': 'Track no encontrado'}), 404
        download_url = downloader.get_track_url(track_id, quality)
        if download_url:
            return jsonify({'success': True,'download_url': download_url,'quality': downloader.quality_map.get(quality, {}).get('name',''),'track_info': {'title': track_info.get('title'),'artist': track_info.get('performer', {}).get('name'),'album': track_info.get('album', {}).get('title')}})
        return jsonify({'success': False,'error': 'No se pudo obtener enlace de descarga'}), 400
    except Exception as e:
        logger.exception("Error en /download")
        return jsonify({'success': False,'error': str(e)}), 500

@api_bp.route('/proxy-download')
def proxy_download():
    try:
        url = request.args.get('url')
        filename = request.args.get('filename', 'track')
        track_id = request.args.get('track_id')
        if not url:
            return jsonify({'success': False,'error': 'URL requerida'}), 400
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        temp_file.close()
        if track_id:
            try:
                t_info = downloader.get_track_info(track_id)
                if t_info:
                    album_info = t_info.get('album', {})
                    images = album_info.get('image', {}) if isinstance(album_info, dict) else {}
                    cover_url = images.get('large') or images.get('small')
                    performer = t_info.get('performer', {})
                    artist_name = performer.get('name', '') if isinstance(performer, dict) else ''
                    released_at = album_info.get('released_at', '') if isinstance(album_info, dict) else ''
                    year = ''
                    if isinstance(released_at, int):
                        try:
                            from datetime import datetime
                            year = str(datetime.fromtimestamp(released_at).year)
                        except Exception:
                            pass
                    elif isinstance(released_at, str) and len(released_at) >= 4:
                        year = released_at[:4]
                    metadata = {'title': t_info.get('title', ''), 'artist': artist_name, 'album': album_info.get('title', '') if isinstance(album_info, dict) else '', 'year': year, 'track_number': str(t_info.get('track_number', '')) if t_info.get('track_number') else ''}
                    add_metadata_to_file(temp_file.name, metadata, cover_url)
            except Exception:
                pass
        return send_file(temp_file.name, as_attachment=True, download_name=filename, mimetype='application/octet-stream')
    except Exception as e:
        logger.exception("Error en /proxy-download")
        return jsonify({'success': False,'error': str(e)}), 500

@api_bp.route('/preview', methods=['POST'])
def get_preview():
    try:
        data = request.get_json() or {}
        track_id = data.get('track_id')
        if not track_id:
            return jsonify({'success': False,'error': 'Track ID requerido'}), 400
        track_info = downloader.get_track_info(track_id)
        if not track_info:
            return jsonify({'success': False,'error': 'Track no encontrado'}), 404
        preview_url = None
        # Intento directo
        for field in ['preview_url', 'preview', 'sample_url', 'stream_url']:
            if field in track_info and track_info[field]:
                preview_url = track_info[field]; break
        if not preview_url:
            ts = str(int(time.time()))
            try:
                hash_string = f"trackgetFileUrlformat_id5intentstreamtrack_id{track_id}{ts}{downloader.app_secret}"
                sig = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
                params = {'request_ts': ts,'request_sig': sig,'track_id': track_id,'format_id': '5','intent': 'stream','sample': 'true','app_id': downloader.app_id,'user_auth_token': downloader.token}
                r = downloader.session.get(f"{downloader.base_url}/track/getFileUrl", params=params, timeout=10)
                if r.status_code == 200:
                    preview_url = r.json().get('url')
            except Exception:
                pass
        if not preview_url:
            stream_url = downloader.get_track_url(track_id, '5')
            if stream_url:
                preview_url = stream_url
        if preview_url:
            return jsonify({'success': True,'preview_url': preview_url,'track_info': {'title': track_info.get('title', 'Unknown'),'artist': track_info.get('performer', {}).get('name', 'Unknown'),'album': track_info.get('album', {}).get('title', 'Unknown'),'cover': track_info.get('album', {}).get('image', {}).get('small', '')}})
        return jsonify({'success': False,'error': 'Preview no disponible'}), 404
    except Exception as e:
        logger.exception("Error en /preview")
        return jsonify({'success': False, 'error': str(e)}), 500
