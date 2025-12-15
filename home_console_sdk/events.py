from typing import Callable, Dict, List

class EventsClient:
    """Клиент для работы с событиями"""
    
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._handlers: Dict[str, List[Callable]] = {}
    
    async def emit(self, event_name: str, **data):
        """Опубликовать событие"""
        full_event_name = f"{self.plugin_id}.{event_name}"
        await self._event_bus.publish(full_event_name, data)
    
    def on(self, event_name: str):
        """Декоратор для подписки на событие"""
        def decorator(func: Callable):
            self._handlers.setdefault(event_name, []).append(func)
            return func
        return decorator