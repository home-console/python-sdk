import httpx
from typing import List, Dict, Any, Optional
import logging

from .models import User, Device, DeviceCreate, DeviceUpdate, Plugin
from .exceptions import AuthenticationError, APIError, NotFoundError

logger = logging.getLogger(__name__)

class CoreAPIClient:
    """
    HTTP клиент для взаимодействия с Core API
    
    Пример:
        client = CoreAPIClient("http://core-api:8000")
        await client.login("admin", "password")
        devices = await client.list_devices()
    """
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        """
        Args:
            base_url: URL Core API (http://core-api:8000)
            token: JWT токен (если уже есть)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )
    
    # ========== AUTH ==========
    
    async def login(self, username: str, password: str) -> str:
        """
        Вход в систему
        
        Returns:
            JWT токен
        """
        response = await self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid credentials")
        
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return self.token
    
    async def register(self, username: str, email: str, password: str) -> User:
        """Регистрация"""
        response = await self.client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        response.raise_for_status()
        return User(**response.json())
    
    async def get_current_user(self) -> User:
        """Получить текущего пользователя"""
        response = await self._request("GET", "/api/v1/users/me")
        return User(**response)
    
    # ========== DEVICES ==========
    
    async def list_devices(self) -> List[Device]:
        """Список устройств"""
        response = await self._request("GET", "/api/v1/plugins/devices/")
        return [Device(**d) for d in response]
    
    async def get_device(self, device_id: int) -> Device:
        """Получить устройство"""
        response = await self._request("GET", f"/api/v1/plugins/devices/{device_id}")
        return Device(**response)
    
    async def create_device(self, device: DeviceCreate) -> Device:
        """Создать устройство"""
        response = await self._request(
            "POST",
            "/api/v1/plugins/devices/",
            json=device.model_dump(exclude_none=True)
        )
        return Device(**response)
    
    async def update_device(self, device_id: int, device: DeviceUpdate) -> Device:
        """Обновить устройство"""
        response = await self._request(
            "PUT",
            f"/api/v1/plugins/devices/{device_id}",
            json=device.model_dump(exclude_none=True)
        )
        return Device(**response)
    
    async def delete_device(self, device_id: int):
        """Удалить устройство"""
        await self._request("DELETE", f"/api/v1/plugins/devices/{device_id}")
    
    # ========== PLUGINS ==========
    
    async def get_plugin(self, plugin_id: str):
        """Получить информацию о плагине"""
        response = await self.client.get(f"/api/v1/plugins/{plugin_id}")
        return response.json()

    async def get_list_plugins(self) -> List[Plugin]:
        """Список плагинов"""
        response = await self._request("GET", "/api/v1/admin/plugins")
        # Response is list of dicts with different structure
        return response

    async def call_plugin(self, plugin_id: str, endpoint: str, **kwargs):
        """Вызвать endpoint другого плагина"""
        response = await self.client.post(
            f"/api/v1/{plugin_id}/{endpoint}",
            json=kwargs
        )
        return response.json()

    async def get_stats(self) -> Dict[str, Any]:
        """Статистика системы"""
        return await self._request("GET", "/api/v1/admin/stats")
    
    # ========== HELPERS ==========
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Any:
        """
        Внутренний метод для HTTP запросов
        
        Автоматически добавляет токен и обрабатывает ошибки
        """
        if not self.token:
            raise AuthenticationError("Not authenticated. Call login() first")
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        
        response = await self.client.request(
            method,
            path,
            headers=headers,
            **kwargs
        )
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired token")
        elif response.status_code == 404:
            raise NotFoundError(f"Resource not found: {path}")
        elif response.status_code >= 400:
            raise APIError(
                f"API error: {response.text}",
                status_code=response.status_code
            )
        
        if response.status_code == 204:
            return None
        
        return response.json()
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
