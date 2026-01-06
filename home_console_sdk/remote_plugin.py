"""
Базовый класс для REMOTE SYSTEM PLUGINS для Home Console.

Этот модуль реализует HTTP контракт для удалённых плагинов, как определено в:
https://github.com/home-console/core-runtime-service/REMOTE_PLUGIN_CONTRACT.md

ИСПОЛЬЗОВАНИЕ:
- Remote plugin это независимый HTTP сервис (FastAPI, Flask, etc.)
- Реализует явные lifecycle endpoints
- Не требует Core Runtime в зависимостях
- Может быть на любом языке (Python SDK — вспомогательный инструмент)

ПРИМЕР:

    from fastapi import FastAPI
    from home_console_sdk.remote_plugin import RemotePluginBase
    import asyncio

    class MyMetricsPlugin(RemotePluginBase):
        name = "remote_metrics"
        version = "0.1.0"
        
        def __init__(self):
            super().__init__()
            # Регистрируем сервис
            self.register_service("metrics.report", "/metrics/report", "POST")
        
        async def on_load(self):
            print("Plugin loaded")
        
        async def on_start(self):
            print("Plugin started")
        
        async def on_stop(self):
            print("Plugin stopped")
    
    # Создаём FastAPI приложение и интегрируем плагин
    app = FastAPI()
    plugin = MyMetricsPlugin()
    
    @app.get("/plugin/metadata")
    async def get_metadata():
        return plugin.get_metadata()
    
    @app.post("/plugin/load")
    async def plugin_load():
        await plugin.on_load()
        return {"status": "ok"}
    
    # ... остальные endpoints
    
    @app.post("/metrics/report")
    async def report_metrics(request):
        body = await request.json()
        kwargs = body.get("kwargs", {})
        # обработка метрики
        return {"status": "ok"}
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


class RemotePluginBase(ABC):
    """
    Базовый класс для реализации контракта REMOTE SYSTEM PLUGIN.
    
    Контракт определяет:
    - Lifecycle HTTP endpoints (/plugin/{load,start,stop,unload,metadata,health})
    - Сервисные endpoints (зависит от плагина)
    - Формат данных (JSON с полями args/kwargs)
    - Гарантии идемпотентности
    
    Это не фреймворк, а контракт. SDK помогает:
    - Декларировать сервисы
    - Валидировать metadata
    - Документировать требования
    
    Реальная HTTP реализация (маршруты, сервер) — ответственность разработчика.
    """
    
    # Метаданные плагина (ДОЛЖНЫ быть переопределены)
    name: str = "unknown_plugin"
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    
    # Тип плагина (всегда "system" для контракта)
    type: str = "system"
    mode: str = "remote"
    
    def __init__(self):
        """
        Инициализация базового класса.
        
        Инициализирует:
        - Список сервисов (будет заполнен через register_service)
        - Внутреннее состояние (не управляется SDK, информационное)
        """
        self._services: List[Dict[str, str]] = []
        self._loaded: bool = False
        self._started: bool = False
    
    # ========== LIFECYCLE METHODS (ОБЯЗАТЕЛЬНЫ К РЕАЛИЗАЦИИ) ==========
    
    @abstractmethod
    async def on_load(self) -> None:
        """
        Инициализация плагина (вызывается из POST /plugin/load).
        
        КОНТРАКТ:
        - Должно быть ИДЕМПОТЕНТНО (вызов дважды не вызывает ошибку)
        - Должно подготовить ресурсы, но НЕ запускать фоновые задачи
        - Должно быстро вернуться (< 1 сек)
        - Может выбросить исключение (будет обработано proxy как 500)
        
        ОТВЕТСТВЕННОСТЬ ПЛАГИНА:
        - Проверить конфигурацию
        - Выделить ресурсы
        - Подготовить состояние
        
        НЕ НАДО:
        - Запускать background tasks
        - Открывать listening sockets (кроме HTTP самого плагина)
        - Обрабатывать внешние события
        """
        pass
    
    @abstractmethod
    async def on_start(self) -> None:
        """
        Запуск плагина (вызывается из POST /plugin/start).
        
        КОНТРАКТ:
        - Должно быть ИДЕМПОТЕНТНО
        - Должно активировать плагин (запустить background tasks, слушать события)
        - Вызывается ПОСЛЕ on_load()
        - Может выбросить исключение
        
        ОТВЕТСТВЕННОСТЬ ПЛАГИНА:
        - Запустить background workers
        - Подписаться на события
        - Начать обслуживать service endpoints
        
        ГАРАНТИЯ КОНТРАКТА:
        - Service endpoints должны быть доступны и обрабатывать вызовы
        """
        pass
    
    @abstractmethod
    async def on_stop(self) -> None:
        """
        Остановка плагина (вызывается из POST /plugin/stop).
        
        КОНТРАКТ:
        - Должно быть ИДЕМПОТЕНТНО
        - Должно прекратить обработку новых запросов
        - Должно позволить in-flight запросам завершиться
        - Должно быстро вернуться (< 5 сек)
        
        ОТВЕТСТВЕННОСТЬ ПЛАГИНА:
        - Остановить фоновые задачи
        - Отписаться от событий
        - Освободить временные ресурсы
        
        НЕ НАДО:
        - Закрывать постоянные соединения (БД, etc.)
        - Удалять состояние
        
        ПРИМЕЧАНИЕ:
        - После on_stop() может быть вызван on_start() снова (переводит в STARTED)
        """
        pass
    
    async def on_unload(self) -> None:
        """
        Выгрузка плагина (вызывается из POST /plugin/unload).
        
        КОНТРАКТ:
        - Должно быть ИДЕМПОТЕНТНО
        - Вызывается ПОСЛЕ on_stop()
        - Финальная очистка перед выходом процесса
        - Может выбросить исключение (логируется, но не блокирует)
        
        ОТВЕТСТВЕННОСТЬ ПЛАГИНА:
        - Закрыть все соединения (БД, файлы, etc.)
        - Флешить буферы
        - Очистить состояние
        
        НЕ НАДО:
        - Выполнять тяжёлые операции (на выходе всё равно процесс завершится)
        """
        pass
    
    async def health(self) -> Dict[str, Any]:
        """
        Проверка живости плагина (вызывается из GET /plugin/health).
        
        КОНТРАКТ (опциональный):
        - Должно вернуть JSON с полем "status"
        - Используется для диагностики
        - Может быть вызвано в любой момент
        
        DEFAULT РЕАЛИЗАЦИЯ:
        - Вернуть {"status": "ok", "loaded": True, "started": True}
        
        ПЕРЕОПРЕДЕЛЕНИЕ:
        - Плагин может переопределить для более детальной информации
        - Пример: добавить {"uptime": seconds, "requests_processed": count}
        """
        return {
            "status": "ok",
            "loaded": self._loaded,
            "started": self._started,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # ========== SERVICE REGISTRATION ==========
    
    def register_service(
        self,
        name: str,
        endpoint: str,
        method: str = "POST",
        description: str = "",
    ) -> None:
        """
        Зарегистрировать сервис, который предоставляет этот плагин.
        
        КОНТРАКТ:
        - Вызывается в __init__() или на этапе конфигурации (до on_load)
        - Сервисы передаются в metadata и используются proxy для регистрации в Core
        - Каждый сервис должен иметь соответствующий HTTP endpoint
        
        ПАРАМЕТРЫ:
        name (str): Имя сервиса в ServiceRegistry (например, "metrics.report")
                    Должно быть уникально в пределах Core Runtime
                    Формат: "namespace.action"
        
        endpoint (str): Относительный HTTP endpoint (например, "/metrics/report")
                        Proxy будет делать запросы на {base_url}{endpoint}
        
        method (str): HTTP метод ("GET" или "POST")
                      GET: сервис не требует параметров (информационный)
                      POST: сервис получает параметры через body
        
        description (str): Опциональное описание для документации
        
        ПРИМЕРЫ:
        
        # Логирование — просто POST
        self.register_service(
            "logger.log",
            "/logger/log",
            "POST",
            "Send log message"
        )
        
        # Метрики — с параметрами
        self.register_service(
            "metrics.report",
            "/metrics/report",
            "POST",
            "Report metric value with tags"
        )
        
        # Информационный endpoint — GET
        self.register_service(
            "metrics.dump",
            "/metrics/dump",
            "GET",
            "Dump all metrics"
        )
        
        ВАЛИДАЦИЯ:
        - Проверяет что endpoint начинается с /
        - Проверяет что method в ["GET", "POST"]
        - При нарушении вызывает ValueError
        
        ПРИМЕЧАНИЕ:
        - Реальная HTTP реализация — в развёрнутом плагине
        - SDK только хранит метаданные и помогает их валидировать
        - Proxy генерирует форвардеры на основе этих метаданных
        """
        if not endpoint.startswith("/"):
            raise ValueError(f"endpoint должен начинаться с /: {endpoint}")
        
        if method.upper() not in ["GET", "POST"]:
            raise ValueError(f"method должен быть GET или POST: {method}")
        
        service = {
            "name": name,
            "endpoint": endpoint,
            "method": method.upper(),
        }
        
        if description:
            service["description"] = description
        
        self._services.append(service)
    
    # ========== METADATA GENERATION ==========
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Вернуть метаданные плагина для отправки в GET /plugin/metadata.
        
        КОНТРАКТ:
        - Вызывается из HTTP handler для GET /plugin/metadata
        - Вернуть JSON с полями:
          * name (str): идентификатор плагина
          * type (str): "system"
          * mode (str): "remote"
          * version (str): версия плагина
          * description (str): описание
          * author (str): автор
          * services (list): зарегистрированные сервисы
        
        ПРИМЕЧАНИЕ:
        - Proxy прочитает это один раз при on_load()
        - Используется для регистрации сервисов в ServiceRegistry
        
        ВАЛИДАЦИЯ:
        - Все поля должны быть JSON-serializable
        - services должны быть list с dict'ами (name, endpoint, method)
        
        ПРИМЕР ВОЗВРАТА:
        {
            "name": "remote_metrics",
            "type": "system",
            "mode": "remote",
            "version": "0.1.0",
            "description": "Удалённый сборщик метрик",
            "author": "Home Console",
            "services": [
                {"name": "metrics.report", "endpoint": "/metrics/report", "method": "POST"},
                {"name": "metrics.dump", "endpoint": "/metrics/dump", "method": "GET"}
            ]
        }
        """
        return {
            "name": self.name,
            "type": self.type,
            "mode": self.mode,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "services": self._services,
        }
    
    # ========== VALIDATION ==========
    
    def validate_metadata(self) -> List[str]:
        """
        Валидировать метаданные плагина.
        
        Возвращает список ошибок (пустой список = OK).
        
        ПРОВЕРЯЕТ:
        - name не пусто и не "unknown_plugin"
        - version валидный семантический версион (X.Y.Z)
        - services не null, each service has name/endpoint/method
        - endpoint начинается с /
        - method in ["GET", "POST"]
        
        ПРИМЕЧАНИЕ:
        - Используйте перед развёртыванием для отладки
        - Proxy использует более мягкую валидацию (не блокирует)
        
        ПРИМЕР:
        errors = plugin.validate_metadata()
        if errors:
            for error in errors:
                print(f"Validation error: {error}")
            exit(1)
        """
        errors = []
        
        if not self.name or self.name == "unknown_plugin":
            errors.append("Plugin name is not set or is default")
        
        # Проверяем версию (простая валидация)
        if self.version and self.version.count(".") < 2:
            errors.append(f"Version should be X.Y.Z format: {self.version}")
        
        if not isinstance(self._services, list):
            errors.append("services must be a list")
        else:
            for i, svc in enumerate(self._services):
                if not isinstance(svc, dict):
                    errors.append(f"Service {i} is not a dict")
                    continue
                
                if "name" not in svc:
                    errors.append(f"Service {i} missing 'name'")
                if "endpoint" not in svc:
                    errors.append(f"Service {i} missing 'endpoint'")
                if "method" not in svc:
                    errors.append(f"Service {i} missing 'method'")
                
                if "endpoint" in svc and not svc["endpoint"].startswith("/"):
                    errors.append(f"Service {i} endpoint should start with /: {svc['endpoint']}")
                
                if "method" in svc and svc["method"] not in ["GET", "POST"]:
                    errors.append(f"Service {i} method should be GET or POST: {svc['method']}")
        
        return errors


# Функция-помощник для создания HTTP handlers
def create_lifecycle_handlers(plugin: RemotePluginBase) -> Dict[str, Any]:
    """
    Создать готовые HTTP handlers для lifecycle endpoints.
    
    Это вспомогательная функция для быстрого монтирования endpoints.
    
    ВОЗВРАЩАЕТ:
    Dict с ключами:
    - "metadata": async handler для GET /plugin/metadata
    - "health": async handler для GET /plugin/health
    - "load": async handler для POST /plugin/load
    - "start": async handler для POST /plugin/start
    - "stop": async handler для POST /plugin/stop
    - "unload": async handler для POST /plugin/unload
    
    ИСПОЛЬЗОВАНИЕ (FastAPI):
    
        from fastapi import FastAPI
        from home_console_sdk.remote_plugin import RemotePluginBase, create_lifecycle_handlers
        
        class MyPlugin(RemotePluginBase):
            ...
        
        app = FastAPI()
        plugin = MyPlugin()
        handlers = create_lifecycle_handlers(plugin)
        
        app.add_api_route("/plugin/metadata", handlers["metadata"], methods=["GET"])
        app.add_api_route("/plugin/health", handlers["health"], methods=["GET"])
        app.add_api_route("/plugin/load", handlers["load"], methods=["POST"])
        app.add_api_route("/plugin/start", handlers["start"], methods=["POST"])
        app.add_api_route("/plugin/stop", handlers["stop"], methods=["POST"])
        app.add_api_route("/plugin/unload", handlers["unload"], methods=["POST"])
    
    ПРИМЕЧАНИЕ:
    - Handlers оборачивают методы плагина и обрабатывают исключения
    - Все возвращают JSON с полем "status"
    - При ошибке вернут 500 с деталями
    """
    
    async def metadata_handler():
        return plugin.get_metadata()
    
    async def health_handler():
        return await plugin.health()
    
    async def load_handler():
        try:
            await plugin.on_load()
            plugin._loaded = True
            return {"status": "ok", "message": "plugin loaded"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def start_handler():
        try:
            await plugin.on_start()
            plugin._started = True
            return {"status": "ok", "message": "plugin started"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def stop_handler():
        try:
            await plugin.on_stop()
            plugin._started = False
            return {"status": "ok", "message": "plugin stopped"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def unload_handler():
        try:
            await plugin.on_unload()
            plugin._loaded = False
            plugin._started = False
            return {"status": "ok", "message": "plugin unloaded"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    return {
        "metadata": metadata_handler,
        "health": health_handler,
        "load": load_handler,
        "start": start_handler,
        "stop": stop_handler,
        "unload": unload_handler,
    }
