"""
WebSocket API routes.

Provides WebSocket endpoint for real-time chat.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, patient_id: str):
        """Accept and register a new connection."""
        await websocket.accept()
        self.active_connections[patient_id] = websocket
        logger.info(f"Patient {patient_id} connected via WebSocket")

    def disconnect(self, patient_id: str):
        """Remove a connection."""
        if patient_id in self.active_connections:
            del self.active_connections[patient_id]
            logger.info(f"Patient {patient_id} disconnected")

    async def send_personal_message(self, message: dict, patient_id: str):
        """Send a message to a specific patient."""
        if patient_id in self.active_connections:
            websocket = self.active_connections[patient_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {patient_id}: {e}")
                self.disconnect(patient_id)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.

    Expected message format:
    {
        "type": "connect" | "chat_message" | "ping",
        "patient_id": str,
        "message_id"?: str,
        "content"?: str
    }
    """
    logger.info("WebSocket connection attempt")

    patient_id = None

    try:
        # Wait for the first message to get patient_id
        data = await websocket.receive_text()
        message = json.loads(data)

        logger.info(f"Received WebSocket message: {message}")

        patient_id = message.get("patient_id", "unknown")

        if message.get("type") == "connect":
            await manager.connect(websocket, patient_id)
            await websocket.send_json({
                "type": "connected",
                "patient_id": patient_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            # If first message is not connect, still accept the connection
            await manager.connect(websocket, patient_id)
            await websocket.send_json({
                "type": "connected",
                "patient_id": patient_id,
                "timestamp": datetime.now().isoformat()
            })
            # Process the initial message
            if message.get("type") == "chat_message":
                await handle_chat_message(message, patient_id)

        # Keep listening for messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "chat_message":
                await handle_chat_message(message, patient_id)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "connect":
                # Already connected, just acknowledge
                await websocket.send_json({
                    "type": "connected",
                    "patient_id": patient_id
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {patient_id}")
        if patient_id:
            manager.disconnect(patient_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if patient_id:
            manager.disconnect(patient_id)


async def handle_chat_message(message: dict, patient_id: str):
    """
    Handle a chat message and send a response.

    For now, this is a simple echo/mock response.
    In production, this would call the LangGraph agent.
    """
    message_id = message.get("message_id", f"msg-{datetime.now().timestamp()}")
    content = message.get("content", "")

    logger.info(f"Handling message from {patient_id}: {content}")

    # Simulate processing delay
    await asyncio.sleep(0.5)

    # Create a mock response
    response = {
        "type": "chat_response",
        "message_id": f"response-{datetime.now().timestamp()}",
        "original_message_id": message_id,
        "content": f"收到您的消息：{content}\n\n这是一个模拟回复。后端 AI 服务正在开发中。",
        "timestamp": datetime.now().isoformat(),
        "intent": "general",
        "confidence": 0.8,
    }

    await manager.send_personal_message(response, patient_id)
