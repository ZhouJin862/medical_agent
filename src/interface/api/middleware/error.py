"""Error handling middleware."""

import logging
from typing import Callable, Union

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("medical_agent.api")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors globally."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any errors."""
        try:
            return await call_next(request)
        except StarletteHTTPException as exc:
            return self._handle_http_exception(exc)
        except ValueError as exc:
            return self._handle_validation_error(exc)
        except Exception as exc:
            return self._handle_unexpected_error(exc, request)

    def _handle_http_exception(self, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning("HTTP exception: %s - %s", exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "message": str(exc.detail),
                    "status_code": exc.status_code,
                }
            }
        )

    def _handle_validation_error(self, exc: ValueError) -> JSONResponse:
        """Handle validation errors."""
        logger.warning("Validation error: %s", str(exc))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "message": str(exc),
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                }
            }
        )

    def _handle_unexpected_error(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle unexpected errors."""
        logger.error(
            "Unexpected error on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }
            }
        )
