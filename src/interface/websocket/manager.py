"""
Connection Manager - Manages WebSocket connections and message broadcasting.

Handles:
- Connection pooling
- Message broadcasting to all connected clients
- Individual message sending
- Connection state tracking
"""

import logging
from typing import Dict, Set, Optional
from datetime import datetime
from enum import Enum

try:
    from fastapi import WebSocket
    from fastapi.websockets import WebSocketDisconnect
except ImportError:
    WebSocket = None
    WebSocketDisconnect = Exception

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Status of a WebSocket connection."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionInfo:
    """
    Information about a WebSocket connection.

    Attributes:
        websocket: The WebSocket instance
        patient_id: Associated patient/user ID
        connection_id: Unique connection identifier
        connected_at: When the connection was established
        last_activity: Last activity timestamp
        status: Current connection status
    """

    def __init__(
        self,
        websocket: "WebSocket",
        patient_id: str,
        connection_id: str,
    ):
        self.websocket = websocket
        self.patient_id = patient_id
        self.connection_id = connection_id
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.status = ConnectionStatus.CONNECTED


class ConnectionManager:
    """
    Manager for WebSocket connections.

    Provides:
    - Connection tracking
    - Broadcasting to all connections
    - Targeted messaging by patient_id
    - Connection cleanup
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Active connections by patient_id
        self._active_connections: Dict[str, Set[ConnectionInfo]] = {}

        # Connection lookup by connection_id
        self._connection_lookup: Dict[str, ConnectionInfo] = {}

        # Counter for generating connection IDs
        self._connection_counter = 0

        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: "WebSocket", patient_id: str) -> str:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            patient_id: Patient/user identifier

        Returns:
            Connection ID for the new connection
        """
        # Generate connection ID
        self._connection_counter += 1
        connection_id = f"conn_{self._connection_counter}_{patient_id}"

        # Create connection info
        connection_info = ConnectionInfo(
            websocket=websocket,
            patient_id=patient_id,
            connection_id=connection_id,
        )

        # Add to active connections
        if patient_id not in self._active_connections:
            self._active_connections[patient_id] = set()

        self._active_connections[patient_id].add(connection_info)
        self._connection_lookup[connection_id] = connection_info

        logger.info(
            f"WebSocket connected: patient_id={patient_id}, "
            f"connection_id={connection_id}"
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        Remove and close a WebSocket connection.

        Args:
            connection_id: Connection identifier to disconnect
        """
        if connection_id not in self._connection_lookup:
            logger.warning(f"Connection not found: {connection_id}")
            return

        connection_info = self._connection_lookup[connection_id]
        patient_id = connection_info.patient_id

        # Remove from lookup
        del self._connection_lookup[connection_id]

        # Remove from active connections
        if patient_id in self._active_connections:
            self._active_connections[patient_id].discard(connection_info)

            if not self._active_connections[patient_id]:
                del self._active_connections[patient_id]

        logger.info(
            f"WebSocket disconnected: patient_id={patient_id}, "
            f"connection_id={connection_id}"
        )

    async def send_personal_message(
        self,
        message: dict,
        patient_id: str,
    ) -> bool:
        """
        Send a message to all connections for a specific patient.

        Args:
            message: Message dictionary to send
            patient_id: Patient/user identifier

        Returns:
            True if message was sent successfully
        """
        if patient_id not in self._active_connections:
            logger.warning(f"No active connections for patient: {patient_id}")
            return False

        sent_count = 0
        failed_count = 0

        for connection_info in list(self._active_connections[patient_id]):
            try:
                await connection_info.websocket.send_json(message)
                connection_info.last_activity = datetime.now()
                sent_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to send to connection {connection_info.connection_id}: {e}"
                )
                await self.disconnect(connection_info.connection_id)
                failed_count += 1

        if sent_count > 0:
            logger.debug(
                f"Sent message to {sent_count} connection(s) for patient {patient_id}"
            )

        return sent_count > 0

    async def send_to_connection(
        self,
        message: dict,
        connection_id: str,
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            message: Message dictionary to send
            connection_id: Connection identifier

        Returns:
            True if message was sent successfully
        """
        if connection_id not in self._connection_lookup:
            logger.warning(f"Connection not found: {connection_id}")
            return False

        connection_info = self._connection_lookup[connection_id]

        try:
            await connection_info.websocket.send_json(message)
            connection_info.last_activity = datetime.now()
            return True

        except Exception as e:
            logger.error(
                f"Failed to send to connection {connection_id}: {e}"
            )
            await self.disconnect(connection_id)
            return False

    async def broadcast(self, message: dict) -> int:
        """
        Broadcast a message to all active connections.

        Args:
            message: Message dictionary to broadcast

        Returns:
            Number of connections the message was sent to
        """
        sent_count = 0

        for connection_info in list(self._connection_lookup.values()):
            try:
                await connection_info.websocket.send_json(message)
                connection_info.last_activity = datetime.now()
                sent_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to broadcast to {connection_info.connection_id}: {e}"
                )
                await self.disconnect(connection_info.connection_id)

        if sent_count > 0:
            logger.info(f"Broadcasted message to {sent_count} connection(s)")

        return sent_count

    def get_active_connections(self, patient_id: Optional[str] = None) -> list:
        """
        Get active connection information.

        Args:
            patient_id: Optional patient filter

        Returns:
            List of connection information dictionaries
        """
        if patient_id:
            connections = self._active_connections.get(patient_id, set())
        else:
            connections = set()
            for conns in self._active_connections.values():
                connections.update(conns)

        return [
            {
                "connection_id": c.connection_id,
                "patient_id": c.patient_id,
                "connected_at": c.connected_at.isoformat(),
                "last_activity": c.last_activity.isoformat(),
                "status": c.status.value,
            }
            for c in connections
        ]

    def get_connection_count(self, patient_id: Optional[str] = None) -> int:
        """
        Get count of active connections.

        Args:
            patient_id: Optional patient filter

        Returns:
            Number of active connections
        """
        if patient_id:
            return len(self._active_connections.get(patient_id, set()))

        return sum(len(conns) for conns in self._active_connections.values())

    def is_connected(self, patient_id: str) -> bool:
        """
        Check if a patient has any active connections.

        Args:
            patient_id: Patient/user identifier

        Returns:
            True if at least one active connection exists
        """
        return patient_id in self._active_connections and len(
            self._active_connections[patient_id]
        ) > 0


# Global connection manager instance
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager instance.

    Returns:
        ConnectionManager singleton
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
