from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .client import CoreAPIClient
import logging
import os

class PluginBase(ABC):
    """
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
