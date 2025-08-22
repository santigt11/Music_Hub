import os
import json
from typing import Dict, Any

# Configuración general y constantes
QOBUZ_TOKEN = os.environ.get('QOBUZ_TOKEN', "wGhVEBhBrpMHmQ1TnZ7njn0_WuGUUeujgHP-KBerx1DRiYeKcgO0Czm8_Us6W9WvxPWmJd0IEnEBi75FE0qE1w")

# Token de Genius API - usar variable de entorno o fallback
GENIUS_TOKEN = os.environ.get('GENIUS_TOKEN', "bOb0AM7TteQJ9J2t1JjQtHfSw2qlhp_U5oyFRenLmshiQw0jgrowXLyurdbda6Rt")

# Flask settings
FLASK_DEBUG = os.environ.get('FLASK_ENV') == 'development'
PORT = int(os.environ.get('PORT', 5000))

# Archivo donde guardar credenciales actualizadas
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', 'qobuz_credentials.json')

def load_credentials() -> Dict[str, Any]:
    """
    Carga las credenciales desde el archivo JSON si existe
    """
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading credentials: {e}")
    
    return {}

def save_credentials(credentials: Dict[str, Any]) -> bool:
    """
    Guarda las credenciales en el archivo JSON
    """
    try:
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False

def update_qobuz_credentials(new_credentials: Dict[str, str]) -> bool:
    """
    Actualiza las credenciales de Qobuz
    """
    try:
        # Cargar credenciales existentes
        all_credentials = load_credentials()
        
        # Actualizar con nuevas credenciales
        qobuz_creds = all_credentials.get('qobuz', {})
        
        if 'token' in new_credentials:
            qobuz_creds['token'] = new_credentials['token']
        if 'app_id' in new_credentials:
            qobuz_creds['app_id'] = new_credentials['app_id']
        if 'app_secret' in new_credentials:
            qobuz_creds['app_secret'] = new_credentials['app_secret']
        if 'user_id' in new_credentials:
            qobuz_creds['user_id'] = new_credentials['user_id']
        
        # Agregar timestamp de actualización
        from datetime import datetime
        qobuz_creds['updated_at'] = datetime.now().isoformat()
        
        all_credentials['qobuz'] = qobuz_creds
        
        # Guardar archivo
        return save_credentials(all_credentials)
        
    except Exception as e:
        print(f"Error updating Qobuz credentials: {e}")
        return False

def get_current_token() -> str:
    """
    Obtiene el token actual, priorizando variables de entorno de Vercel
    """
    # Detectar si estamos en Vercel
    is_vercel = bool(os.environ.get('VERCEL'))
    
    if is_vercel:
        from .services.vercel_adapter import get_current_token_vercel
        return get_current_token_vercel()
    else:
        # En desarrollo local, usar archivo de credenciales
        credentials = load_credentials()
        qobuz_creds = credentials.get('qobuz', {})
        
        # Priorizar token del archivo de credenciales
        if 'token' in qobuz_creds:
            return qobuz_creds['token']
        
        # Fallback al token por defecto
        return QOBUZ_TOKEN

# Actualizar el token global
CURRENT_QOBUZ_TOKEN = get_current_token()

__all__ = ["QOBUZ_TOKEN", "CURRENT_QOBUZ_TOKEN", "GENIUS_TOKEN", "FLASK_DEBUG", "PORT", 
          "update_qobuz_credentials", "get_current_token", "load_credentials"]
