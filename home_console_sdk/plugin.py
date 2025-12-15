"""
Plugin base classes for Home Console plugins.

Two types of plugins are supported:
1. PluginBase - для ВНЕШНИХ плагинов (микросервисы, HTTP)
2. InternalPluginBase - для ВСТРАИВАЕМЫХ плагинов (в core-service)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .client import CoreAPIClient
import logging
import os
from fastapi import APIRouter


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
    
    def __init__(self, app, db_session_maker, event_bus):
        """
        Инициализация плагина.
        
        Args:
            app: FastAPI приложение
            db_session_maker: async_sessionmaker для БД доступа
            event_bus: EventBus для публикации/подписки на события
        """
        self.app = app
        self.db_session_maker = db_session_maker
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"plugin.{self.id}")
    
    @abstractmethod
    async def on_load(self):
        """Вызывается при загрузке плагина. Обязателен к реализации."""
        pass
    
    async def on_unload(self):
        """Вызывается при выгрузке плагина (опционально)."""
        pass
    
    # ========== HELPER МЕТОДЫ ==========
    
    async def emit_event(self, event_name: str, data: Dict[str, Any]):
        """
        Опубликовать событие в EventBus.
        
        Args:
            event_name: Имя события (будет префиксировано plugin.id)
            data: Данные события
        """
        full_event_name = f"{self.id}.{event_name}"
        await self.event_bus.emit(full_event_name, data)
    
    async def subscribe_event(self, event_pattern: str, handler):
        """
        Подписаться на события.
        
        Args:
            event_pattern: Паттерн события (например: "device.*" или "*.state_changed")
            handler: Async функция-обработчик(event_name: str, data: dict)
        """
        await self.event_bus.subscribe(event_pattern, handler)
    
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