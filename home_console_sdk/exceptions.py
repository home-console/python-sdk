class HomeConsoleSDKError(Exception):
    """Базовый exception для SDK"""
    pass

class AuthenticationError(HomeConsoleSDKError):
    """Ошибка аутентификации"""
    pass

class APIError(HomeConsoleSDKError):
    """Ошибка API"""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code

class NotFoundError(APIError):
    """Ресурс не найден"""
    pass

class ValidationError(HomeConsoleSDKError):
    """Ошибка валидации"""
    pass

# Backwards-compatibility alias: older imports expect SmartHomeSDKError
SmartHomeSDKError = HomeConsoleSDKError