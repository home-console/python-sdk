"""
Authentication utilities for plugins
"""

from typing import Optional
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os


security = HTTPBearer(auto_error=False)


class PluginAuth:
    """Класс для аутентификации плагинов"""
    
    def __init__(self, plugin_id: str):
        """
        Args:
            plugin_id: ID плагина
        """
        self.plugin_id = plugin_id
        self._api_key = os.getenv(f"PLUGIN_{plugin_id.upper().replace('-', '_')}_API_KEY")
    
    def verify_api_key(self, api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
        """
        Проверить API ключ из заголовка
        
        Args:
            api_key: API ключ из заголовка X-API-Key
            
        Returns:
            True если ключ валиден
            
        Raises:
            HTTPException: Если ключ невалиден
        """
        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        if self._api_key and api_key != self._api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        return True
    
    def verify_bearer_token(
        self, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> str:
        """
        Проверить Bearer токен
        
        Args:
            credentials: Credentials из заголовка Authorization
            
        Returns:
            Токен если валиден
            
        Raises:
            HTTPException: Если токен невалиден
        """
        if not credentials:
            raise HTTPException(status_code=401, detail="Bearer token required")
        
        return credentials.credentials


def require_api_key(plugin_id: str):
    """
    Dependency для проверки API ключа
    
    Пример использования:
        @router.get("/private")
        async def private_endpoint(auth: bool = Depends(require_api_key("my-plugin"))):
            return {"message": "Access granted"}
    """
    auth = PluginAuth(plugin_id)
    return auth.verify_api_key


def require_bearer_token(plugin_id: str):
    """
    Dependency для проверки Bearer токена
    
    Пример использования:
        @router.get("/secure")
        async def secure_endpoint(token: str = Depends(require_bearer_token("my-plugin"))):
            return {"message": "Access granted", "token": token}
    """
    auth = PluginAuth(plugin_id)
    return auth.verify_bearer_token