"""Medical Agent FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.interface.api.middleware import (
    LoggingMiddleware,
    ErrorHandlingMiddleware,
    add_cors_middleware,
)
from src.interface.api.middleware.logging import setup_logging

# Initialize logger
logger = setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Using model: {settings.model}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered medical consultation and health plan generation system",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# Add CORS middleware
add_cors_middleware(app)

# Add custom middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint with service information."""
    return JSONResponse(
        content={
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "healthy",
            "model": settings.model,
        }
    )


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint for container orchestration."""
    return JSONResponse(
        content={"status": "healthy", "service": settings.app_name}
    )


# Include routers
from src.interface.api.routes import skill_packages, skills, streaming_chat
from src.interface.api.routes.chat import router, v1_router  # Import directly from chat.py
app.include_router(skill_packages.router)
app.include_router(skills.router)
app.include_router(streaming_chat.router)
app.include_router(router)  # Main chat router with /send endpoint
app.include_router(v1_router)  # V1 router for backward compatibility
