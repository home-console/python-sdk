from .plugin import PluginBase, InternalPluginBase
from .remote_plugin import RemotePluginBase, create_lifecycle_handlers
from .client import CoreAPIClient
from .db import DatabaseClient
from .events import EventsClient
from .config import PluginConfig
from .tasks import TaskManager, BackgroundTask, background_task, schedule
from .auth import PluginAuth, require_api_key, require_bearer_token
from .models import (
    User,
    Device,
    DeviceCreate,
    DeviceUpdate,
    Plugin
)
from .exceptions import (
    HomeConsoleSDKError,
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
    # Plugin bases
    "PluginBase",
    "InternalPluginBase",
    # Remote Plugin (NEW in v0.1.0)
    "RemotePluginBase",
    "create_lifecycle_handlers",
    # Clients
    "CoreAPIClient",
    "DatabaseClient",
    "EventsClient",
    # Utilities
    "PluginConfig",
    "TaskManager",
    "BackgroundTask",
    "background_task",
    "schedule",
    # Auth
    "PluginAuth",
    "require_api_key",
    "require_bearer_token",
    # Models
    "User",
    "Device",
    "DeviceCreate",
    "DeviceUpdate",
    "Plugin",
    # Exceptions
    "HomeConsoleSDKError",
    "AuthenticationError",
    "APIError",
    "NotFoundError",
    "ValidationError",
]

# Backwards-compatibility alias
SmartHomeSDKError = HomeConsoleSDKError
__all__.append("SmartHomeSDKError")
