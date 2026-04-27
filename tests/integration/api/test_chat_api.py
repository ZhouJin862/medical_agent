"""
Integration tests for Chat API endpoints.

Tests cover:
- POST /api/chat/send - Send message and get AI response
- GET /api/chat/consultations/{consultation_id}/messages - Get consultation messages
- POST /api/chat/consultations/{consultation_id}/close - Close consultation
- GET /api/chat/consultations/active/{patient_id} - Get active consultation
- GET /api/v1/chat/sessions/{patient_id} - Get chat sessions (v1 API)
- GET /api/v1/chat/sessions/{session_id}/messages - Get session messages (v1 API)
- DELETE /api/v1/chat/sessions/{session_id} - Delete session (v1 API)
"""
import pytest
import json
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock

from src.interface.api.main import app
from src.application.services.chat_service import ChatApplicationService


@pytest.fixture
def mock_chat_service():
    """Create mock chat service."""
    from src.interface.api.dependencies import get_chat_service

    service = Mock()
    service.send_message = AsyncMock(return_value={
        "consultation_id": "test-consultation-1",
        "user_message": {
            "id": "msg-1",
            "consultation_id": "test-consultation-1",
            "role": "user",
            "content": "你好",
            "created_at": "2024-01-15T10:00:00",
        },
        "ai_response": {
            "id": "msg-2",
            "consultation_id": "test-consultation-1",
            "role": "assistant",
            "content": "您好！我是您的健康助手",
            "intent": "greeting",
            "created_at": "2024-01-15T10:00:01",
        },
    })

    # Use FastAPI's dependency override mechanism
    app.dependency_overrides[get_chat_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def mock_consultation_service():
    """Create mock consultation service."""
    from src.interface.api.dependencies import get_consultation_service

    service = Mock()
    service.get_consultation_messages = AsyncMock(return_value=[
        {
            "id": "msg-1",
            "consultation_id": "consult-1",
            "role": "user",
            "content": "你好",
            "created_at": "2024-01-15T10:00:00",
        },
        {
            "id": "msg-2",
            "consultation_id": "consult-1",
            "role": "assistant",
            "content": "您好！",
            "intent": "greeting",
            "created_at": "2024-01-15T10:00:01",
        },
    ])
    service.close_consultation = AsyncMock(return_value=True)
    service.get_active_consultation = AsyncMock(return_value={
        "consultation_id": "active-consult-1",
        "patient_id": "patient-123",
        "status": "active",
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:30:00",
        "message_count": 5,
    })

    app.dependency_overrides[get_consultation_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_send_message_success(mock_chat_service):
    """Test sending a message successfully."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                    "patient_id": "patient-123",
                    "message_content": "你好",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["consultation_id"] == "test-consultation-1"
    assert "user_message" in data
    assert "ai_response" in data
    mock_chat_service.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_with_consultation_id(mock_chat_service):
    """Test sending a message with existing consultation ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "patient_id": "patient-123",
                "message_content": "我今天感觉头晕",
                "consultation_id": "existing-consultation-1",
            },
        )

    assert response.status_code == 200
    mock_chat_service.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_validation_error():
    """Test sending a message with invalid data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "patient_id": "patient-123",
                # Missing message_content
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_conversation_messages(mock_consultation_service):
    """Test getting conversation messages."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/consultations/consult-1/messages",
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    mock_consultation_service.get_consultation_messages.assert_called_once()


@pytest.mark.asyncio
async def test_close_consultation(mock_consultation_service):
    """Test closing a consultation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/consultations/consult-1/close",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    mock_consultation_service.close_consultation.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_consultation(mock_consultation_service):
    """Test getting active consultation for a patient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/consultations/active/patient-123",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["consultation_id"] == "active-consult-1"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_active_consultation_none(mock_consultation_service):
    """Test getting active consultation when none exists."""
    mock_consultation_service.get_active_consultation = AsyncMock(return_value=None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/consultations/active/patient-no-active",
        )

    assert response.status_code == 200
    data = response.json()
    assert data is None


@pytest.mark.asyncio
async def test_send_message_with_long_content(mock_chat_service):
    """Test sending a message with long content."""
    long_message = "你好，" + "这是一个很长的消息。" * 50

    mock_chat_service.send_message = AsyncMock(return_value={
        "consultation_id": "test-consultation-1",
        "user_message": {
            "id": "msg-1",
            "role": "user",
            "content": long_message,
        },
        "ai_response": {
            "id": "msg-2",
            "role": "assistant",
            "content": "收到了您的长消息。",
        },
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "patient_id": "patient-123",
                "message_content": long_message,
            },
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_send_message_with_special_characters(mock_chat_service):
    """Test sending a message with special characters."""
    special_message = "我今天血压是150/95 mmHg，血糖是7.5 mmol/L，总胆固醇是6.2 mmol/L。"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "patient_id": "patient-123",
                "message_content": special_message,
            },
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_conversation_messages_with_limit(mock_consultation_service):
    """Test getting conversation messages with custom limit."""
    mock_consultation_service.get_consultation_messages = AsyncMock(return_value=[])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/chat/consultations/consult-1/messages?limit=50",
        )

    assert response.status_code == 200
    mock_consultation_service.get_consultation_messages.assert_called_once()


@pytest.mark.asyncio
async def test_close_consultation_not_found(mock_consultation_service):
    """Test closing a consultation that doesn't exist."""
    mock_consultation_service.close_consultation = AsyncMock(return_value=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/consultations/nonexistent/close",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False


# ========== V1 API Tests ==========


@pytest.mark.asyncio
async def test_v1_get_chat_sessions():
    """Test getting chat sessions for a patient (v1 API)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/chat/sessions/patient-123",
        )

    # Should return 200 even if no sessions exist
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total_count" in data


@pytest.mark.asyncio
async def test_v1_debug_paths():
    """Test the debug paths endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/debug/paths")

    assert response.status_code == 200
    data = response.json()
    assert "current_file" in data
    assert "base_dir" in data


@pytest.mark.asyncio
async def test_v1_test_new_endpoint():
    """Test the new endpoint verification."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/test/new")

    assert response.status_code == 200
    data = response.json()
    assert "test" in data

