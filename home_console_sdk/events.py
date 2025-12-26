from typing import Callable, Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EventsClient:
    """Клиент для работы с событиями"""
    
    def __init__(self, plugin_id: str, event_bus: Any):
        """
        Args:
            plugin_id: ID плагина
            event_bus: EventBus из core-service
        """
        self.plugin_id = plugin_id
        self._event_bus = event_bus
        self._handlers: Dict[str, List[Callable]] = {}
    
    async def emit(self, event_name: str, data: Optional[Dict[str, Any]] = None):
        """
        Опубликовать событие
        
        Args:
            event_name: Имя события (будет автоматически добавлен префикс plugin_id)
            data: Данные события
        """
        full_event_name = f"{self.plugin_id}.{event_name}"
        await self._event_bus.emit(full_event_name, data or {})
        logger.debug(f"Event emitted: {full_event_name}")
    
    async def subscribe(self, event_pattern: str, handler: Callable):
        """
        Подписаться на события
        
        Args:
            event_pattern: Паттерн события (например: "device.*" или "*.state_changed")
            handler: Async функция-обработчик(event_name: str, data: dict)
        """
        await self._event_bus.subscribe(event_pattern, handler)
        self._handlers.setdefault(event_pattern, []).append(handler)
        logger.debug(f"Subscribed to pattern: {event_pattern}")
    
    def on(self, event_name: str):
        """
        Декоратор для подписки на событие
        
        Пример:
            @events.on("device.created")
            async def handle_device_created(event_name: str, data: dict):
                print(f"Device created: {data}")
        """
        def decorator(func: Callable):
            self._handlers.setdefault(event_name, []).append(func)
            return func
        return decorator
    
    async def unsubscribe(self, event_pattern: str, handler: Optional[Callable] = None):
        """
        Отписаться от событий
        
        Args:
            event_pattern: Паттерн события
            handler: Конкретный обработчик (если None - отписаться от всех)
        """
        if handler:
            handlers = self._handlers.get(event_pattern, [])
            if handler in handlers:
                handlers.remove(handler)
                await self._event_bus.unsubscribe(event_pattern, handler)
        else:
            # Отписаться от всех обработчиков данного паттерна
            handlers = self._handlers.pop(event_pattern, [])
            for h in handlers:
                await self._event_bus.unsubscribe(event_pattern, h)
        
        logger.debug(f"Unsubscribed from pattern: {event_pattern}")