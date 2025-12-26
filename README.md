# Home Console SDK (Python)

SDK для разработки плагинов для Home Console платформы.

This SDK can be installed locally for development or published to a registry.

Quick setup (development):

```bash
cd sdk/python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Для production

```bash
pip install home-console-sdk
```

## 🚀 Быстрый старт

### Создание плагина

```python
from home_console_sdk import InternalPluginBase
from fastapi import APIRouter

class MyPlugin(InternalPluginBase):
    id = "my_plugin"
    name = "My Plugin"
    version = "1.0.0"
    
    async def on_load(self):
        # Используем Dependency Injection для моделей
        Device = self.models.get('Device')
        
        # Группируем endpoints
        api_router = APIRouter(prefix="/api", tags=["my-plugin"])
        api_router.add_api_route("/status", self.get_status, methods=["GET"])
        
        self.router = api_router
        self.logger.info("✅ Plugin loaded")
```

### Инфраструктурный плагин

Для плагинов, которые должны монтироваться на `/api` без префикса:

```python
class InfraPlugin(InternalPluginBase):
    id = "my_infra_plugin"
    infrastructure = True  # Маркируем как инфраструктурный
```

**Или через plugin.json:**

```json
{
  "id": "my_infra_plugin",
  "infrastructure": true
}
```

## 📚 Документация

- [DEV_SETUP.md](./DEV_SETUP.md) - Установка для разработки
- [OAUTH_INTEGRATION.md](./OAUTH_INTEGRATION.md) - OAuth интеграция
- [CHANGELOG.md](./CHANGELOG.md) - История изменений
- [MIGRATION.md](./MIGRATION.md) - Миграция с предыдущих версий
- [examples.py](./examples.py) - Примеры использования

## ✨ Возможности SDK v0.0.2

### 1. Dependency Injection моделей

```python
# ❌ Больше не нужно!
# from ...models import Device

# ✅ Используйте DI
Device = self.models.get('Device')
```

### 2. Автоматическое управление роутами

```python
# SDK автоматически вызывает:
await plugin.mount_router()    # После on_load()
await plugin.unmount_router()  # При выгрузке
```

### 3. Группировка endpoints

```python
auth_router = APIRouter(prefix="/auth")
devices_router = APIRouter(prefix="/devices")

self.router = APIRouter()
self.router.include_router(auth_router)
self.router.include_router(devices_router)
```

## 📚 Документация

### Типы плагинов

SDK поддерживает два типа плагинов:

1. **InternalPluginBase** — Встроенные плагины (загружаются в core-service)
2. **PluginBase** — Внешние плагины (микросервисы, HTTP API)

### Пример встроенного плагина

```python
from home_console_sdk import InternalPluginBase
from fastapi import APIRouter

class MyPlugin(InternalPluginBase):
    id = "my-plugin"
    name = "My Plugin"
    version = "1.0.0"
    description = "Мой первый плагин"
    
    async def on_load(self):
        """Инициализация при загрузке"""
        self.logger.info("Plugin loaded!")
        
        # Создание API endpoints
        self.router = APIRouter()
        self.router.add_api_route("/hello", self.hello, methods=["GET"])
        
        # Подписка на события
        await self.subscribe_event("device.*", self.on_device_event)
        
        # Фоновая задача
        self.tasks.add_task("sync", self.sync_data, interval=60.0)
        
        # Работа с БД
        results = await self.db.query("SELECT * FROM my_plugin_devices")
        
        # Конфигурация
        api_key = self.config.require("API_KEY")
        debug = self.config.get_bool("DEBUG", False)
    
    async def hello(self):
        return {"message": "Hello from plugin!"}
    
    async def on_device_event(self, event_name: str, data: dict):
        self.logger.info(f"Device event: {event_name}")
        
        # Отправить событие
        await self.emit_event("processed", {"original": event_name})
    
    async def sync_data(self):
        """Периодическая синхронизация"""
        self.logger.info("Syncing data...")
    
    async def on_unload(self):
        """Cleanup при выгрузке"""
        self.tasks.stop_all()
```

### Пример внешнего плагина (микросервис)

```python
from home_console_sdk import PluginBase

class ExternalPlugin(PluginBase):
    id = "external-plugin"
    name = "External Plugin"
    version = "1.0.0"
    
    async def on_start(self):
        """Запуск плагина"""
        # Получаем устройства через Core API
        devices = await self.core.list_devices()
        self.logger.info(f"Found {len(devices)} devices")
        
        # Создаем устройство
        from home_console_sdk import DeviceCreate
        device = await self.core.create_device(
            DeviceCreate(name="My Device", type="sensor")
        )
    
    async def handle_event(self, event_name: str, data: dict):
        """Обработка событий от Core"""
        self.logger.info(f"Event: {event_name}")

# Запуск
if __name__ == "__main__":
    import asyncio
    plugin = ExternalPlugin()
    asyncio.run(plugin.run())
```

## 🔧 Возможности SDK

### DatabaseClient — Работа с БД

```python
# Доступен через self.db в InternalPluginBase

# SELECT запрос
results = await self.db.query(
    "SELECT * FROM my_plugin_users WHERE active = :active",
    {"active": True}
)

# INSERT/UPDATE/DELETE
await self.db.execute(
    "INSERT INTO my_plugin_logs (message) VALUES (:msg)",
    {"msg": "Hello"}
)

# Регистрация SQLAlchemy модели
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MyModel(Base):
    __tablename__ = "data"  # Будет создана как "my_plugin_data"
    id = Column(Integer, primary_key=True)
    name = Column(String)

await self.db.register_model(MyModel)
```

### EventsClient — События

```python
# Доступен через self.events

# Отправить событие
await self.events.emit("user_created", {"user_id": 123})

# Подписаться на события
await self.events.subscribe("device.*", self.handle_device_event)

# Декоратор
@self.events.on("device.state_changed")
async def on_state_change(event_name: str, data: dict):
    print(f"State changed: {data}")
```

### PluginConfig — Конфигурация

```python
# Доступен через self.config

# Простое получение
api_key = self.config.get("API_KEY", "default")
port = self.config.get_int("PORT", 8080)
debug = self.config.get_bool("DEBUG", False)

# Обязательное значение
token = self.config.require("TOKEN")  # Выбросит ValueError если нет

# Pydantic модели
from pydantic import BaseModel

class MyConfig(BaseModel):
    api_key: str
    timeout: int = 30
    enabled: bool = True

config = self.config.load_from_model(MyConfig)
print(config.api_key)
```

Переменные окружения: `PLUGIN_<PLUGIN_ID>_<KEY>`  
Например: `PLUGIN_MY_PLUGIN_API_KEY=secret123`

### TaskManager — Фоновые задачи

```python
# Доступен через self.tasks

# Периодическая задача
async def sync():
    print("Syncing...")

self.tasks.add_task("sync", sync, interval=60.0)  # Каждые 60 сек

# Однократно с задержкой
self.tasks.schedule_once("cleanup", cleanup_func, delay=10.0)

# В конкретное время
from datetime import datetime, timedelta
run_at = datetime.now() + timedelta(hours=1)
self.tasks.schedule_at("report", generate_report, run_at)

# Остановить все задачи
self.tasks.stop_all()
```

### PluginAuth — Аутентификация

```python
from home_console_sdk import require_api_key, require_bearer_token

# В роутере
@self.router.get("/private")
async def private_endpoint(auth: bool = Depends(require_api_key(self.id))):
    return {"message": "Access granted"}

@self.router.get("/secure")
async def secure(token: str = Depends(require_bearer_token(self.id))):
    return {"token": token}
```

Переменная окружения: `PLUGIN_<PLUGIN_ID>_API_KEY`

## 🧪 Тестирование SDK

Создайте тестовый скрипт:

```python
from home_console_sdk import CoreAPIClient
import asyncio

async def test():
    client = CoreAPIClient("http://localhost:8000")
    await client.login("admin", "password")
    
    devices = await client.list_devices()
    print(f"Devices: {devices}")
    
    await client.close()

asyncio.run(test())
```

## 📖 Дополнительно

### Зависимости

SDK требует:
- Python >= 3.11
- httpx >= 0.25.0
- pydantic >= 2.5.0
- sqlalchemy >= 2.0 (опционально, для DatabaseClient)
- fastapi (опционально, для InternalPluginBase)

### Структура SDK

```
home_console_sdk/
├── __init__.py          # Экспорты
├── plugin.py            # PluginBase, InternalPluginBase
├── client.py            # CoreAPIClient (HTTP)
├── db.py                # DatabaseClient
├── events.py            # EventsClient
├── config.py            # PluginConfig
├── tasks.py             # TaskManager, BackgroundTask
├── auth.py              # PluginAuth
├── models.py            # Pydantic модели
└── exceptions.py        # Исключения
```

- `setup.py` contains `install_requires` and is the canonical list for packaging.
- `requirements.txt` is useful for local development and test runners — keep it in sync with `install_requires`.
- `dev-requirements.txt` contains build/test tools (`build`, `twine`, `pytest`).

Versioning and publishing

- Use semantic tags like `v0.0.1`, `v0.0.2` and push tags to trigger CI.
- Registries normally prevent re-uploading the same version. Bump the version in `setup.py` before re-tagging.

Testing examples

Create a small script in another project to import and call the SDK:

```python
from smarthome_sdk import CoreAPIClient
import asyncio

async def main():
		async with CoreAPIClient("http://localhost:8000") as c:
				# use client
				pass

asyncio.run(main())
```

If you want, I can add a tiny `examples/test_project` that demonstrates `-e ../sdk/python` install and a simple test script.
