"""
WebSocket Interface - Real-time communication for health consultation.

Provides:
- WebSocketHandler for managing WebSocket connections
- ConnectionManager for connection pooling and broadcasting
- Real-time message streaming support
"""

from .handler import WebSocketHandler
from .manager import ConnectionManager

__all__ = [
    "WebSocketHandler",
    "ConnectionManager",
]
