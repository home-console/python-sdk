"""
Plugin base classes for Home Console plugins.

Two types of plugins are supported:
1. PluginBase - для ВНЕШНИХ плагинов (микросервисы, HTTP)
2. InternalPluginBase - для ВСТРАИВАЕМЫХ плагинов (в core-service)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TYPE_CHECKING
from .client import CoreAPIClient
from .db import DatabaseClient
from .events import EventsClient
from .config import PluginConfig
from .tasks import TaskManager
import logging
import os
import json
from pathlib import Path
from fastapi import APIRouter

if TYPE_CHECKING:
    from fastapi import Request


class PluginBase(ABC):
    """
    Базовый класс для ВНЕШНИХ плагинов (микросервисы, HTTP).
    
    **Это для ВНЕШНИХ плагинов** - независимых приложений, запущенных отдельно от core-service.
    Общаются с Core по HTTP API через CoreAPIClient.
    
    Для ВНУТРЕННИХ плагинов (загружаемые в core-service) используйте: InternalPluginBase
    
    Базовый класс для внешних плагинов (микросервисов)
    
    Пример использования:
    
    class MyPlugin(PluginBase):
        id = "my-plugin"
        name = "My Plugin"
        version = "1.0.0"
        
        async def on_start(self):
            # Инициализация
            pass
        
        async def on_stop(self):
            # Cleanup
            pass
        
        async def handle_event(self, event_name: str, data: dict):
            # Обработка событий
            pass
    
    # Запуск:
    plugin = MyPlugin()
    await plugin.run()
    
    Примечание: Это ВНЕШНИЙ плагин. Запускается как отдельный процесс/контейнер.
    Для встраиваемых плагинов используйте InternalPluginBase из core-service.
    """
    
    # Метаданные (обязательны)
    id: str = "unknown"
    name: str = "Unknown Plugin"
    version: str = "1.0.0"
    description: str = ""
    
    def __init__(self):
        self.logger = logging.getLogger(f"plugin.{self.id}")
        
        # Core API client
        core_api_url = os.getenv("CORE_API_URL", "http://core-api:8000")
        self.core = CoreAPIClient(core_api_url)
        
        # Config
        self._config = {}
    
    @abstractmethod
    async def on_start(self):
        """Вызывается при старте плагина"""
        pass
    
    async def on_stop(self):
        """Вызывается при остановке плагина (опционально)"""
        pass

    async def health(self) -> Dict[str, Any]:
        """Health check"""
        return {"status": "healthy", "version": self.version}
    
    async def handle_event(self, event_name: str, data: Dict[str, Any]):
        """Обработка событий от Core API (опционально)"""
        pass
    
    # ========== HELPERS ==========
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Получить конфигурацию"""
        env_key = f"PLUGIN_{self.id.upper().replace('-', '_')}_{key.upper()}"
        return os.getenv(env_key, default)
    
    async def authenticate(self):
        """Аутентификация в Core API"""
        username = self.get_config("USERNAME", "plugin")
        password = self.get_config("PASSWORD")
        
        if not password:
            raise ValueError(f"PLUGIN_{self.id.upper()}_PASSWORD not set")
        
        await self.core.login(username, password)
        self.logger.info("✅ Authenticated with Core API")
    
    async def run(self):
        """Запустить плагин"""
        try:
            self.logger.info(f"🚀 Starting {self.name} v{self.version}")
            
            # Аутентификация
            await self.authenticate()
            
            # Инициализация плагина
            await self.on_start()
            
            self.logger.info(f"✅ {self.name} started successfully")
            
            # TODO: Event loop для обработки событий
            # (Можно добавить WebSocket для real-time событий)
            
        except KeyboardInterrupt:
            self.logger.info("⚠️ Shutting down...")
        finally:
            await self.on_stop()
            await self.core.close()
            self.logger.info("👋 Stopped")


class InternalPluginBase(ABC):
    """
    Базовый класс для встраиваемых плагинов (в процессе Core Service).
    
    **Это для ВНУТРЕННИХ плагинов**, которые загружаются непосредственно в core-service.
    Имеют прямой доступ к БД, EventBus и FastAPI приложению.
    
    Для ВНЕШНИХ плагинов (микросервисы) используйте: PluginBase
    
    Плагины загружаются автоматически из папки plugins/ через PluginLoader.
    
    Пример использования:
    
    ```python
    from home_console_sdk.plugin import InternalPluginBase
    from fastapi import APIRouter
    
    class DevicesPlugin(InternalPluginBase):
        id = "devices"
        name = "Devices Manager"
        version = "1.0.0"
        
        async def on_load(self):
            # Инициализация при загрузке
            self.logger.info("Devices plugin loaded")
            # Создаем FastAPI роутер и регистрируем endpoints
            self.router = APIRouter()
            # ...
        
        async def on_unload(self):
            # Cleanup при выгрузке (опционально)
            self.logger.info("Devices plugin unloaded")
    ```
    """
    
    # Метаданные плагина (должны быть переопределены в наследнике)
    id: str = "unknown"
    name: str = "Unknown Plugin"
    version: str = "1.0.0"
    description: str = ""
    
    # Router для регистрации endpoint'ов
    router: Optional[APIRouter] = None
    
    # Флаг состояния плагина
    _is_loaded: bool = False
    _router_mounted: bool = False
    
    def __init__(self, app, db_session_maker, event_bus, models: Optional[Dict[str, Any]] = None):
        """
        Инициализация плагина.
        
        Args:
            app: FastAPI приложение
            db_session_maker: async_sessionmaker для БД доступа
            event_bus: EventBus для публикации/подписки на события
            models: Dict с SQLAlchemy моделями для Dependency Injection
                    Пример: {'Device': Device, 'User': User, 'PluginBinding': PluginBinding}
                    
        Пример использования моделей:
            ```python
            class MyPlugin(InternalPluginBase):
                async def on_load(self):
                    # Получаем модель через DI
                    Device = self.models.get('Device')
                    
                    if Device:
                        async with self.db_session_maker() as db:
                            device = Device(name="New Device")
                            db.add(device)
                            await db.commit()
            ```
        """
        self.app = app
        self.db_session_maker = db_session_maker
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"plugin.{self.id}")
        
        # Dependency Injection моделей
        self.models = models or {}
        
        # Инициализация клиентов и утилит
        self.db = DatabaseClient(self.id, db_session_maker)
        self.events = EventsClient(self.id, event_bus)
        self.config = PluginConfig(self.id)
        self.tasks = TaskManager(self.id)
        
        # Флаги состояния
        self._is_loaded = False
        self._router_mounted = False
    
    @abstractmethod
    async def on_load(self):
        """Вызывается при загрузке плагина. Обязателен к реализации."""
        pass
    
    async def on_unload(self):
        """Вызывается при выгрузке плагина (опционально)."""
        pass
    
    # ========== LIFECYCLE METHODS ==========
    
    async def mount_router(self):
        """
        Монтировать router в FastAPI приложение.
        
        Вызывается автоматически plugin_loader после on_load().
        НЕ вызывайте вручную - используется только внутри plugin_loader!
        """
        if self.router and not self._router_mounted:
            try:
                # Монтируем router с prefix /plugins/{plugin_id}
                self.app.include_router(
                    self.router,
                    prefix=f"/plugins/{self.id}",
                    tags=[self.id]
                )
                self._router_mounted = True
                self.logger.info(f"✅ Router mounted at /plugins/{self.id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to mount router: {e}")
                raise
    
    async def unmount_router(self):
        """
        Отмонтировать router из FastAPI приложения.
        
        Вызывается автоматически при on_unload() или при ошибке загрузки.
        НЕ вызывайте вручную - используется только внутри plugin_loader!
        """
        if self.router and self._router_mounted:
            try:
                # FastAPI не имеет встроенного метода для удаления router
                # Фильтруем routes, исключая routes этого плагина
                prefix = f"/plugins/{self.id}"
                self.app.routes = [
                    route for route in self.app.routes
                    if not (hasattr(route, 'path') and route.path.startswith(prefix))
                ]
                self._router_mounted = False
                self.logger.info(f"✅ Router unmounted from /plugins/{self.id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to unmount router: {e}")
    
    @property
    def is_loaded(self) -> bool:
        """Проверить, загружен ли плагин"""
        return self._is_loaded
    
    @property
    def is_router_mounted(self) -> bool:
        """Проверить, смонтирован ли router"""
        return self._router_mounted
    
    # ========== HELPER МЕТОДЫ ==========
    
    async def emit_event(self, event_name: str, data: Dict[str, Any]):
        """
        Опубликовать событие в EventBus.
        
        Args:
            event_name: Имя события (будет префиксировано plugin.id)
            data: Данные события
        """
        await self.events.emit(event_name, data)
    
    async def subscribe_event(self, event_pattern: str, handler):
        """
        Подписаться на события.
        
        Args:
            event_pattern: Паттерн события (например: "device.*" или "*.state_changed")
            handler: Async функция-обработчик(event_name: str, data: dict)
        """
        await self.events.subscribe(event_pattern, handler)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Получить значение конфигурации из переменных окружения.
        
        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию
            
        Returns:
            Значение из env или default
            
        Пример:
            api_key = plugin.get_config("API_KEY", "default-key")
            # Ищет переменную окружения: PLUGIN_MYPLUG_API_KEY
        """
        env_key = f"PLUGIN_{self.id.upper().replace('-', '_')}_{key.upper()}"
        return os.getenv(env_key, default)
    
    async def _get_current_user_id(self, request) -> str:
        """
        Извлечь user_id из request без зависимостей от ядра.
        
        Использует только Dependency Injection и request.state, установленный middleware.
        Не требует прямых импортов из core-service.
        
        Args:
            request: FastAPI Request объект
            
        Returns:
            user_id как строка
            
        Raises:
            HTTPException: 401 если пользователь не авторизован
            
        Пример использования:
            ```python
            @router.get("/my-endpoint")
            async def my_endpoint(request: Request):
                user_id = await self._get_current_user_id(request)
                # Используем user_id для работы с данными пользователя
            ```
        
        Примечание:
            - Плагины могут переопределить этот метод для кастомной логики
            - Метод автоматически получает get_current_user_fn из app.state (если доступен)
            - Middleware должен устанавливать request.state.user для cookie-авторизации
        """
        from fastapi import HTTPException
        
        # Option 1: User already set by middleware/dependency
        if hasattr(request.state, 'user') and request.state.user:
            user = request.state.user
            # Handle both User object and dict payload
            if hasattr(user, 'id'):
                return str(user.id)
            elif isinstance(user, dict):
                user_id = user.get('sub') or user.get('id')
                if user_id:
                    return str(user_id)
            else:
                return str(user)
        
        # Option 2: Try to use get_current_user_fn if available (DI from core)
        # This function is injected by plugin_loader and handles both Bearer token and cookies
        get_current_user_fn = getattr(self, 'get_current_user_fn', None)
        if not get_current_user_fn and hasattr(self, 'app'):
            # Try to get from app.state (set by core-service)
            get_current_user_fn = getattr(self.app.state, 'get_current_user', None)
        
        if get_current_user_fn:
            try:
                from fastapi.security import HTTPAuthorizationCredentials
                
                # Try with Bearer token first
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    # Create mock credentials object
                    class MockCredentials:
                        def __init__(self, token):
                            self.credentials = token
                    
                    try:
                        # Try to call with credentials
                        user = await get_current_user_fn(request, MockCredentials(token))
                        if user:
                            return str(user.id if hasattr(user, 'id') else user)
                    except Exception:
                        # If that fails, try without credentials (it will check cookies)
                        pass
                
                # Fallback: try without credentials (will check cookies)
                try:
                    user = await get_current_user_fn(request)
                    if user:
                        return str(user.id if hasattr(user, 'id') else user)
                except Exception as e:
                    self.logger.debug(f"get_current_user_fn failed: {e}")
            except Exception as e:
                self.logger.debug(f"Failed to use get_current_user_fn: {e}")
        
        # Option 3: Try to extract user_id from token payload directly (if middleware set it)
        try:
            # Check if there's a token payload in request state (set by middleware)
            if hasattr(request.state, 'token_payload'):
                payload = request.state.token_payload
                if isinstance(payload, dict):
                    user_id = payload.get('sub') or payload.get('id')
                    if user_id:
                        return str(user_id)
        except Exception:
            pass
        
        # No user found - raise 401
        raise HTTPException(status_code=401, detail="Unauthorized: user authentication required")
    
    @classmethod
    def load_manifest(cls, manifest_path: str) -> Optional[Dict[str, Any]]:
        """
        Загрузить метаданные плагина из plugin.json.
        
        Args:
            manifest_path: Путь к plugin.json
            
        Returns:
            Dict с метаданными или None если файл не найден
            
        Пример:
            # В plugin_loader.py
            metadata = InternalPluginBase.load_manifest("/opt/plugins/my-plugin/plugin.json")
            if metadata:
                plugin.name = metadata.get('name', plugin.name)
                plugin.version = metadata.get('version', plugin.version)
        """
        try:
            path = Path(manifest_path)
            if not path.exists():
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return metadata
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to load manifest from {manifest_path}: {e}")
            return None
