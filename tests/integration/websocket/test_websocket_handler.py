"""
Integration tests for WebSocket functionality.

Tests cover:
1. Connection management (connect, disconnect)
2. Message broadcasting to all clients
3. Message sending to specific client
4. Session state synchronization
5. Multiple concurrent clients
6. Connection error handling
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.interface.websocket.manager import (
    ConnectionManager,
    ConnectionInfo,
    ConnectionStatus,
)
from src.interface.websocket.handler import WebSocketHandler


class TestConnectionManager:
    """Test suite for ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connect_single_client(self, connection_manager, mock_websocket):
        """Test connecting a single WebSocket client."""
        patient_id = "patient-123"
        connection_id = await connection_manager.connect(mock_websocket, patient_id)

        assert connection_id is not None
        assert connection_id.startswith("conn_")
        assert patient_id in connection_id
        assert connection_manager.is_connected(patient_id)
        assert connection_manager.get_connection_count() == 1
        assert connection_manager.get_connection_count(patient_id) == 1

    @pytest.mark.asyncio
    async def test_connect_multiple_clients_same_patient(
        self, connection_manager, mock_websocket
    ):
        """Test connecting multiple clients with the same patient ID."""
        patient_id = "patient-123"

        # Create multiple mock websockets
        websockets = []
        for i in range(3):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            websockets.append(ws)

        connection_ids = []
        for ws in websockets:
            conn_id = await connection_manager.connect(ws, patient_id)
            connection_ids.append(conn_id)

        assert len(connection_ids) == 3
        assert all(conn_id is not None for conn_id in connection_ids)
        assert connection_manager.is_connected(patient_id)
        assert connection_manager.get_connection_count(patient_id) == 3
        assert connection_manager.get_connection_count() == 3

    @pytest.mark.asyncio
    async def test_connect_multiple_patients(
        self, connection_manager, mock_websocket
    ):
        """Test connecting multiple different patients."""
        patient_ids = ["patient-1", "patient-2", "patient-3"]

        connection_ids = []
        for patient_id in patient_ids:
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            conn_id = await connection_manager.connect(ws, patient_id)
            connection_ids.append(conn_id)

        assert len(connection_ids) == 3
        assert connection_manager.get_connection_count() == 3

        for patient_id in patient_ids:
            assert connection_manager.is_connected(patient_id)
            assert connection_manager.get_connection_count(patient_id) == 1

    @pytest.mark.asyncio
    async def test_disconnect_client(self, connection_manager, mock_websocket):
        """Test disconnecting a client."""
        patient_id = "patient-123"
        connection_id = await connection_manager.connect(mock_websocket, patient_id)

        assert connection_manager.is_connected(patient_id)

        await connection_manager.disconnect(connection_id)

        assert not connection_manager.is_connected(patient_id)
        assert connection_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_multiple_connections(
        self, connection_manager, mock_websocket
    ):
        """Test disconnecting multiple connections."""
        patient_id = "patient-123"

        # Create multiple connections
        websockets = []
        connection_ids = []
        for i in range(3):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            websockets.append(ws)
            conn_id = await connection_manager.connect(ws, patient_id)
            connection_ids.append(conn_id)

        assert connection_manager.get_connection_count(patient_id) == 3

        # Disconnect one at a time
        await connection_manager.disconnect(connection_ids[0])
        assert connection_manager.get_connection_count(patient_id) == 2

        await connection_manager.disconnect(connection_ids[1])
        assert connection_manager.get_connection_count(patient_id) == 1

        await connection_manager.disconnect(connection_ids[2])
        assert connection_manager.get_connection_count(patient_id) == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, connection_manager):
        """Test disconnecting a connection that doesn't exist."""
        # Should not raise an error
        await connection_manager.disconnect("nonexistent-conn-id")
        assert connection_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal_message(self, connection_manager, mock_websocket):
        """Test sending a message to a specific patient."""
        patient_id = "patient-123"
        await connection_manager.connect(mock_websocket, patient_id)

        message = {"type": "test", "content": "Hello patient"}

        result = await connection_manager.send_personal_message(message, patient_id)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_multiple_connections(
        self, connection_manager, mock_websocket
    ):
        """Test sending a personal message to multiple connections of same patient."""
        patient_id = "patient-123"

        # Create multiple connections
        websockets = []
        for i in range(3):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            websockets.append(ws)
            await connection_manager.connect(ws, patient_id)

        message = {"type": "test", "content": "Hello all connections"}

        result = await connection_manager.send_personal_message(message, patient_id)

        assert result is True
        for ws in websockets:
            ws.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_no_connections(
        self, connection_manager
    ):
        """Test sending a message to a patient with no connections."""
        message = {"type": "test", "content": "Hello"}

        result = await connection_manager.send_personal_message(message, "nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_connection(self, connection_manager, mock_websocket):
        """Test sending a message to a specific connection ID."""
        patient_id = "patient-123"
        connection_id = await connection_manager.connect(mock_websocket, patient_id)

        message = {"type": "test", "content": "Hello connection"}

        result = await connection_manager.send_to_connection(message, connection_id)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_connection(self, connection_manager):
        """Test sending a message to a nonexistent connection."""
        message = {"type": "test", "content": "Hello"}

        result = await connection_manager.send_to_connection(
            message, "nonexistent-conn"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_message(
        self, connection_manager, mock_websocket
    ):
        """Test broadcasting a message to all connected clients."""
        # Create multiple connections for different patients
        connections = {}
        for patient_id in ["patient-1", "patient-2", "patient-3"]:
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            connections[patient_id] = ws
            await connection_manager.connect(ws, patient_id)

        message = {"type": "broadcast", "content": "System announcement"}

        sent_count = await connection_manager.broadcast(message)

        assert sent_count == 3
        for ws in connections.values():
            ws.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_message_to_empty_manager(self, connection_manager):
        """Test broadcasting when no connections exist."""
        message = {"type": "broadcast", "content": "Test"}

        sent_count = await connection_manager.broadcast(message)

        assert sent_count == 0

    @pytest.mark.asyncio
    async def test_send_personal_message_with_failure(
        self, connection_manager, mock_websocket
    ):
        """Test handling connection failure during personal message send."""
        patient_id = "patient-123"

        # Create two connections - one will fail
        ws1 = Mock()
        ws1.send_json = AsyncMock(side_effect=Exception("Connection broken"))
        ws2 = Mock()
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()

        await connection_manager.connect(ws1, patient_id)
        await connection_manager.connect(ws2, patient_id)

        message = {"type": "test", "content": "Hello"}

        # Should still return True because ws2 succeeds
        result = await connection_manager.send_personal_message(message, patient_id)

        assert result is True
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_get_active_connections(
        self, connection_manager, mock_websocket
    ):
        """Test getting list of active connections."""
        patient_id = "patient-123"
        connection_id = await connection_manager.connect(mock_websocket, patient_id)

        connections = connection_manager.get_active_connections(patient_id)

        assert len(connections) == 1
        assert connections[0]["connection_id"] == connection_id
        assert connections[0]["patient_id"] == patient_id
        assert "connected_at" in connections[0]
        assert "last_activity" in connections[0]
        assert connections[0]["status"] == "connected"

    @pytest.mark.asyncio
    async def test_get_active_connections_all(
        self, connection_manager, mock_websocket
    ):
        """Test getting all active connections without patient filter."""
        # Create connections for multiple patients
        for patient_id in ["patient-1", "patient-2"]:
            await connection_manager.connect(mock_websocket, patient_id)

        all_connections = connection_manager.get_active_connections()

        assert len(all_connections) == 2

    @pytest.mark.asyncio
    async def test_get_connection_count(self, connection_manager, mock_websocket):
        """Test getting connection counts."""
        # Initially no connections
        assert connection_manager.get_connection_count() == 0

        # Add first patient
        await connection_manager.connect(mock_websocket, "patient-1")
        assert connection_manager.get_connection_count() == 1

        # Add second patient
        await connection_manager.connect(mock_websocket, "patient-2")
        assert connection_manager.get_connection_count() == 2

    @pytest.mark.asyncio
    async def test_is_connected(self, connection_manager, mock_websocket):
        """Test checking if patient is connected."""
        patient_id = "patient-123"

        assert not connection_manager.is_connected(patient_id)

        await connection_manager.connect(mock_websocket, patient_id)

        assert connection_manager.is_connected(patient_id)

    @pytest.mark.asyncio
    async def test_connection_counter_increment(self, connection_manager):
        """Test that connection IDs increment properly."""
        ws1 = Mock()
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()
        ws2.send_json = AsyncMock()

        conn_id_1 = await connection_manager.connect(ws1, "patient-1")
        conn_id_2 = await connection_manager.connect(ws2, "patient-2")

        # Connection IDs should be different and sequential
        assert conn_id_1 != conn_id_2
        assert "conn_1_" in conn_id_1
        assert "conn_2_" in conn_id_2


class TestWebSocketHandler:
    """Test suite for WebSocketHandler class."""

    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initialization with default manager."""
        handler = WebSocketHandler()
        assert handler.manager is not None
        assert isinstance(handler.manager, ConnectionManager)

    @pytest.mark.asyncio
    async def test_handler_with_custom_manager(self, connection_manager):
        """Test handler initialization with custom manager."""
        handler = WebSocketHandler(manager=connection_manager)
        assert handler.manager is connection_manager

    @pytest.mark.asyncio
    async def test_handle_connection_welcome_message(
        self, connection_manager, mock_websocket
    ):
        """Test that welcome message is sent on connection."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        # Mock the message loop to stop after one iteration
        mock_websocket.receive_text.side_effect = Exception("Stop loop")

        await handler.handle_connection(mock_websocket, patient_id)

        # Verify welcome message was sent
        mock_websocket.accept.assert_called_once()
        calls = mock_websocket.send_json.call_args_list

        # First call should be welcome message
        welcome_call = calls[0]
        welcome_msg = welcome_call[0][0]
        assert welcome_msg["type"] == "connected"
        assert welcome_msg["patient_id"] == patient_id
        assert "connection_id" in welcome_msg

    @pytest.mark.asyncio
    async def test_handle_ping_message(
        self, connection_manager, mock_websocket
    ):
        """Test handling ping message."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        # Set up message sequence: ping then disconnect
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            Exception("Stop loop")
        ]

        await handler.handle_connection(mock_websocket, patient_id)

        # Should have received welcome and pong
        calls = mock_websocket.send_json.call_args_list
        assert len(calls) >= 2

        pong_call = [c for c in calls if c[0][0].get("type") == "pong"]
        assert len(pong_call) > 0

    @pytest.mark.asyncio
    async def test_handle_get_state_message(
        self, connection_manager, mock_websocket
    ):
        """Test handling get_state message."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        mock_websocket.receive_text.side_effect = [
            '{"type": "get_state"}',
            Exception("Stop loop")
        ]

        await handler.handle_connection(mock_websocket, patient_id)

        calls = mock_websocket.send_json.call_args_list
        state_calls = [c for c in calls if c[0][0].get("type") == "state"]
        assert len(state_calls) > 0

        state_msg = state_calls[0][0][0]
        assert state_msg["patient_id"] == patient_id
        assert "active_connections" in state_msg

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(
        self, connection_manager, mock_websocket
    ):
        """Test handling unknown message type."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        mock_websocket.receive_text.side_effect = [
            '{"type": "unknown_type"}',
            Exception("Stop loop")
        ]

        await handler.handle_connection(mock_websocket, patient_id)

        calls = mock_websocket.send_json.call_args_list
        error_calls = [c for c in calls if c[0][0].get("type") == "error"]
        assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_handle_connection_disconnect_cleanup(
        self, connection_manager, mock_websocket
    ):
        """Test that connection is cleaned up on disconnect."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        # Simulate immediate disconnect
        from fastapi.websockets import WebSocketDisconnect
        mock_websocket.receive_text.side_effect = WebSocketDisconnect(
            code=1000, reason="Normal closure"
        )

        await handler.handle_connection(mock_websocket, patient_id)

        # Connection should be cleaned up
        assert not connection_manager.is_connected(patient_id)

    @pytest.mark.asyncio
    async def test_handle_chat_message_empty_content(
        self, connection_manager, mock_websocket
    ):
        """Test handling chat message with empty content."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        mock_websocket.receive_text.side_effect = [
            '{"type": "chat", "content": ""}',
            Exception("Stop loop")
        ]

        await handler.handle_connection(mock_websocket, patient_id)

        calls = mock_websocket.send_json.call_args_list
        error_calls = [c for c in calls if c[0][0].get("type") == "error"]
        assert len(error_calls) > 0

        error_msg = error_calls[0][0][0]
        assert "Empty message content" in error_msg["message"]


class TestMultipleConcurrentClients:
    """Test suite for multiple concurrent WebSocket connections."""

    @pytest.mark.asyncio
    async def test_concurrent_connections_different_patients(
        self, connection_manager
    ):
        """Test multiple concurrent connections from different patients."""
        connections = []

        # Create 5 concurrent connections
        for i in range(5):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()

            patient_id = f"patient-{i}"
            conn_id = await connection_manager.connect(ws, patient_id)
            connections.append((ws, conn_id, patient_id))

        assert connection_manager.get_connection_count() == 5

        # Broadcast to all
        broadcast_msg = {"type": "broadcast", "content": "Hello everyone"}
        sent_count = await connection_manager.broadcast(broadcast_msg)

        assert sent_count == 5
        for ws, _, _ in connections:
            ws.send_json.assert_called_with(broadcast_msg)

    @pytest.mark.asyncio
    async def test_concurrent_connections_same_patient(
        self, connection_manager
    ):
        """Test multiple concurrent connections from the same patient."""
        patient_id = "patient-123"
        connections = []

        # Create 3 connections from same patient
        for i in range(3):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            conn_id = await connection_manager.connect(ws, patient_id)
            connections.append((ws, conn_id))

        assert connection_manager.get_connection_count(patient_id) == 3

        # Send personal message - should reach all 3
        personal_msg = {"type": "personal", "content": "Hello patient"}
        result = await connection_manager.send_personal_message(
            personal_msg, patient_id
        )

        assert result is True
        for ws, _ in connections:
            ws.send_json.assert_called_with(personal_msg)

    @pytest.mark.asyncio
    async def test_selective_messaging_with_concurrent_clients(
        self, connection_manager
    ):
        """Test selective messaging when multiple clients are connected."""
        # Create connections for different patients
        patient1_ws = Mock()
        patient1_ws.accept = AsyncMock()
        patient1_ws.close = AsyncMock()
        patient1_ws.send_json = AsyncMock()

        patient2_ws = Mock()
        patient2_ws.accept = AsyncMock()
        patient2_ws.close = AsyncMock()
        patient2_ws.send_json = AsyncMock()

        conn1 = await connection_manager.connect(patient1_ws, "patient-1")
        conn2 = await connection_manager.connect(patient2_ws, "patient-2")

        # Send to patient-1 only
        msg1 = {"type": "private", "content": "For patient 1 only"}
        await connection_manager.send_personal_message(msg1, "patient-1")

        # Only patient-1 should receive the message
        patient1_ws.send_json.assert_called_with(msg1)
        # patient-2 should not have been called with this message
        assert not any(
            call[0][0] == msg1 for call in patient2_ws.send_json.call_args_list
        )

    @pytest.mark.asyncio
    async def test_concurrent_disconnects(self, connection_manager):
        """Test disconnecting multiple concurrent connections."""
        connections = []

        # Create 5 connections
        for i in range(5):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            conn_id = await connection_manager.connect(ws, f"patient-{i}")
            connections.append((conn_id, f"patient-{i}"))

        assert connection_manager.get_connection_count() == 5

        # Disconnect all
        for conn_id, patient_id in connections:
            await connection_manager.disconnect(conn_id)

        assert connection_manager.get_connection_count() == 0

        # Verify all patients are disconnected
        for _, patient_id in connections:
            assert not connection_manager.is_connected(patient_id)


class TestConnectionErrorHandling:
    """Test suite for connection error handling."""

    @pytest.mark.asyncio
    async def test_send_to_disconnected_connection(self, connection_manager):
        """Test sending to a connection that has been closed."""
        ws = Mock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("Connection closed"))

        conn_id = await connection_manager.connect(ws, "patient-1")

        # Try to send - should handle the error
        result = await connection_manager.send_to_connection(
            {"type": "test", "content": "Hello"}, conn_id
        )

        # Should return False due to error
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_with_some_failed_connections(
        self, connection_manager
    ):
        """Test broadcasting when some connections have failed."""
        # Create multiple connections, some will fail
        connections = []
        for i in range(5):
            ws = Mock()
            # Make odd-indexed connections fail
            if i % 2 == 1:
                ws.send_json = AsyncMock(side_effect=Exception("Failed"))
            else:
                ws.send_json = AsyncMock()
            connections.append(ws)

        for i, ws in enumerate(connections):
            await connection_manager.connect(ws, f"patient-{i}")

        # Broadcast - should succeed for working connections
        message = {"type": "broadcast", "content": "Test"}
        sent_count = await connection_manager.broadcast(message)

        # Should have sent to 3 successful connections (indices 0, 2, 4)
        assert sent_count == 3

    @pytest.mark.asyncio
    async def test_invalid_json_message(self, connection_manager, mock_websocket):
        """Test handling of invalid JSON message."""
        handler = WebSocketHandler(manager=connection_manager)
        patient_id = "patient-123"

        # Invalid JSON should be handled
        mock_websocket.receive_text.side_effect = [
            "invalid json{{{",
            Exception("Stop loop")
        ]

        # Should not crash, but handle error gracefully
        try:
            await handler.handle_connection(mock_websocket, patient_id)
        except Exception:
            # Expected to catch JSON decode error
            pass

    @pytest.mark.asyncio
    async def test_connection_manager_resilience(self, connection_manager):
        """Test that connection manager remains functional after errors."""
        # Add some connections
        for i in range(3):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            await connection_manager.connect(ws, f"patient-{i}")

        # Cause some failures
        failed_ws = Mock()
        failed_ws.send_json = AsyncMock(side_effect=Exception("Failed"))
        await connection_manager.connect(failed_ws, "failed-patient")

        # Manager should still work
        working_ws = Mock()
        working_ws.accept = AsyncMock()
        working_ws.close = AsyncMock()
        working_ws.send_json = AsyncMock()
        conn_id = await connection_manager.connect(working_ws, "working-patient")

        # Should be able to send to working connection
        result = await connection_manager.send_to_connection(
            {"type": "test"}, conn_id
        )

        assert result is True
