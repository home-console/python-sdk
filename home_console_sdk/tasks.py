"""
Background tasks and scheduled jobs for plugins
"""

from typing import Callable, Optional, Awaitable, Any
import asyncio
import logging
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class BackgroundTask:
    """Wrapper для фоновой задачи"""
    
    def __init__(
        self, 
        func: Callable[..., Awaitable[Any]], 
        name: str,
        interval: Optional[float] = None,
        *args, 
        **kwargs
    ):
        """
        Args:
            func: Async функция для выполнения
            name: Имя задачи
            interval: Интервал повтора в секундах (None = однократно)
            args: Позиционные аргументы для функции
            kwargs: Именованные аргументы для функции
        """
        self.func = func
        self.name = name
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def run(self):
        """Запустить задачу"""
        self._running = True
        try:
            while self._running:
                try:
                    await self.func(*self.args, **self.kwargs)
                except Exception as e:
                    logger.error(f"Error in background task {self.name}: {e}", exc_info=True)
                
                if self.interval is None or not self._running:
                    break
                
                await asyncio.sleep(self.interval)
        finally:
            self._running = False
    
    def start(self):
        """Запустить задачу в фоне"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())
            logger.info(f"Started background task: {self.name}")
    
    def stop(self):
        """Остановить задачу"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info(f"Stopped background task: {self.name}")
    
    def is_running(self) -> bool:
        """Проверить запущена ли задача"""
        return self._running and self._task is not None and not self._task.done()


class TaskManager:
    """Менеджер фоновых задач для плагина"""
    
    def __init__(self, plugin_id: str):
        """
        Args:
            plugin_id: ID плагина
        """
        self.plugin_id = plugin_id
        self._tasks: dict[str, BackgroundTask] = {}
    
    def add_task(
        self, 
        name: str, 
        func: Callable[..., Awaitable[Any]], 
        interval: Optional[float] = None,
        *args,
        **kwargs
    ) -> BackgroundTask:
        """
        Добавить и запустить фоновую задачу
        
        Args:
            name: Имя задачи
            func: Async функция для выполнения
            interval: Интервал повтора в секундах (None = однократно)
            args: Позиционные аргументы
            kwargs: Именованные аргументы
            
        Returns:
            BackgroundTask объект
            
        Пример:
            async def sync_devices():
                print("Syncing devices...")
            
            task_manager.add_task("sync", sync_devices, interval=60.0)
        """
        task = BackgroundTask(func, name, interval, *args, **kwargs)
        self._tasks[name] = task
        task.start()
        return task
    
    def remove_task(self, name: str):
        """
        Остановить и удалить задачу
        
        Args:
            name: Имя задачи
        """
        task = self._tasks.pop(name, None)
        if task:
            task.stop()
    
    def get_task(self, name: str) -> Optional[BackgroundTask]:
        """Получить задачу по имени"""
        return self._tasks.get(name)
    
    def stop_all(self):
        """Остановить все задачи"""
        for task in self._tasks.values():
            task.stop()
        self._tasks.clear()
    
    def schedule_once(
        self, 
        name: str, 
        func: Callable[..., Awaitable[Any]], 
        delay: float,
        *args,
        **kwargs
    ):
        """
        Запланировать однократное выполнение через delay секунд
        
        Args:
            name: Имя задачи
            func: Async функция
            delay: Задержка в секундах
            args: Позиционные аргументы
            kwargs: Именованные аргументы
        """
        async def delayed_task():
            await asyncio.sleep(delay)
            await func(*args, **kwargs)
        
        self.add_task(name, delayed_task, interval=None)
    
    def schedule_at(
        self,
        name: str,
        func: Callable[..., Awaitable[Any]],
        at_time: datetime,
        *args,
        **kwargs
    ):
        """
        Запланировать выполнение в конкретное время
        
        Args:
            name: Имя задачи
            func: Async функция
            at_time: Время выполнения
            args: Позиционные аргументы
            kwargs: Именованные аргументы
        """
        delay = (at_time - datetime.now()).total_seconds()
        if delay < 0:
            logger.warning(f"Task {name} scheduled in the past, executing immediately")
            delay = 0
        
        self.schedule_once(name, func, delay, *args, **kwargs)


def background_task(interval: Optional[float] = None):
    """
    Декоратор для создания фоновой задачи
    
    Args:
        interval: Интервал повтора в секундах (None = однократно)
        
    Пример:
        @background_task(interval=60.0)
        async def sync_task():
            print("Running sync...")
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if interval:
                while True:
                    await func(*args, **kwargs)
                    await asyncio.sleep(interval)
            else:
                await func(*args, **kwargs)
        
        # Type ignore для динамических атрибутов
        wrapper._is_background_task = True  # type: ignore
        wrapper._interval = interval  # type: ignore
        return wrapper
    
    return decorator


def schedule(interval: float):
    """
    Декоратор для периодических задач (alias для background_task)
    
    Args:
        interval: Интервал в секундах
        
    Пример:
        @schedule(interval=300)  # Каждые 5 минут
        async def cleanup():
            print("Cleaning up...")
    """
    return background_task(interval=interval)
