"""Logging middleware setup."""

import logging
import sys
from time import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings


def setup_logging() -> logging.Logger:
    """Configure application logging."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("medical_agent")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        logger = logging.getLogger("medical_agent.api")
        start_time = time()

        # Log request
        logger.info(
            "Request: %s %s from %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown"
        )

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time() - start_time
        logger.info(
            "Response: %s %s - Status: %d - Time: %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time
        )

        response.headers["X-Process-Time"] = str(process_time)
        return response
