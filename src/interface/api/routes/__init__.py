"""API routes module."""

from src.interface.api.routes.chat import router as chat_router
from src.interface.api.routes.health import router as health_router
from src.interface.api.routes.plan import router as plan_router
from src.interface.api.routes.consultation import router as consultation_router
from src.interface.api.routes.skills import router as skills_router
from src.interface.api.routes.websocket import router as websocket_router

__all__ = [
    "chat_router",
    "health_router",
    "plan_router",
    "consultation_router",
    "skills_router",
    "websocket_router",
]
