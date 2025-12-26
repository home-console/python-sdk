"""
Примеры использования Home Console SDK
"""

from home_console_sdk import (
    InternalPluginBase,
    PluginBase,
    CoreAPIClient,
    DeviceCreate,
    PluginConfig,
    TaskManager,
    background_task,
    schedule,
    require_api_key,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
import asyncio


# ============= ПРИМЕР 1: Встроенный плагин =============

class WeatherPlugin(InternalPluginBase):
    """Плагин для работы с погодой"""
    
    id = "weather"
    name = "Weather Plugin"
    version = "1.0.0"
    description = "Интеграция с погодными сервисами"
    
    async def on_load(self):
        """Инициализация плагина"""
        self.logger.info("🌤️ Weather plugin loading...")
        
        # 1. Конфигурация
        self.api_key = self.config.require("API_KEY")
        self.update_interval = self.config.get_int("UPDATE_INTERVAL", 300)
        
        # 2. Регистрация БД модели
        Base = declarative_base()
        
        class WeatherCache(Base):
            __tablename__ = "cache"
            id = Column(Integer, primary_key=True)
            city = Column(String)
            temperature = Column(Integer)
            updated = Column(String)
        
        await self.db.register_model(WeatherCache)
        
        # 3. API endpoints
        self.router = APIRouter()
        self.router.add_api_route(
            "/current/{city}",
            self.get_weather,
            methods=["GET"]
        )
        
        # 4. Подписка на события
        await self.subscribe_event("automation.*", self.handle_automation)
        
        # 5. Фоновые задачи
        self.tasks.add_task(
            "update_weather",
            self.update_weather,
            interval=self.update_interval
        )
        
        self.logger.info("✅ Weather plugin loaded")
    
    async def get_weather(self, city: str):
        """API endpoint для получения погоды"""
        # Проверяем кэш
        results = await self.db.query(
            "SELECT * FROM weather_cache WHERE city = :city",
            {"city": city}
        )
        
        if results:
            return results[0]
        
        # Получаем данные (имитация)
        weather = {"city": city, "temperature": 22, "condition": "sunny"}
        
        # Сохраняем в БД
        await self.db.execute(
            "INSERT INTO weather_cache (city, temperature) VALUES (:city, :temp)",
            {"city": city, "temp": weather["temperature"]}
        )
        
        return weather
    
    async def handle_automation(self, event_name: str, data: dict):
        """Обработчик событий автоматизации"""
        self.logger.info(f"Automation event: {event_name}")
        
        # Проверяем температуру и отправляем уведомление
        if data.get("type") == "check_temperature":
            weather = await self.get_weather(data["city"])
            
            if weather["temperature"] > 30:
                await self.emit_event("hot_weather_alert", {
                    "city": data["city"],
                    "temperature": weather["temperature"]
                })
    
    async def update_weather(self):
        """Периодическое обновление погоды"""
        self.logger.debug("Updating weather cache...")
        # Обновление кэша...
    
    async def on_unload(self):
        """Cleanup"""
        self.tasks.stop_all()
        await self.db.close()


# ============= ПРИМЕР 2: Внешний плагин (микросервис) =============

class TelegramBotPlugin(PluginBase):
    """Внешний плагин - Telegram бот"""
    
    id = "telegram-bot"
    name = "Telegram Bot"
    version = "1.0.0"
    
    async def on_start(self):
        """Запуск бота"""
        self.bot_token = self.get_config("BOT_TOKEN")
        
        # Получаем пользователей из Core API
        user = await self.core.get_current_user()
        self.logger.info(f"Bot started for user: {user.username}")
        
        # Получаем устройства
        devices = await self.core.list_devices()
        self.logger.info(f"Managing {len(devices)} devices")
        
        # Запускаем polling (имитация)
        await self.start_polling()
    
    async def start_polling(self):
        """Polling Telegram API"""
        while True:
            # Имитация получения сообщений
            await asyncio.sleep(1)
    
    async def handle_event(self, event_name: str, data: dict):
        """Обработка событий от Core"""
        if event_name == "device.state_changed":
            # Отправляем уведомление в Telegram
            self.logger.info(f"Device changed: {data}")


# ============= ПРИМЕР 3: Использование конфигурации =============

class ConfigExamplePlugin(InternalPluginBase):
    """Пример работы с конфигурацией"""
    
    id = "config-example"
    name = "Config Example"
    version = "1.0.0"
    
    async def on_load(self):
        # Простые значения
        api_key = self.config.get("API_KEY", "default-key")
        port = self.config.get_int("PORT", 8080)
        debug = self.config.get_bool("DEBUG", False)
        servers = self.config.get_list("SERVERS", ["localhost"])
        
        # Обязательное значение
        try:
            token = self.config.require("TOKEN")
        except ValueError as e:
            self.logger.error(f"Missing required config: {e}")
        
        # Pydantic модель
        class MyConfig(BaseModel):
            api_key: str
            timeout: int = 30
            retry_count: int = 3
            enabled: bool = True
        
        try:
            config = self.config.load_from_model(MyConfig)
            self.logger.info(f"Config loaded: {config.api_key}")
        except Exception as e:
            self.logger.error(f"Config validation failed: {e}")


# ============= ПРИМЕР 4: Фоновые задачи =============

class TasksExamplePlugin(InternalPluginBase):
    """Пример работы с фоновыми задачами"""
    
    id = "tasks-example"
    name = "Tasks Example"
    version = "1.0.0"
    
    async def on_load(self):
        # Периодическая задача
        self.tasks.add_task(
            "heartbeat",
            self.send_heartbeat,
            interval=30.0  # Каждые 30 секунд
        )
        
        # Однократная задача с задержкой
        self.tasks.schedule_once(
            "delayed_init",
            self.delayed_initialization,
            delay=5.0  # Через 5 секунд
        )
        
        # Задача в конкретное время
        from datetime import datetime, timedelta
        
        run_at = datetime.now() + timedelta(minutes=5)
        self.tasks.schedule_at(
            "scheduled_task",
            self.scheduled_task,
            run_at
        )
    
    async def send_heartbeat(self):
        """Отправка heartbeat"""
        self.logger.debug("💓 Heartbeat")
        await self.emit_event("heartbeat", {"timestamp": "now"})
    
    async def delayed_initialization(self):
        """Инициализация с задержкой"""
        self.logger.info("Delayed init complete")
    
    async def scheduled_task(self):
        """Задача по расписанию"""
        self.logger.info("Scheduled task executed")
    
    async def on_unload(self):
        self.tasks.stop_all()


# ============= ПРИМЕР 5: Аутентификация =============

class SecurePlugin(InternalPluginBase):
    """Плагин с защищенными endpoints"""
    
    id = "secure"
    name = "Secure Plugin"
    version = "1.0.0"
    
    async def on_load(self):
        self.router = APIRouter()
        
        # Публичный endpoint
        self.router.add_api_route(
            "/public",
            self.public_endpoint,
            methods=["GET"]
        )
        
        # Защищенный API ключом
        self.router.add_api_route(
            "/private",
            self.private_endpoint,
            methods=["GET"],
            dependencies=[Depends(require_api_key(self.id))]
        )
    
    async def public_endpoint(self):
        return {"message": "Public access"}
    
    async def private_endpoint(self):
        return {"message": "Private access - authenticated"}


# ============= ПРИМЕР 6: Работа с событиями =============

class EventsExamplePlugin(InternalPluginBase):
    """Пример работы с событиями"""
    
    id = "events-example"
    name = "Events Example"
    version = "1.0.0"
    
    async def on_load(self):
        # Подписка на конкретные события
        await self.subscribe_event("device.created", self.on_device_created)
        await self.subscribe_event("device.updated", self.on_device_updated)
        
        # Подписка с wildcard
        await self.subscribe_event("automation.*", self.on_any_automation)
        
        # Использование декоратора
        @self.events.on("user.login")
        async def on_user_login(event_name: str, data: dict):
            self.logger.info(f"User logged in: {data}")
    
    async def on_device_created(self, event_name: str, data: dict):
        self.logger.info(f"New device: {data}")
        
        # Отправляем свое событие
        await self.emit_event("device_indexed", {
            "device_id": data["device_id"],
            "indexed_at": "now"
        })
    
    async def on_device_updated(self, event_name: str, data: dict):
        self.logger.info(f"Device updated: {data}")
    
    async def on_any_automation(self, event_name: str, data: dict):
        self.logger.info(f"Automation event: {event_name}")


# ============= ПРИМЕР 7: HTTP клиент =============

async def external_plugin_example():
    """Пример использования CoreAPIClient"""
    
    client = CoreAPIClient("http://localhost:8000")
    
    try:
        # Вход
        token = await client.login("admin", "password")
        print(f"Logged in, token: {token[:20]}...")
        
        # Получение пользователя
        user = await client.get_current_user()
        print(f"User: {user.username}")
        
        # Работа с устройствами
        devices = await client.list_devices()
        print(f"Devices: {len(devices)}")
        
        # Создание устройства
        device = await client.create_device(
            DeviceCreate(
                name="Test Device",
                type="sensor",
                state={"temperature": 22.5}
            )
        )
        print(f"Created device: {device.id}")
        
        # Обновление устройства
        from home_console_sdk import DeviceUpdate
        updated = await client.update_device(
            device.id,
            DeviceUpdate(state={"temperature": 23.0})
        )
        print(f"Updated device: {updated.state}")
        
    finally:
        await client.close()


# Запуск примера
if __name__ == "__main__":
    asyncio.run(external_plugin_example())
