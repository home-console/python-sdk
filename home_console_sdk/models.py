from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class User(BaseModel):
    """Пользователь системы"""
    id: int
    username: str
    email: str
    is_active: bool = True
    created_at: Optional[datetime] = None

class Device(BaseModel):
    """Устройство"""
    id: int
    user_id: int
    plugin_id: str
    external_id: Optional[str] = None
    name: str
    type: str
    state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

class DeviceCreate(BaseModel):
    """Создание устройства"""
    name: str
    type: str
    external_id: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DeviceUpdate(BaseModel):
    """Обновление устройства"""
    name: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class Plugin(BaseModel):
    """Плагин"""
    id: int
    plugin_id: str
    name: str
    version: Optional[str] = None
    enabled: bool = True
    loaded: bool = False
    plugin_type: str = "in_process"
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None