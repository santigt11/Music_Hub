"""Funciones utilitarias relacionadas con el token de Qobuz"""
from __future__ import annotations
import base64
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ..config import QOBUZ_TOKEN
from ..app_factory import get_downloader


def calculate_time_remaining(end_date: Optional[any]) -> Dict[str, Any]:
    """Calcula el tiempo restante basado en un timestamp o fecha string"""
    if not end_date:
        return {
            'tiempo_restante': 'No disponible',
            'estado': 'indefinido',
            'timestamp_fin': None
        }
    
    try:
        # Manejar diferentes formatos de fecha
        if isinstance(end_date, str):
            # Formato de fecha string como "2025-10-08"
            if len(end_date) == 10:  # YYYY-MM-DD
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            else:
                # Otros formatos de string
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        elif isinstance(end_date, (int, float)):
            # Timestamp numérico
            end_datetime = datetime.fromtimestamp(end_date, tz=timezone.utc)
        else:
            return {
                'tiempo_restante': f'Formato no soportado: {type(end_date)}',
                'estado': 'error',
                'timestamp_fin': end_date
            }
        
        now = datetime.now(timezone.utc)
        
        # Calcular diferencia
        time_diff = end_datetime - now
        
        if time_diff.total_seconds() <= 0:
            return {
                'tiempo_restante': 'Expirado',
                'estado': 'expirado',
                'fecha_original': end_date,
                'fecha_fin_legible': end_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        
        # Calcular días, horas, minutos
        total_seconds = int(time_diff.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        # Formatear tiempo restante
        if days > 0:
            if days == 1:
                tiempo_str = f"1 día, {hours} horas"
            else:
                tiempo_str = f"{days} días, {hours} horas"
        elif hours > 0:
            if hours == 1:
                tiempo_str = f"1 hora, {minutes} minutos"
            else:
                tiempo_str = f"{hours} horas, {minutes} minutos"
        else:
            if minutes == 1:
                tiempo_str = "1 minuto"
            else:
                tiempo_str = f"{minutes} minutos"
        
        return {
            'tiempo_restante': tiempo_str,
            'estado': 'activo',
            'fecha_original': end_date,
            'fecha_fin_legible': end_datetime.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'dias_restantes': days,
            'horas_restantes': hours,
            'minutos_restantes': minutes,
            'total_segundos': total_seconds
        }
    except Exception as e:
        return {
            'tiempo_restante': f'Error calculando: {str(e)}',
            'estado': 'error',
            'fecha_original': end_date
        }


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
                end_date = subscription.get('end_date')
                tiempo_info = calculate_time_remaining(end_date)
                
                info['suscripcion'] = {
                    'tipo': subscription.get('offer', 'No disponible'),
                    'estado': subscription.get('status', 'No disponible'),
                    'inicio': subscription.get('start_date'),
                    'fin': subscription.get('end_date'),
                    'periodo': subscription.get('periodicity', 'No disponible'),
                    'renovacion_automatica': subscription.get('is_recurring', False),
                    'tiempo_restante': tiempo_info['tiempo_restante'],
                    'estado_tiempo': tiempo_info['estado'],
                    'fecha_fin_legible': tiempo_info.get('fecha_fin_legible'),
                    'dias_restantes': tiempo_info.get('dias_restantes'),
                    'horas_restantes': tiempo_info.get('horas_restantes')
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

__all__ = ["get_token_info", "calculate_time_remaining"]
