"""
Plugin base classes for HomeConsole plugins.

BasePlugin    — встраиваемые плагины (загружаются в core-runtime-service).
               Используй это для всех плагинов в каталоге.

PluginBase    — внешние плагины-микросервисы (отдельный процесс/контейнер).
               Общаются с core по HTTP. Для большинства плагинов не нужен.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# PluginMetadata — публичный контракт метаданных (frozen, никакой логики)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PluginMetadata:
    """
    Метаданные плагина. Объявляются плагином, читаются core.

    Пример:
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="my_plugin",
                version="1.0.0",
                description="My plugin",
            )
    """
    name: str
    version: str
    description: str | None = None
    is_integration: bool = False
    integration_flags: list[str] = field(default_factory=list)
    capabilities_provided: list[str] = field(default_factory=list)
    capabilities_required: list[str] = field(default_factory=list)
    dynamic_service_registration: bool = False


# ---------------------------------------------------------------------------
# PluginRuntime — opaque Protocol. Реальный объект приходит от core.
# Используется только для type hints в плагинах.
# ---------------------------------------------------------------------------

@runtime_checkable
class PluginRuntime(Protocol):
    """Среда выполнения плагина. Предоставляется core, не создаётся плагином."""

    async def register_service(self, name: str, handler: Any) -> None: ...
    async def call_service(self, name: str, payload: Any = None) -> Any: ...
    async def publish_event(self, event_type: str, payload: Any = None) -> None: ...
    async def subscribe_event(self, event_type: str, handler: Any) -> None: ...


# ---------------------------------------------------------------------------
# BasePlugin — контракт для встраиваемых плагинов
# ---------------------------------------------------------------------------

class BasePlugin(ABC):
    """
    Базовый класс для плагинов HomeConsole.

    Lifecycle (вызывает только core, не плагин):
        on_load  → on_start → (работает) → on_stop → on_unload

    Минимальный плагин:

        from home_console_sdk import BasePlugin, PluginMetadata

        class MyPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name="my_plugin", version="1.0.0")

            async def on_load(self) -> None:
                await self.runtime.register_service("my_plugin.ping", self._ping)

            async def _ping(self, payload=None):
                return {"ok": True}
    """

    def __init__(self, runtime: Optional[PluginRuntime] = None) -> None:
        self._runtime: Optional[PluginRuntime] = runtime

    @property
    def runtime(self) -> PluginRuntime:
        """Среда выполнения. Гарантированно доступна в on_load/on_start/on_stop/on_unload."""
        if self._runtime is None:
            raise RuntimeError(
                "Plugin runtime not set. "
                "Do not call runtime before on_load — core sets it automatically."
            )
        return self._runtime

    @runtime.setter
    def runtime(self, value: Optional[PluginRuntime]) -> None:
        self._runtime = value

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Метаданные плагина. Обязательны к реализации."""
        ...

    async def on_load(self) -> None:
        """Регистрация сервисов, capabilities, операций. Вызывается core при загрузке."""

    async def on_start(self) -> None:
        """Фоновые задачи, подписки на события. Вызывается core при запуске."""

    async def on_stop(self) -> None:
        """Отмена фоновых задач. Вызывается core при остановке."""

    async def on_unload(self) -> None:
        """Очистка ресурсов. Вызывается core при выгрузке."""


# ---------------------------------------------------------------------------
# PluginBase — для внешних плагинов-микросервисов (отдельный процесс)
# ---------------------------------------------------------------------------

class PluginBase(ABC):
    """
    Базовый класс для ВНЕШНИХ плагинов (микросервисы, отдельные контейнеры).
    Общаются с core через HTTP API.
    Для плагинов в каталоге используй BasePlugin.
    """

    id: str = "unknown"
    name: str = "Unknown Plugin"
    version: str = "1.0.0"
    description: str = ""

    @abstractmethod
    async def on_start(self) -> None: ...

    async def on_stop(self) -> None: ...

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "version": self.version}


# ---------------------------------------------------------------------------
# InternalPluginBase — устаревший alias, оставлен для обратной совместимости
# ---------------------------------------------------------------------------

class InternalPluginBase(BasePlugin, ABC):
    """
    Устарел. Используй BasePlugin напрямую.
    Оставлен только для совместимости со старым кодом.
    """

    # Старые атрибуты — для совместимости
    id: str = "unknown"
    name: str = "Unknown Plugin"
    version: str = "1.0.0"
    description: str = ""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.id,
            version=self.version,
            description=self.description,
        )

    async def on_load(self) -> None: ...
