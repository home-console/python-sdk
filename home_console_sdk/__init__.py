# Core plugin contract — главный публичный API
from .plugin import BasePlugin, PluginMetadata, PluginRuntime, PluginBase, InternalPluginBase
from .exceptions import (
    HomeConsoleSDKError,
    AuthenticationError,
    APIError,
    NotFoundError,
    ValidationError,
)

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

__all__ = [
    # Основной контракт плагина
    "BasePlugin",
    "PluginMetadata",
    "PluginRuntime",
    # Внешние плагины-микросервисы
    "PluginBase",
    # Совместимость со старым кодом
    "InternalPluginBase",
    # Исключения
    "HomeConsoleSDKError",
    "AuthenticationError",
    "APIError",
    "NotFoundError",
    "ValidationError",
]

# Backwards-compat alias
SmartHomeSDKError = HomeConsoleSDKError
__all__.append("SmartHomeSDKError")
