"""
Sistema de renovación automática de credenciales de Qobuz
Extrae credenciales específicamente de la página arldeemix.com
"""

import requests
import re
import json
import base64
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import time
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArlDeemixScraper:
    def __init__(self):
        self.base_url = 'https://www.arldeemix.com/2024/12/qobuzdownloaderx-arl-premium-nueva.html'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_from_arldeemix(self) -> Optional[Dict[str, str]]:
        """
        Extrae credenciales específicamente de la página arldeemix
        """
        try:
            logger.info("Obteniendo página de arldeemix...")
            response = requests.get(self.base_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar enlaces a rentry.org en el contenido
            rentry_links = []
            
            # Buscar en enlaces directos
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'rentry.org' in href:
                    rentry_links.append(href)
            
            # Buscar en el texto del contenido
            content_text = soup.get_text()
            rentry_matches = re.findall(r'https://rentry\.org/[\w\-]+', content_text)
            rentry_links.extend(rentry_matches)
            
            # También buscar patrones específicos en el HTML
            html_text = str(soup)
            more_rentry = re.findall(r'rentry\.org/[\w\-]+', html_text)
            for match in more_rentry:
                if not match.startswith('http'):
                    rentry_links.append(f'https://{match}')
            
            logger.info(f"Enlaces encontrados: {rentry_links}")
            
            # Probar cada enlace de rentry
            for link in set(rentry_links):  # usar set para evitar duplicados
                credentials = self.extract_from_rentry(link)
                if credentials:
                    return credentials
            
            # Si no hay enlaces de rentry, buscar directamente en el contenido
            credentials = self.extract_credentials_from_text(content_text)
            if credentials:
                return credentials
                
        except Exception as e:
            logger.error(f"Error extrayendo de arldeemix: {e}")
        
        return None
    
    def extract_from_rentry(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extrae credenciales de una página rentry
        """
        try:
            # Convertir a URL raw si es necesario
            raw_url = url
            if '/raw/' not in url:
                raw_url = url.replace('rentry.org/', 'rentry.org/raw/')
            
            logger.info(f"Obteniendo contenido de: {raw_url}")
            response = requests.get(raw_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            content = response.text
            credentials = self.extract_credentials_from_text(content)
            
            if credentials:
                logger.info(f"Credenciales encontradas en {url}")
                return credentials
            
            # Si no encuentra en raw, probar la URL normal
            if raw_url != url:
                logger.info(f"Probando URL normal: {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar en elementos de código
                for code_elem in soup.find_all(['code', 'pre', 'textarea']):
                    credentials = self.extract_credentials_from_text(code_elem.get_text())
                    if credentials:
                        return credentials
                
                # Buscar en todo el texto
                credentials = self.extract_credentials_from_text(soup.get_text())
                if credentials:
                    return credentials
            
        except Exception as e:
            logger.error(f"Error extrayendo de rentry {url}: {e}")
        
        return None
    
    def extract_credentials_from_text(self, text: str) -> Optional[Dict[str, str]]:
        """
        Extrae credenciales usando patrones regex específicos para Qobuz
        """
        # Limpiar el texto
        clean_text = re.sub(r'[\n\r\t]+', ' ', text)
        
        credentials = {}
        
        # Buscar app_id con patrón específico encontrado
        app_id_patterns = [
            r'app_id[\s:=]+(\d{9})',  # Patrón específico encontrado
            r'app[_\s]*id[:\s=]+["\']?(\d{8,12})["\']?',
            r'(\d{9})'  # Cualquier número de 9 dígitos
        ]
        
        for pattern in app_id_patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            if matches:
                # Usar el primer match válido
                app_id = matches[0] if isinstance(matches[0], str) else str(matches[0])
                if len(app_id) >= 8:
                    credentials['app_id'] = app_id
                    logger.info(f"Encontrado app_id: {app_id}")
                    break
        
        # Buscar app_secret con patrón específico encontrado
        secret_patterns = [
            r'app_secret[\s:=]+([a-f0-9]{32})',  # Patrón hexadecimal específico
            r'app[_\s]*secret[:\s=]+["\']?([a-zA-Z0-9+/=_-]{20,100})["\']?',
            # Buscar después del app_id conocido
            rf'798273057[^a-zA-Z0-9]*([a-f0-9]{{32}})',
            rf'{credentials.get("app_id", "798273057")}[^a-zA-Z0-9]*([a-f0-9]{{32}})' if 'app_id' in credentials else None
        ]
        
        for pattern in secret_patterns:
            if pattern is None:
                continue
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            if matches:
                secret = matches[0] if isinstance(matches[0], str) else str(matches[0])
                if len(secret) >= 20 and secret != credentials.get('app_id'):
                    credentials['app_secret'] = secret
                    logger.info(f"Encontrado app_secret: {secret[:15]}...")
                    break
        
        # Buscar token - strings muy largos base64-like
        token_patterns = [
            r'Token\s+➠([a-zA-Z0-9+/=_\-]{50,}?)(?=User|Email|\s|$)',  # Patrón específico con límite
            r'token[:\s=]+["\']?([a-zA-Z0-9+/=_\-]{50,200})["\']?',
            r'([a-zA-Z0-9+/=_\-]{80,150})'  # Cualquier string muy largo pero limitado
        ]
        
        for pattern in token_patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            if matches:
                for match in matches:
                    token = match.strip() if isinstance(match, str) else str(match).strip()
                    # Verificar que no sea igual a otros campos y sea suficientemente largo
                    if (len(token) >= 50 and 
                        token != credentials.get('app_id') and 
                        token != credentials.get('app_secret')):
                        credentials['token'] = token
                        logger.info(f"Encontrado token: {token[:25]}...")
                        break
            if 'token' in credentials:
                break
        
        # Buscar user_id
        user_id_patterns = [
            r'User\s+ID\s+➠\s+(\d+)',  # Patrón específico encontrado
            r'user[_\s]*id[:\s=]+["\']?(\d{6,})["\']?',
            r'userid[:\s=]+["\']?(\d{6,})["\']?'
        ]
        
        for pattern in user_id_patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            if matches:
                user_id = matches[0] if isinstance(matches[0], str) else str(matches[0])
                if len(user_id) >= 6:
                    credentials['user_id'] = user_id
                    logger.info(f"Encontrado user_id: {user_id}")
                    break
        
        # Debug: mostrar todo lo que encontramos
        logger.info(f"Credenciales extraídas: {list(credentials.keys())}")
        
        # Validar que tenemos al menos app_id y app_secret
        required_fields = ['app_id', 'app_secret']
        if all(field in credentials for field in required_fields):
            return credentials
        
        # Si no tenemos app_secret, pero tenemos token, también es válido
        if 'token' in credentials and len(credentials['token']) >= 50:
            return credentials
        
        logger.warning(f"Credenciales incompletas: {credentials}")
        return None


class QobuzCredentialRenewer:
    def __init__(self):
        self.scraper = ArlDeemixScraper()
        # Detectar si estamos en Vercel
        self.is_vercel = bool(os.environ.get('VERCEL'))
        if self.is_vercel:
            from .vercel_adapter import VercelCredentialManager
            self.vercel_manager = VercelCredentialManager()
    
    def should_renew(self, days_remaining: int, threshold_days: int = 7) -> bool:
        """
        Determina si se debe renovar las credenciales
        """
        return days_remaining <= threshold_days
    
    def validate_token(self, token: str) -> bool:
        """
        Valida si un token de Qobuz funciona
        """
        try:
            from ..utils.token import get_downloader
            downloader = get_downloader()
            user_info = downloader.get_user_info(token)
            return user_info is not None
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
    
    def search_new_credentials(self, skip_validation: bool = False) -> Optional[Dict[str, str]]:
        """
        Busca nuevas credenciales en la página arldeemix
        
        Args:
            skip_validation: Si True, no valida el token (útil para pruebas)
        """
        logger.info("Buscando nuevas credenciales en arldeemix...")
        
        credentials = self.scraper.extract_from_arldeemix()
        
        if credentials and ('token' in credentials or ('app_id' in credentials and 'app_secret' in credentials)):
            logger.info("Credenciales encontradas, validando...")
            
            # Validar el token si está disponible y no se omite la validación
            if 'token' in credentials and not skip_validation:
                if self.validate_token(credentials['token']):
                    logger.info("Token válido encontrado!")
                    return credentials
                else:
                    logger.warning("Token encontrado pero no válido")
            elif 'token' in credentials and skip_validation:
                logger.info("Token encontrado (validación omitida)")
                return credentials
            else:
                # Si solo tenemos app_id y app_secret, aceptar (se puede generar token después)
                logger.info("App ID y Secret encontrados")
                return credentials
        
        logger.warning("No se encontraron credenciales válidas")
        return None
    
    def update_config_file(self, credentials: Dict[str, str]) -> bool:
        """
        En Vercel: retorna las credenciales para mostrar al usuario
        En local: actualiza el archivo de configuración
        """
        if self.is_vercel:
            # En Vercel no podemos actualizar variables de entorno automáticamente
            # Solo retornamos True y las credenciales se mostrarán al usuario
            return True
        else:
            # En desarrollo local, actualizar archivo
            try:
                from ..config import update_qobuz_credentials
                return update_qobuz_credentials(credentials)
            except Exception as e:
                logger.error(f"Error updating config: {e}")
                return False
    
    def perform_renewal(self) -> Dict[str, Any]:
        """
        Realiza el proceso completo de renovación
        """
        result = {
            'success': False,
            'message': '',
            'new_credentials': None,
            'vercel_instructions': None,
            'is_vercel': self.is_vercel,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Buscar nuevas credenciales
            new_credentials = self.search_new_credentials()
            
            if not new_credentials:
                result['message'] = 'No se encontraron nuevas credenciales válidas en arldeemix.com'
                return result
            
            # En Vercel, preparar instrucciones para el usuario
            if self.is_vercel:
                result['success'] = True
                result['message'] = 'Credenciales encontradas! Actualiza las variables de entorno en Vercel'
                result['vercel_instructions'] = self.vercel_manager.format_credentials_for_display(new_credentials)
                result['local_storage_data'] = self.vercel_manager.save_to_local_storage_format(new_credentials)
                result['new_credentials'] = {
                    'app_id': new_credentials.get('app_id', 'No disponible'),
                    'user_id': new_credentials.get('user_id', 'No disponible'),
                    'token_preview': new_credentials.get('token', '')[:20] + '...' if new_credentials.get('token') else 'No disponible'
                }
            else:
                # En local, actualizar configuración
                if self.update_config_file(new_credentials):
                    result['success'] = True
                    result['message'] = 'Credenciales actualizadas exitosamente desde arldeemix.com'
                    result['new_credentials'] = {
                        'app_id': new_credentials.get('app_id', 'No disponible'),
                        'user_id': new_credentials.get('user_id', 'No disponible'),
                        'token_preview': new_credentials.get('token', '')[:20] + '...' if new_credentials.get('token') else 'No disponible'
                    }
                else:
                    result['message'] = 'Error al actualizar el archivo de configuración'
            
        except Exception as e:
            result['message'] = f'Error durante la renovación: {str(e)}'
            logger.error(f"Error en perform_renewal: {e}")
        
        return result


def check_and_renew_if_needed() -> Dict[str, Any]:
    """
    Función principal que verifica si es necesario renovar y lo hace automáticamente
    """
    try:
        from ..utils.token import get_token_info, calculate_time_remaining
        
        # Obtener información actual del token
        token_info = get_token_info()
        
        if not token_info.get('token_valido'):
            logger.warning("Token actual no válido, intentando renovación...")
            renewer = QobuzCredentialRenewer()
            return renewer.perform_renewal()
        
        # Verificar si necesita renovación
        suscripcion = token_info.get('suscripcion', {})
        dias_restantes = suscripcion.get('dias_restantes', 0)
        
        renewer = QobuzCredentialRenewer()
        
        if renewer.should_renew(dias_restantes):
            logger.info(f"Token expira en {dias_restantes} días, iniciando renovación automática...")
            return renewer.perform_renewal()
        else:
            return {
                'success': True,
                'message': f'Token válido por {dias_restantes} días más, no requiere renovación',
                'days_remaining': dias_restantes,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error en check_and_renew_if_needed: {e}")
        return {
            'success': False,
            'message': f'Error verificando renovación: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }


__all__ = ['QobuzCredentialRenewer', 'check_and_renew_if_needed']
