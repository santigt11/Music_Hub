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
        from ..config import get_current_token
        token = get_current_token()
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
                
                # Determinar estado basado en la información disponible
                is_canceled = subscription.get('is_canceled', False)
                estado_sub = 'Cancelada' if is_canceled else 'Activa'
                
                info['suscripcion'] = {
                    'tipo': subscription.get('offer', 'No disponible'),
                    'estado': estado_sub,
                    'inicio': subscription.get('start_date'),
                    'fin': subscription.get('end_date'),
                    'periodo': subscription.get('periodicity', 'No disponible'),
                    'renovacion_automatica': not is_canceled,  # Si no está cancelada, se renueva
                    'tiempo_restante': tiempo_info['tiempo_restante'],
                    'estado_tiempo': tiempo_info['estado'],
                    'fecha_fin_legible': tiempo_info.get('fecha_fin_legible'),
                    'dias_restantes': tiempo_info.get('dias_restantes'),
                    'horas_restantes': tiempo_info.get('horas_restantes')
                }
            
            credential = user_info.get('credential', {})
            if credential:
                params = credential.get('parameters', {})
                info['calidad'] = {
                    'nivel': params.get('lossy_streaming', False),
                    'calidad_maxima': params.get('lossless_streaming', False),
                    'hires_disponible': params.get('hires_streaming', False)
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


def format_token_info_display(token_info: Dict[str, Any]) -> str:
    """Formatea la información del token para mostrar de manera visual"""
    if not token_info.get('token_valido'):
        return f"❌ Token inválido: {token_info.get('error', 'Error desconocido')}"
    
    lines = []
    lines.append("✅ Token válido")
    lines.append(f"Tipo: {token_info.get('tipo', 'No disponible')}")
    lines.append("")
    
    # Información del usuario
    usuario = token_info.get('usuario', {})
    if usuario:
        lines.append("👤 USUARIO:")
        lines.append(f"  Email: {usuario.get('email', 'No disponible')}")
        nombre = usuario.get('nombre', '')
        apellido = usuario.get('apellido', '')
        nombre_completo = f"{nombre} {apellido}".strip()
        lines.append(f"  Nombre: {nombre_completo if nombre_completo else 'No disponible'}")
        lines.append(f"  País: {usuario.get('pais', 'No disponible')}")
        lines.append(f"  ID: {usuario.get('id', 'No disponible')}")
        lines.append("")
    
    # Información de suscripción
    suscripcion = token_info.get('suscripcion', {})
    if suscripcion:
        lines.append("💳 SUSCRIPCIÓN:")
        lines.append(f"  Tipo: {suscripcion.get('tipo', 'No disponible')}")
        estado = suscripcion.get('estado', 'No disponible')
        lines.append(f"  Estado: {estado}")
        
        # Tiempo restante
        tiempo_restante = suscripcion.get('tiempo_restante')
        estado_tiempo = suscripcion.get('estado_tiempo')
        fecha_fin = suscripcion.get('fecha_fin_legible')
        
        if tiempo_restante and estado_tiempo:
            if estado_tiempo == 'activo':
                lines.append(f"  ⏰ Tiempo restante: {tiempo_restante}")
                if fecha_fin:
                    lines.append(f"  📅 Fecha de expiración: {fecha_fin}")
            elif estado_tiempo == 'expirado':
                lines.append(f"  ⏰ Estado: EXPIRADO")
                if fecha_fin:
                    lines.append(f"  📅 Expiró el: {fecha_fin}")
            else:
                lines.append(f"  📅 Fecha de expiración: {tiempo_restante}")
        else:
            lines.append(f"  📅 Fecha de expiración: No disponible")
        
        renovacion = suscripcion.get('renovacion_automatica', False)
        lines.append(f"  🔄 Renovación automática: {'Sí' if renovacion else 'No'}")
        
        periodo = suscripcion.get('periodo')
        if periodo and periodo != 'No disponible':
            periodo_es = {
                'monthly': 'Mensual',
                'yearly': 'Anual',
                'quarterly': 'Trimestral'
            }.get(periodo, periodo)
            lines.append(f"  📊 Período: {periodo_es}")
        
        lines.append("")
    
    # Información de calidad
    calidad = token_info.get('calidad', {})
    if calidad:
        lines.append("🎵 CALIDAD DISPONIBLE:")
        nivel = calidad.get('nivel')
        if nivel is not None:
            lines.append(f"  MP3: {'Sí' if nivel else 'No'}")
        
        calidad_max = calidad.get('calidad_maxima')
        if calidad_max is not None:
            lines.append(f"  FLAC: {'Sí' if calidad_max else 'No'}")
        
        hires = calidad.get('hires_disponible')
        if hires is not None:
            lines.append(f"  Hi-Res: {'Sí' if hires else 'No'}")
    
    return "\n".join(lines)


__all__ = ["get_token_info", "calculate_time_remaining", "format_token_info_display"]
