"""Blueprint de rutas de la API.

Endpoints principales extraídos del monolito original. Se busca mantener compatibilidad
con la semántica previa mientras se simplifica la implementación. Falta todavía portar
funcionalidades avanzadas (lyrics, locale forcing, matching extendido)."""
from __future__ import annotations
from flask import Blueprint, request, jsonify, send_file
import os, tempfile, time, hashlib, logging
from datetime import datetime
import requests
from ..app_factory import get_downloader
from ..config import FLASK_DEBUG
from ..utils.metadata import add_metadata_to_file
from ..utils.token import get_token_info, format_token_info_display
from ..services.auto_renewal import check_and_renew_if_needed, QobuzCredentialRenewer

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

downloader = get_downloader()

@api_bp.route('/test')
def api_test():
    """Endpoint de test conservado para script de pruebas locales."""
    return jsonify({"status": "ok"})

@api_bp.route('/debug/env')
def debug_env():
    """Endpoint para verificar variables de entorno en producción"""
    import os
    from ..config import GENIUS_TOKEN, QOBUZ_TOKEN
    
    return jsonify({
        "genius_token_configured": bool(GENIUS_TOKEN and GENIUS_TOKEN != "tu_token_de_genius_aqui"),
        "genius_token_preview": GENIUS_TOKEN[:20] + "..." if GENIUS_TOKEN else "NO_SET",
        "qobuz_token_configured": bool(QOBUZ_TOKEN),
        "qobuz_token_preview": QOBUZ_TOKEN[:20] + "..." if QOBUZ_TOKEN else "NO_SET",
        "env_genius": bool(os.environ.get('GENIUS_TOKEN')),
        "env_qobuz": bool(os.environ.get('QOBUZ_TOKEN')),
        "flask_env": os.environ.get('FLASK_ENV', 'not_set')
    })

@api_bp.route('/debug/lyrics-test')
def debug_lyrics_test():
    """Endpoint para probar la funcionalidad de búsqueda por letras"""
    import traceback
    import datetime
    import io
    import sys
    
    debug_info = []
    
    timestamp = datetime.datetime.now().isoformat()
    debug_info.append(f"[DEBUG] Timestamp del deployment: {timestamp}")
    
    try:
        test_phrase = "y si te digo que es para toda la vida pero no como esos"
        debug_info.append(f"[DEBUG] Iniciando test de búsqueda por letras con: '{test_phrase}'")
        
        # Verificar configuración antes de la búsqueda
        from ..config import GENIUS_TOKEN
        debug_info.append(f"[DEBUG] Token disponible: {bool(GENIUS_TOKEN)}")
        debug_info.append(f"[DEBUG] Token preview: {GENIUS_TOKEN[:20]}..." if GENIUS_TOKEN else "[DEBUG] No token")
        
        debug_info.append("[DEBUG] ⚠️ VERSIÓN CON LOGGING DETALLADO ACTIVADA")
        
        # Capturar todos los prints durante la búsqueda
        old_stdout = sys.stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            # Intentar la búsqueda
            debug_info.append("[DEBUG] 🚀 Iniciando búsqueda con captura de logs...")
            results = downloader.search_by_lyrics(test_phrase, limit=1)
            debug_info.append(f"[DEBUG] Búsqueda completada, resultados: {len(results)}")
            
            # Restaurar stdout y capturar lo que se imprimió
            sys.stdout = old_stdout
            captured_logs = captured_output.getvalue()
            
            if captured_logs:
                debug_info.append("[DEBUG] 📝 Logs capturados durante la búsqueda:")
                for line in captured_logs.strip().split('\n'):
                    if line.strip():
                        debug_info.append(f"  {line}")
            else:
                debug_info.append("[DEBUG] ❌ No se capturaron logs de la búsqueda")
                
        except Exception as search_error:
            sys.stdout = old_stdout
            debug_info.append(f"[DEBUG] 💥 Error durante la búsqueda: {str(search_error)}")
            debug_info.append(f"[DEBUG] 📋 Traceback: {traceback.format_exc()}")
            
        # Si no hay resultados, intentar búsqueda simple
        if not results:
            debug_info.append("[DEBUG] Sin resultados, intentando búsqueda simple...")
            try:
                # Probar directamente la API de Genius
                import requests
                import urllib.parse
                
                headers = {
                    'Authorization': f'Bearer {GENIUS_TOKEN}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                encoded_query = urllib.parse.quote("Robleis POV")
                api_url = f"https://api.genius.com/search?q={encoded_query}"
                
                debug_info.append(f"[DEBUG] Probando API directa: {api_url}")
                response = requests.get(api_url, headers=headers, timeout=5)
                debug_info.append(f"[DEBUG] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get('response', {}).get('hits', [])
                    debug_info.append(f"[DEBUG] API responde OK, hits: {len(hits)}")
                else:
                    debug_info.append(f"[DEBUG] API error: {response.text[:200]}")
                    
            except Exception as e:
                debug_info.append(f"[DEBUG] Error en test directo: {str(e)}")
        
        return jsonify({
            "success": True,
            "test_phrase": test_phrase,
            "results_count": len(results),
            "results": results[:1] if results else [],
            "debug_info": debug_info,
            "message": "Test de búsqueda por letras completado"
        })
        
    except Exception as e:
        debug_info.append(f"[DEBUG] Error general: {str(e)}")
        debug_info.append(f"[DEBUG] Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "success": False,
            "error": str(e),
            "test_phrase": test_phrase,
            "debug_info": debug_info,
            "traceback": traceback.format_exc()
        }), 500
        
        # Si no hay resultados, intentar una búsqueda más simple
        if not results:
            debug_info.append("[DEBUG] Sin resultados, intentando búsqueda simple...")
            try:
                # Probar directamente la API de Genius
                import requests
                import urllib.parse
                
                headers = {
                    'Authorization': f'Bearer {GENIUS_TOKEN}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                encoded_query = urllib.parse.quote("Robleis POV")
                api_url = f"https://api.genius.com/search?q={encoded_query}"
                
                debug_info.append(f"[DEBUG] Probando API directa: {api_url}")
                response = requests.get(api_url, headers=headers, timeout=5)
                debug_info.append(f"[DEBUG] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get('response', {}).get('hits', [])
                    debug_info.append(f"[DEBUG] API responde OK, hits: {len(hits)}")
                else:
                    debug_info.append(f"[DEBUG] API error: {response.text[:200]}")
                    
            except Exception as e:
                debug_info.append(f"[DEBUG] Error en test directo: {str(e)}")
        
        return jsonify({
            "success": True,
            "test_phrase": test_phrase,
            "results_count": len(results),
            "results": results[:1] if results else [],
            "debug_info": debug_info,
            "message": "Test de búsqueda por letras completado"
        })
        
    except Exception as e:
        debug_info.append(f"[DEBUG] Error general: {str(e)}")
        debug_info.append(f"[DEBUG] Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "success": False,
            "error": str(e),
            "test_phrase": test_phrase,
            "debug_info": debug_info,
            "traceback": traceback.format_exc()
        }), 500

@api_bp.route('/token-info')
def token_info():
    try:
        info = get_token_info()
        return jsonify({'success': True, 'token_info': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/token-info-display')
def token_info_display():
    try:
        from app_modules.utils.token import format_token_info_display
        display_info = format_token_info_display()
        return jsonify({'success': True, 'display_info': display_info})
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
                print(f"[API DEBUG] Iniciando búsqueda por letras con frase: '{query}'")
                lyrics_results = downloader.search_by_lyrics(query, limit=1)
                print(f"[API DEBUG] Resultados de búsqueda por letras: {len(lyrics_results)} encontrados")
                logger.info("/search LYRICS mode: frase='%s' -> lyrics_results=%d", query, len(lyrics_results))
                
                for i, t in enumerate(lyrics_results):
                    print(f"[API DEBUG] Procesando resultado {i+1}: {t.get('title')} - {t.get('performer', {}).get('name', 'Unknown')}")
                    
                    # Construir información del álbum con artista
                    album_info = t.get('album', {})
                    album_title = album_info.get('title', 'Unknown')
                    album_artist = album_info.get('artist', {}).get('name', '') if album_info.get('artist') else ''
                    
                    # Formatear álbum con artista si está disponible
                    if album_artist and album_artist != t.get('performer', {}).get('name', ''):
                        album_display = f"{album_title} - {album_artist}"
                    else:
                        album_display = album_title
                    
                    item = {
                        'id': t.get('id'),
                        'title': t.get('title'),
                        'artist': t.get('performer', {}).get('name', 'Unknown'),
                        'album': album_display,
                        'duration': t.get('duration', 0),
                        'cover': t.get('album', {}).get('image', {}).get('small', ''),
                        'source': t.get('source') or 'qobuz'
                    }
                    for extra in ['found_by_lyrics','genius_match','genius_url','matched_fragment','lyrics_fragment']:
                        if t.get(extra):
                            item[extra] = t.get(extra)
                    results.append(item)
                    
                if lyrics_results:
                    print(f"[API DEBUG] Primer resultado por letras: '{results[0]['title']}' source={results[0].get('source')} genius={results[0].get('genius_match')}")
                    logger.info("/search LYRICS first item: title='%s' source=%s genius=%s", results[0]['title'], results[0].get('source'), results[0].get('genius_match'))
                else:
                    print("[API DEBUG] ❌ No se encontraron resultados por letras")
            
            # Luego búsqueda normal
            tracks = downloader.search_tracks_with_locale(query, limit=15, force_latin=True)
            for t in tracks:
                # Evitar duplicados con resultados por letra
                if any((existing.get('id') and existing.get('id') == t.get('id')) or (existing.get('title') == t.get('title') and existing.get('artist') == (t.get('performer', {}) or {}).get('name', 'Unknown')) for existing in results):
                    continue
                
                # Construir información del álbum con artista
                album_info = t.get('album', {})
                album_title = album_info.get('title', 'Unknown')
                album_artist = album_info.get('artist', {}).get('name', '') if album_info.get('artist') else ''
                
                # Formatear álbum con artista si está disponible
                if album_artist and album_artist != t.get('performer', {}).get('name', ''):
                    album_display = f"{album_title} - {album_artist}"
                else:
                    album_display = album_title
                
                item = {
                    'id': t.get('id'),
                    'title': t.get('title'),
                    'artist': t.get('performer', {}).get('name', 'Unknown'),
                    'album': album_display,
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
                            # Construir información del álbum con artista
                            album_info = mapped.get('album', {})
                            album_title = album_info.get('title', 'Unknown')
                            album_artist = album_info.get('artist', {}).get('name', '') if album_info.get('artist') else ''
                            
                            # Formatear álbum con artista si está disponible
                            if album_artist and album_artist != mapped.get('performer', {}).get('name', ''):
                                album_display = f"{album_title} - {album_artist}"
                            else:
                                album_display = album_title
                            
                            results.append({
                                'id': mapped.get('id'),
                                'title': mapped.get('title'),
                                'artist': mapped.get('performer', {}).get('name','Unknown'),
                                'album': album_display,
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
                                    # Construir información del álbum con artista
                                    album_info = t.get('album', {})
                                    album_title = album_info.get('title', 'Unknown')
                                    album_artist = album_info.get('artist', {}).get('name', '') if album_info.get('artist') else ''
                                    
                                    # Formatear álbum con artista si está disponible
                                    if album_artist and album_artist != t.get('performer', {}).get('name', ''):
                                        album_display = f"{album_title} - {album_artist}"
                                    else:
                                        album_display = album_title
                                    
                                    results.append({
                                        'id': t.get('id'),
                                        'title': t.get('title'),
                                        'artist': t.get('performer', {}).get('name','Unknown'),
                                        'album': album_display,
                                        'duration': t.get('duration',0),
                                        'cover': t.get('album', {}).get('image', {}).get('small',''),
                                        'source': 'qobuz',
                                        'spotify_fallback': True
                                    })
            else:
                tracks = downloader.search_tracks_with_locale(query, limit=15, force_latin=True)
                for track in tracks:
                    # Construir información del álbum con artista
                    album_info = track.get('album', {})
                    album_title = album_info.get('title', 'Unknown')
                    album_artist = album_info.get('artist', {}).get('name', '') if album_info.get('artist') else ''
                    
                    # Formatear álbum con artista si está disponible
                    if album_artist and album_artist != track.get('performer', {}).get('name', ''):
                        album_display = f"{album_title} - {album_artist}"
                    else:
                        album_display = album_title
                    
                    results.append({
                        'id': track.get('id'),
                        'title': track.get('title'),
                        'artist': track.get('performer', {}).get('name', 'Unknown'),
                        'album': album_display,
                        'duration': track.get('duration', 0),
                        'cover': track.get('album', {}).get('image', {}).get('small', ''),
                        'source': 'qobuz'
                    })
        # Poner resultados por letra primero y, si existen, limitar a mostrar solo uno de lyrics
        if results:
            lyrics_items = [r for r in results if r.get('found_by_lyrics')]
            normal_items = [r for r in results if not r.get('found_by_lyrics')]
            if lyrics_items:
                lyrics_items = lyrics_items[:1]
            results = lyrics_items + normal_items

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

        payload = {'success': True, 'results': results, 'total': len(results)}
        if FLASK_DEBUG:
            try:
                payload['debug'] = {
                    'lyrics_count': len(lyrics_results),
                    'lyrics_titles': [r.get('title') for r in lyrics_results],
                    'first_item': results[0].get('title') if results else None,
                    'first_is_lyrics': bool(results and results[0].get('found_by_lyrics')),
                }
            except Exception:
                pass
        return jsonify(payload)
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
                    
                    # Obtener artista del álbum
                    album_artist_info = album_info.get('artist', {}) if isinstance(album_info, dict) else {}
                    album_artist_name = album_artist_info.get('name', '') if isinstance(album_artist_info, dict) else ''
                    
                    # Obtener género
                    genre_info = album_info.get('genre', {}) if isinstance(album_info, dict) else {}
                    genre_name = genre_info.get('name', '') if isinstance(genre_info, dict) else ''
                    
                    # Obtener año
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
                    
                    # Construir metadatos completos
                    metadata = {
                        'title': t_info.get('title', ''),
                        'artist': artist_name,
                        'album': album_info.get('title', '') if isinstance(album_info, dict) else '',
                        'album_artist': album_artist_name,
                        'year': year,
                        'track_number': str(t_info.get('track_number', '')) if t_info.get('track_number') else '',
                        'disc_number': str(t_info.get('media_number', '')) if t_info.get('media_number') else '',
                        'genre': genre_name
                    }
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


@api_bp.route('/auto-renewal/check')
def check_auto_renewal():
    """Verifica si es necesario renovar las credenciales"""
    try:
        result = check_and_renew_if_needed()
        return jsonify(result)
    except Exception as e:
        logger.exception("Error en auto-renewal check")
        return jsonify({
            'success': False,
            'message': f'Error verificando renovación: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@api_bp.route('/auto-renewal/force', methods=['POST'])
def force_auto_renewal():
    """Fuerza la renovación de credenciales"""
    try:
        renewer = QobuzCredentialRenewer()
        result = renewer.perform_renewal()
        return jsonify(result)
    except Exception as e:
        logger.exception("Error en force auto-renewal")
        return jsonify({
            'success': False,
            'message': f'Error forzando renovación: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@api_bp.route('/auto-renewal/status')
def auto_renewal_status():
    """Obtiene el estado actual del sistema de renovación automática"""
    try:
        from ..utils.token import get_token_info
        from ..config import load_credentials
        from ..services.vercel_adapter import check_vercel_environment
        
        # Información del token actual
        token_info = get_token_info()
        suscripcion = token_info.get('suscripcion', {})
        
        # Verificar entorno
        vercel_info = check_vercel_environment()
        
        status = {
            'token_valid': token_info.get('token_valido', False),
            'days_remaining': suscripcion.get('dias_restantes', 0),
            'needs_renewal': suscripcion.get('dias_restantes', 0) <= 7,
            'subscription_end': suscripcion.get('fecha_fin_legible'),
            'auto_renewal_enabled': True,
            'is_vercel': vercel_info['is_vercel'],
            'vercel_env': vercel_info['vercel_env'],
            'has_env_vars': vercel_info['has_qobuz_token'],
            'timestamp': datetime.now().isoformat()
        }
        
        # En desarrollo local, agregar información de credenciales guardadas
        if not vercel_info['is_vercel']:
            saved_credentials = load_credentials()
            qobuz_creds = saved_credentials.get('qobuz', {})
            status['last_update'] = qobuz_creds.get('updated_at', 'Nunca')
            status['has_saved_credentials'] = bool(qobuz_creds)
        
        return jsonify(status)
    except Exception as e:
        logger.exception("Error en auto-renewal status")
        return jsonify({
            'success': False,
            'message': f'Error obteniendo estado: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@api_bp.route('/vercel/environment')
def vercel_environment():
    """Información del entorno de Vercel"""
    try:
        from ..services.vercel_adapter import check_vercel_environment
        return jsonify(check_vercel_environment())
    except Exception as e:
        logger.exception("Error checking Vercel environment")
        return jsonify({
            'error': str(e),
            'is_vercel': bool(os.environ.get('VERCEL'))
        }), 500
