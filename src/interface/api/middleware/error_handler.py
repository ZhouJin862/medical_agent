"""
Error handler middleware.

Provides global error handling for the FastAPI application.
"""
import logging
from typing import Any
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.domain.shared.exceptions.domain_exception import DomainException
from src.domain.shared.exceptions.patient_not_found import PatientNotFoundException
from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException
from src.application.services.skill_management_service import (
    SkillNotFoundException,
    SkillAlreadyExistsException,
)
from src.interface.api.dto.response import ErrorResponse

logger = logging.getLogger(__name__)


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Handle HTTP exceptions.

    Args:
        request: FastAPI request
        exc: HTTP exception

    Returns:
        JSON error response
    """
    error_response = ErrorResponse(
        error=type(exc).__name__,
        message=exc.detail,
        timestamp=datetime.now().isoformat(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle request validation exceptions.

    Args:
        request: FastAPI request
        exc: Validation exception

    Returns:
        JSON error response with validation details
    """
    errors = exc.errors()
    error_details = "; ".join([
        f"{'.'.join(str(e['loc']) if e['loc'] else ['body'])}: {e['msg']}"
        for e in errors
    ])

    error_response = ErrorResponse(
        error="ValidationError",
        message="Invalid request data",
        detail=error_details,
        timestamp=datetime.now().isoformat(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def domain_exception_handler(
    request: Request,
    exc: DomainException,
) -> JSONResponse:
    """
    Handle domain exceptions.

    Args:
        request: FastAPI request
        exc: Domain exception

    Returns:
        JSON error response
    """
    logger.warning(f"Domain exception: {exc.message}")

    # Determine status code based on exception type
    if isinstance(exc, PatientNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, InvalidVitalSignsException):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (SkillNotFoundException, SkillAlreadyExistsException)):
        status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, SkillNotFoundException) else status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    error_response = ErrorResponse(
        error=type(exc).__name__,
        message=exc.message,
        timestamp=datetime.now().isoformat(),
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle all other exceptions.

    Args:
        request: FastAPI request
        exc: Generic exception

    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)

    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        detail=str(exc) if logger.level <= logging.DEBUG else None,
        timestamp=datetime.now().isoformat(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def setup_error_handlers(app) -> None:
    """
    Setup all error handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers registered")
