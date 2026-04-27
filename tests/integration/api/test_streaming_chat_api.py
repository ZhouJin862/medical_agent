"""
Integration tests for Streaming Chat API (SSE) endpoints.
"""
import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.interface.api.main import app


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    manager = Mock()

    # Mock session
    mock_session = Mock()
    mock_session.session_id = "test-session-1"
    mock_session.patient_id = "patient-123"
    mock_session.created_at = datetime.now()
    mock_session.updated_at = datetime.now()
    mock_session.metadata = {}

    # Mock get_or_create_session
    manager.get_or_create_session = Mock(return_value=mock_session)

    # Mock add_user_message
    manager.add_user_message = Mock()

    # Mock add_assistant_message
    manager.add_assistant_message = Mock()

    # Mock get_conversation_history
    mock_session.get_conversation_history = Mock(return_value=[])

    return manager, mock_session


@pytest.fixture
def mock_medical_agent():
    """Create mock medical agent."""
    agent = Mock()

    # Mock agent state
    mock_state = Mock()
    mock_state.status = Mock()
    mock_state.status.value = "completed"
    mock_state.intent = Mock()
    mock_state.intent.value = "health_assessment"
    mock_state.confidence = 0.9
    mock_state.suggested_skill = "hypertension_assessment"
    mock_state.final_response = "您好！根据您提供的血压数据，您的收缩压为150 mmHg，舒张压为95 mmHg，属于高血压1级。建议您注意饮食控制，减少钠盐摄入..."
    mock_state.patient_context = None

    agent.process = AsyncMock(return_value=mock_state)

    return agent


@pytest.mark.asyncio
async def test_streaming_chat_success(mock_session_manager, mock_medical_agent):
    """Test successful streaming chat request."""
    manager, mock_session = mock_session_manager

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_medical_agent,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/stream",
                    json={
                        "patient_id": "patient-123",
                        "message": "我今天血压有点高，150/95，需要担心吗？",
                    },
                )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE stream
    chunks = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            chunks.append(data)

    # Verify chunks
    assert len(chunks) > 0
    assert chunks[0]["type"] == "start"
    assert "session_id" in chunks[0]

    # Check for token chunks
    token_chunks = [c for c in chunks if c["type"] == "token"]
    assert len(token_chunks) > 0

    # Check for end chunk
    end_chunks = [c for c in chunks if c["type"] == "end"]
    assert len(end_chunks) == 1
    assert end_chunks[0]["intent"] == "health_assessment"


@pytest.mark.asyncio
async def test_streaming_chat_with_session_id(mock_session_manager, mock_medical_agent):
    """Test streaming chat with existing session ID."""
    manager, mock_session = mock_session_manager
    mock_session.session_id = "existing-session-1"

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_medical_agent,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/stream",
                    json={
                        "session_id": "existing-session-1",
                        "patient_id": "patient-123",
                        "message": "你好",
                    },
                )

    assert response.status_code == 200

    # Verify session was retrieved
    manager.get_or_create_session.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_chat_validation_error():
    """Test streaming chat with invalid request data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "patient_id": "patient-123",
                # Missing message
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_streaming_chat_empty_message():
    """Test streaming chat with empty message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "patient_id": "patient-123",
                "message": "",  # Empty message
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_streaming_chat_with_party_id(mock_session_manager, mock_medical_agent):
    """Test streaming chat with party_id in message."""
    manager, mock_session = mock_session_manager

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_medical_agent,
        ):
            with patch(
                "src.interface.api.routes.streaming_chat._get_health_data_from_pingan",
                return_value={"age": 45, "diseaseHistory": ["I10"]},
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/chat/stream",
                        json={
                            "patient_id": "patient-123",
                            "message": "客户号是 123456789，帮我看看我的健康状况",
                        },
                    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_streaming_chat_agent_error(mock_session_manager):
    """Test streaming chat when agent processing fails."""
    manager, mock_session = mock_session_manager

    mock_agent = Mock()
    mock_agent.process = AsyncMock(side_effect=Exception("Agent processing failed"))

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_agent,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/stream",
                    json={
                        "patient_id": "patient-123",
                        "message": "你好",
                    },
                )

    assert response.status_code == 200

    # Check for error chunk in stream
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            if data["type"] == "error":
                assert "error" in data
                break


@pytest.mark.asyncio
async def test_streaming_chat_with_conversation_history(mock_session_manager, mock_medical_agent):
    """Test streaming chat with conversation history."""
    manager, mock_session = mock_session_manager

    # Add conversation history
    mock_history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "您好！"},
    ]
    mock_session.get_conversation_history = Mock(return_value=mock_history)

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_medical_agent,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/stream",
                    json={
                        "patient_id": "patient-123",
                        "message": "我今天血压有点高",
                    },
                )

    assert response.status_code == 200
    mock_session.get_conversation_history.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_chat_sse_headers(mock_session_manager, mock_medical_agent):
    """Test that streaming chat response has correct SSE headers."""
    manager, mock_session = mock_session_manager

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_medical_agent,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/stream",
                    json={
                        "patient_id": "patient-123",
                        "message": "你好",
                    },
                )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "no-cache" in response.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_streaming_chat_session_persistence(mock_session_manager, mock_medical_agent):
    """Test that streaming chat persists messages to session."""
    manager, mock_session = mock_session_manager

    with patch(
        "src.infrastructure.session.session_manager.get_session_manager",
        return_value=manager,
    ):
        with patch(
            "src.infrastructure.agent.graph.MedicalAgent",
            return_value=mock_medical_agent,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/stream",
                    json={
                        "patient_id": "patient-123",
                        "message": "你好",
                    },
                )

    # Consume the response
    async for _ in response.aiter_lines():
        pass

    # Verify messages were added to session
    manager.add_user_message.assert_called_once()
    manager.add_assistant_message.assert_called_once()
