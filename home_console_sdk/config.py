"""
Configuration management for plugins
"""

from typing import Optional, Any, Dict, Type, TypeVar, get_type_hints
from pydantic import BaseModel, ValidationError, Field
import os
import json
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class PluginConfig:
    """Класс для работы с конфигурацией плагина"""
    
    def __init__(self, plugin_id: str):
        """
        Args:
            plugin_id: ID плагина
        """
        self.plugin_id = plugin_id
        self._prefix = f"PLUGIN_{plugin_id.upper().replace('-', '_')}_"
        self._config_cache: Dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None, cast: Optional[Type] = None) -> Any:
        """
        Получить значение конфигурации из переменной окружения
        
        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию
            cast: Тип для приведения значения (int, bool, float, list, dict)
            
        Returns:
            Значение конфигурации
            
        Пример:
            config.get("API_KEY", "default-key")
            config.get("PORT", 8080, cast=int)
            config.get("DEBUG", False, cast=bool)
        """
        env_key = f"{self._prefix}{key.upper()}"

        # Try prefixed env var first (PLUGIN_{PLUGIN_ID}_{KEY}),
        # then plain KEY as provided, then KEY uppercased, then default.
        value = os.getenv(env_key)
        if value is None:
            # try as-given key
            value = os.getenv(key)
        if value is None:
            # try uppercased key
            value = os.getenv(key.upper())
        if value is None:
            value = default

        if cast and value is not None:
            try:
                if cast == bool:
                    return str(value).lower() in ('true', '1', 'yes', 'on')
                elif cast == list or cast == dict:
                    return json.loads(value) if isinstance(value, str) else value
                else:
                    return cast(value)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to cast {env_key}={value} to {cast}: {e}")
                return default
        
        return value
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Получить целочисленное значение"""
        return self.get(key, default, cast=int)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Получить булево значение"""
        return self.get(key, default, cast=bool)
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Получить значение с плавающей точкой"""
        return self.get(key, default, cast=float)
    
    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """Получить список"""
        return self.get(key, default or [], cast=list)
    
    def get_dict(self, key: str, default: Optional[dict] = None) -> dict:
        """Получить словарь"""
        return self.get(key, default or {}, cast=dict)
    
    def require(self, key: str, cast: Optional[Type] = None) -> Any:
        """
        Получить обязательное значение конфигурации
        
        Args:
            key: Ключ конфигурации
            cast: Тип для приведения значения
            
        Returns:
            Значение конфигурации
            
        Raises:
            ValueError: Если значение не найдено
        """
        value = self.get(key, cast=cast)
        if value is None:
            raise ValueError(
                f"Required configuration {self._prefix}{key.upper()} is not set"
            )
        return value
    
    def load_from_model(self, model_class: Type[T]) -> T:
        """
        Загрузить конфигурацию из Pydantic модели
        
        Args:
            model_class: Pydantic BaseModel класс
            
        Returns:
            Экземпляр модели с загруженной конфигурацией
            
        Raises:
            ValidationError: Если конфигурация невалидна
            
        Пример:
            class MyPluginConfig(BaseModel):
                api_key: str
                port: int = 8080
                debug: bool = False
            
            config = plugin_config.load_from_model(MyPluginConfig)
            print(config.api_key)
        """
        config_data = {}
        
        # Получаем все поля из модели
        hints = get_type_hints(model_class)
        for field_name, field_type in hints.items():
            # Пропускаем приватные поля
            if field_name.startswith('_'):
                continue
            
            # Получаем значение из env
            env_value = self.get(field_name)
            if env_value is not None:
                config_data[field_name] = env_value
        
        # Валидируем и создаем экземпляр модели
        try:
            return model_class(**config_data)
        except ValidationError as e:
            logger.error(f"Configuration validation failed for {self.plugin_id}: {e}")
            raise
    
    def set_cache(self, key: str, value: Any):
        """Сохранить значение в кэш"""
        self._config_cache[key] = value
    
    def get_cache(self, key: str, default: Any = None) -> Any:
        """Получить значение из кэша"""
        return self._config_cache.get(key, default)
    
    def clear_cache(self):
        """Очистить кэш"""
        self._config_cache.clear()
