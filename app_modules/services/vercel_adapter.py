"""
Adaptador del sistema de renovación para Vercel
Usa variables de entorno en lugar de archivos locales
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VercelCredentialManager:
    """
    Maneja credenciales usando variables de entorno de Vercel
    """
    
    def __init__(self):
        self.env_prefix = "QOBUZ_"
    
    def get_credentials(self) -> Dict[str, Any]:
        """
        Obtiene credenciales desde variables de entorno
        """
        credentials = {}
        
        # Intentar obtener desde variables de entorno
        token = os.environ.get(f'{self.env_prefix}TOKEN')
        app_id = os.environ.get(f'{self.env_prefix}APP_ID')
        app_secret = os.environ.get(f'{self.env_prefix}APP_SECRET')
        user_id = os.environ.get(f'{self.env_prefix}USER_ID')
        updated_at = os.environ.get(f'{self.env_prefix}UPDATED_AT')
        
        if token:
            credentials['token'] = token
        if app_id:
            credentials['app_id'] = app_id
        if app_secret:
            credentials['app_secret'] = app_secret
        if user_id:
            credentials['user_id'] = user_id
        if updated_at:
            credentials['updated_at'] = updated_at
            
        return credentials
    
    def format_credentials_for_display(self, credentials: Dict[str, str]) -> str:
        """
        Formatea las credenciales para mostrar al usuario como variables de entorno
        """
        if not credentials:
            return "No se encontraron credenciales nuevas"
        
        lines = ["📋 NUEVAS CREDENCIALES ENCONTRADAS:", ""]
        lines.append("Para actualizar en Vercel, ve a tu dashboard y actualiza estas variables de entorno:")
        lines.append("")
        
        if 'token' in credentials:
            lines.append(f"QOBUZ_TOKEN = {credentials['token']}")
        if 'app_id' in credentials:
            lines.append(f"QOBUZ_APP_ID = {credentials['app_id']}")
        if 'app_secret' in credentials:
            lines.append(f"QOBUZ_APP_SECRET = {credentials['app_secret']}")
        if 'user_id' in credentials:
            lines.append(f"QOBUZ_USER_ID = {credentials['user_id']}")
        
        lines.append("")
        lines.append(f"QOBUZ_UPDATED_AT = {datetime.now().isoformat()}")
        lines.append("")
        lines.append("⚠️ IMPORTANTE: Después de actualizar las variables, redeploy tu aplicación en Vercel")
        
        return "\n".join(lines)
    
    def save_to_local_storage_format(self, credentials: Dict[str, str]) -> str:
        """
        Convierte las credenciales a formato JSON para localStorage del navegador
        """
        storage_data = {
            'qobuz_credentials': credentials,
            'updated_at': datetime.now().isoformat(),
            'source': 'auto_renewal'
        }
        return json.dumps(storage_data, indent=2)


def get_current_token_vercel() -> str:
    """
    Obtiene el token actual priorizando variables de entorno de Vercel
    """
    # Prioridad: Variable de entorno específica > Variable general > Fallback
    token = (
        os.environ.get('QOBUZ_TOKEN') or
        os.environ.get('TOKEN') or
        "wGhVEBhBrpMHmQ1TnZ7njn0_WuGUUeujgHP-KBerx1DRiYeKcgO0Czm8_Us6W9WvxPWmJd0IEnEBi75FE0qE1w"
    )
    return token


def check_vercel_environment() -> Dict[str, Any]:
    """
    Verifica el entorno de Vercel y las variables disponibles
    """
    env_info = {
        'is_vercel': bool(os.environ.get('VERCEL')),
        'vercel_env': os.environ.get('VERCEL_ENV'),
        'vercel_url': os.environ.get('VERCEL_URL'),
        'has_qobuz_token': bool(os.environ.get('QOBUZ_TOKEN')),
        'has_legacy_token': bool(os.environ.get('TOKEN')),
        'current_token_preview': get_current_token_vercel()[:20] + "...",
        'environment_vars': {
            key: "***" if 'TOKEN' in key or 'SECRET' in key else value
            for key, value in os.environ.items()
            if key.startswith('QOBUZ_') or key in ['VERCEL', 'VERCEL_ENV', 'VERCEL_URL']
        }
    }
    return env_info
