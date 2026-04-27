"""
WebSocket Handler - Handles WebSocket connections and message routing.

Provides:
- WebSocket connection handling
- Message routing to agent
- Stream response support
- Error handling
"""

import logging
import json
from typing import Optional, Dict, Any

from .manager import ConnectionManager, get_connection_manager

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Handler for WebSocket connections.

    Manages:
    - Connection lifecycle
    - Message receiving and sending
    - Agent interaction
    - Error handling
    """

    def __init__(self, manager: Optional[ConnectionManager] = None):
        """
        Initialize the WebSocket handler.

        Args:
            manager: Optional connection manager (uses global if not provided)
        """
        self.manager = manager or get_connection_manager()
        logger.info("WebSocketHandler initialized")

    async def handle_connection(
        self,
        websocket,
        patient_id: str,
    ):
        """
        Handle a WebSocket connection from start to finish.

        Args:
            websocket: The WebSocket connection
            patient_id: Patient/user identifier
        """
        connection_id = None

        try:
            # Accept the connection
            await websocket.accept()

            # Register the connection
            connection_id = await self.manager.connect(websocket, patient_id)

            # Send welcome message
            await self._send_message(
                websocket,
                {
                    "type": "connected",
                    "connection_id": connection_id,
                    "patient_id": patient_id,
                    "message": "WebSocket connection established",
                }
            )

            # Message loop
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Update last activity
                await self._handle_message(websocket, patient_id, message)

        except Exception as e:
            logger.error(f"WebSocket error for patient {patient_id}: {e}")

            # Send error message if still connected
            try:
                await self._send_message(
                    websocket,
                    {
                        "type": "error",
                        "message": str(e),
                    }
                )
            except Exception:
                pass

        finally:
            # Cleanup connection
            if connection_id:
                await self.manager.disconnect(connection_id)

    async def _handle_message(
        self,
        websocket,
        patient_id: str,
        message: Dict[str, Any],
    ):
        """
        Handle an incoming message.

        Args:
            websocket: The WebSocket connection
            patient_id: Patient/user identifier
            message: Parsed message dictionary
        """
        message_type = message.get("type", "unknown")

        try:
            if message_type == "chat":
                await self._handle_chat_message(websocket, patient_id, message)

            elif message_type == "ping":
                await self._send_message(websocket, {"type": "pong"})

            elif message_type == "get_state":
                await self._send_state(websocket, patient_id)

            else:
                await self._send_message(
                    websocket,
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

        except Exception as e:
            logger.error(f"Error handling message type {message_type}: {e}")
            await self._send_message(
                websocket,
                {
                    "type": "error",
                    "message": str(e),
                }
            )

    async def _handle_chat_message(
        self,
        websocket,
        patient_id: str,
        message: Dict[str, Any],
    ):
        """
        Handle a chat message by routing to the agent.

        Args:
            websocket: The WebSocket connection
            patient_id: Patient/user identifier
            message: Chat message dictionary
        """
        user_input = message.get("content", "")

        if not user_input:
            await self._send_message(
                websocket,
                {
                    "type": "error",
                    "message": "Empty message content",
                }
            )
            return

        # Send acknowledgment
        await self._send_message(
            websocket,
            {
                "type": "message_ack",
                "content": user_input,
            }
        )

        # Process through agent
        try:
            from src.infrastructure.agent import process_health_query

            result = await process_health_query(user_input, patient_id)

            # Send response
            await self._send_message(
                websocket,
                {
                    "type": "chat_response",
                    "content": result.final_response or "No response generated",
                    "structured_output": result.structured_output,
                    "intent": result.intent.value if result.intent else None,
                    "confidence": result.confidence,
                    "executed_skills": [
                        {
                            "skill_name": s.skill_name,
                            "success": s.success,
                            "execution_time": s.execution_time,
                        }
                        for s in result.executed_skills
                    ],
                }
            )

        except Exception as e:
            logger.error(f"Agent processing error: {e}")
            await self._send_message(
                websocket,
                {
                    "type": "error",
                    "message": f"Processing error: {str(e)}",
                }
            )

    async def _send_state(self, websocket, patient_id: str):
        """
        Send current state information.

        Args:
            websocket: The WebSocket connection
            patient_id: Patient/user identifier
        """
        connections = self.manager.get_active_connections(patient_id)

        await self._send_message(
            websocket,
            {
                "type": "state",
                "patient_id": patient_id,
                "active_connections": len(connections),
                "connections": connections,
            }
        )

    async def _send_message(self, websocket, message: Dict[str, Any]):
        """
        Send a message through the WebSocket.

        Args:
            websocket: The WebSocket connection
            message: Message dictionary to send
        """
        await websocket.send_json(message)


async def handle_websocket_connection(websocket, patient_id: str):
    """
    Convenience function to handle a WebSocket connection.

    Args:
        websocket: The WebSocket connection
        patient_id: Patient/user identifier
    """
    handler = WebSocketHandler()
    await handler.handle_connection(websocket, patient_id)
