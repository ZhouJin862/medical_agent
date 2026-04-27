"""
Fixtures for WebSocket integration tests.

Provides:
- Mock WebSocket objects for testing
- Connection manager fixtures
- Test client setup
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.interface.websocket.manager import (
    ConnectionManager,
    ConnectionInfo,
    ConnectionStatus,
)


@pytest.fixture
def connection_manager():
    """Create a fresh ConnectionManager for each test."""
    manager = ConnectionManager()
    yield manager
    # Cleanup is automatic as manager is recreated each test


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = Mock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    return websocket


@pytest.fixture
def mock_websocket_with_messages(mock_websocket):
    """Create a mock WebSocket with predefined message sequence."""
    messages = []

    async def receive_text_side_effect():
        if messages:
            return messages.pop(0)
        # Simulate connection close after messages are consumed
        from fastapi.websockets import WebSocketDisconnect
        raise WebSocketDisconnect(code=1000, reason="Normal closure")

    mock_websocket.receive_text.side_effect = receive_text_side_effect

    def set_message_sequence(msg_list):
        nonlocal messages
        messages = msg_list.copy()

    mock_websocket.set_message_sequence = set_message_sequence
    return mock_websocket


@pytest.fixture
def connection_info(mock_websocket):
    """Create a ConnectionInfo object for testing."""
    return ConnectionInfo(
        websocket=mock_websocket,
        patient_id="test-patient-1",
        connection_id="test-conn-1",
    )


@pytest.fixture
def connected_websockets(connection_manager, mock_websocket):
    """Factory to create multiple connected WebSocket mocks.

    Returns:
        A function that takes a count and patient_id, creates that many
        connected websockets, and returns a list of (websocket, connection_id) tuples.
    """
    async def create_connected(count: int, patient_id: str = "test-patient"):
        connections = []
        for i in range(count):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.receive_text = AsyncMock()
            ws.send_json = AsyncMock()

            conn_id = await connection_manager.connect(ws, f"{patient_id}-{i}")
            connections.append((ws, conn_id))

        return connections

    return create_connected


@pytest.fixture
def sample_message():
    """Sample message dictionary for testing."""
    return {
        "type": "chat",
        "content": "Hello, how are you?",
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_broadcast_message():
    """Sample broadcast message for testing."""
    return {
        "type": "broadcast",
        "content": "System announcement",
        "timestamp": datetime.now().isoformat(),
    }
