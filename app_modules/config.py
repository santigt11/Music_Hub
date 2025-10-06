import os
import json
from typing import Dict, Any

def _get_required_env_var(var_name: str) -> str:
    """
    Obtiene una variable de entorno requerida, lanza error si no existe
    """
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(f"Variable de entorno requerida no encontrada: {var_name}. "
                        f"Configúrala en Vercel para que la aplicación funcione correctamente.")
    return value

# Variables de entorno requeridas en Vercel
try:
    QOBUZ_TOKEN = _get_required_env_var('QOBUZ_TOKEN')
    QOBUZ_USER_ID = _get_required_env_var('QOBUZ_USER_ID')
    QOBUZ_APP_ID = _get_required_env_var('QOBUZ_APP_ID')
    QOBUZ_APP_SECRET = _get_required_env_var('QOBUZ_APP_SECRET')
    GENIUS_TOKEN = _get_required_env_var('GENIUS_TOKEN')
except ValueError as e:
    print(f"ERROR DE CONFIGURACIÓN: {e}")
    print("Por favor, configura las siguientes variables de entorno en Vercel:")
    print("- QOBUZ_TOKEN")
    print("- QOBUZ_USER_ID")
    print("- QOBUZ_APP_ID")
    print("- QOBUZ_APP_SECRET")
    print("- GENIUS_TOKEN")
    raise

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
    Obtiene el token actual desde variables de entorno
    """
    return QOBUZ_TOKEN

def get_current_user_id() -> str:
    """
    Obtiene el User ID actual desde variables de entorno
    """
    return QOBUZ_USER_ID

def get_current_app_id() -> str:
    """
    Obtiene el App ID actual desde variables de entorno
    """
    return QOBUZ_APP_ID

def get_current_app_secret() -> str:
    """
    Obtiene el App Secret actual desde variables de entorno
    """
    return QOBUZ_APP_SECRET

def get_genius_token() -> str:
    """
    Obtiene el token de Genius desde variables de entorno
    """
    return GENIUS_TOKEN

# Variables globales para compatibilidad
CURRENT_QOBUZ_TOKEN = QOBUZ_TOKEN

__all__ = [
    "QOBUZ_TOKEN", "QOBUZ_USER_ID", "QOBUZ_APP_ID", "QOBUZ_APP_SECRET", 
    "CURRENT_QOBUZ_TOKEN", "GENIUS_TOKEN", "FLASK_DEBUG", "PORT", 
    "update_qobuz_credentials", "get_current_token", "get_current_user_id",
    "get_current_app_id", "get_current_app_secret", "get_genius_token",
    "load_credentials"
]
