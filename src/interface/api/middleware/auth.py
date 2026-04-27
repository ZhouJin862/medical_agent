"""
Authentication middleware.

Provides JWT-based authentication for API endpoints.
"""
import logging
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/ws",  # WebSocket endpoints
}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication.

    Validates JWT tokens from Authorization header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process incoming request for authentication.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from next handler or error response
        """
        # Skip authentication for public paths
        if (
            request.url.path in PUBLIC_PATHS
            or request.url.path.startswith("/api/docs")
            or request.url.path.startswith("/ws")
        ):
            return await call_next(request)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # For now, we'll implement a simple pass-through
        # In production, validate JWT token here
        #
        # Example implementation:
        # auth_header = request.headers.get("Authorization")
        # if not auth_header or not auth_header.startswith("Bearer "):
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Missing or invalid authorization header",
        #     )
        #
        # token = auth_header.split(" ")[1]
        # try:
        #     payload = decode_jwt(token)
        #     request.state.user_id = payload.get("sub")
        # except JWTError as e:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Invalid token",
        #     )

        # For development, allow all requests
        return await call_next(request)


def get_current_user_id(request: Request) -> str | None:
    """
    Get the current user ID from request state.

    Args:
        request: FastAPI request

    Returns:
        User ID or None
    """
    return getattr(request.state, "user_id", None)


def require_auth(request: Request) -> str:
    """
    Require authentication and return user ID.

    Args:
        request: FastAPI request

    Returns:
        User ID

    Raises:
        HTTPException: If user is not authenticated
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user_id
