from .plugin import PluginBase, InternalPluginBase
from .client import CoreAPIClient
from .models import (
    User,
    Device,
    DeviceCreate,
    DeviceUpdate,
    Plugin
)
from .exceptions import (
    SmartHomeSDKError,
    AuthenticationError,
    APIError,
    NotFoundError,
    ValidationError
)

__version__ = "1.0.0"

__all__ = [
    "PluginBase",
    "InternalPluginBase",
    "CoreAPIClient",
    "User",
    "Device",
    "DeviceCreate",
    "DeviceUpdate",
    "Plugin",
    "SmartHomeSDKError",
    "AuthenticationError",
    "APIError",
    "NotFoundError",
    "ValidationError",
]
