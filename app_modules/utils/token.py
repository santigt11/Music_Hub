"""Funciones utilitarias relacionadas con el token de Qobuz"""
from __future__ import annotations
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any
from ..config import QOBUZ_TOKEN
from ..app_factory import get_downloader


def get_token_info(token: Optional[str] = None) -> Dict[str, Any]:
    if not token:
        token = QOBUZ_TOKEN
    try:
        downloader = get_downloader()
        user_info = downloader.get_user_info(token)
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
            credential = user_info.get('credential', {})
            if credential:
                info['calidad'] = {
                    'nivel': credential.get('parameters', {}).get('lossy_streaming', 'No disponible'),
                    'calidad_maxima': credential.get('parameters', {}).get('lossless_streaming', 'No disponible'),
                    'hires_disponible': credential.get('parameters', {}).get('hires_streaming', False)
                }
            return info
        return {'token_valido': False, 'error': 'No se pudo obtener información del usuario'}
    except Exception as e:
        info = {
            'token_valido': False,
            'tipo': 'Error en consulta API',
            'error_api': str(e),
            'longitud': len(token),
            'primeros_chars': token[:20] + '...' if len(token) > 20 else token
        }
        try:
            decoded_bytes = base64.b64decode(token + '==')
            decoded_str = decoded_bytes.decode('utf-8')
            if decoded_str.startswith('{'):
                token_data = json.loads(decoded_str)
                info['tipo'] = 'Token decodificado (pero API falló)'
                info['datos_token'] = token_data
        except Exception:
            pass
        return info

__all__ = ["get_token_info"]
