"""API middleware module."""

from src.interface.api.middleware.auth import (
    AuthenticationMiddleware,
    get_current_user_id,
    require_auth,
)
from src.interface.api.middleware.error_handler import setup_error_handlers
from src.interface.api.middleware.logging import LoggingMiddleware, setup_logging
from src.interface.api.middleware.error import ErrorHandlingMiddleware
from src.interface.api.middleware.cors import add_cors_middleware

__all__ = [
    "AuthenticationMiddleware",
    "get_current_user_id",
    "require_auth",
    "setup_error_handlers",
    "LoggingMiddleware",
    "setup_logging",
    "ErrorHandlingMiddleware",
    "add_cors_middleware",
]
