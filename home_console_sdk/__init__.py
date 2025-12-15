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

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

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
