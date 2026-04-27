"""
Integration tests for Consultation History API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock

from src.interface.api.main import app
from src.interface.api.dependencies import get_consultation_service


@pytest.fixture
def mock_consultation_service():
    """Create mock consultation service."""
    service = Mock()

    # Mock get_consultation_history
    service.get_consultation_history = AsyncMock(return_value=[
        {
            "consultation_id": "consult-1",
            "patient_id": "patient-123",
            "status": "closed",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:30:00",
            "message_count": 12,
        },
        {
            "consultation_id": "consult-2",
            "patient_id": "patient-123",
            "status": "active",
            "created_at": "2024-01-16T09:00:00",
            "updated_at": "2024-01-16T09:15:00",
            "message_count": 5,
        },
    ])

    # Mock get_consultation
    service.get_consultation = AsyncMock(return_value={
        "consultation_id": "consult-1",
        "patient_id": "patient-123",
        "status": "closed",
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:30:00",
        "message_count": 12,
    })

    # Mock get_consultation_summary
    service.get_consultation_summary = AsyncMock(return_value={
        "consultation_id": "consult-1",
        "patient_id": "patient-123",
        "status": "closed",
        "message_count": 12,
        "intents_detected": ["health_assessment", "risk_evaluation"],
        "duration_minutes": 30,
        "start_time": "2024-01-15T10:00:00",
        "end_time": "2024-01-15T10:30:00",
    })

    app.dependency_overrides[get_consultation_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_consultation_history_success(mock_consultation_service):
    """Test getting consultation history for a patient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/patient/patient-123")

    assert response.status_code == 200
    data = response.json()
    assert "consultations" in data
    assert data["total_count"] == 2
    assert data["patient_id"] == "patient-123"
    assert len(data["consultations"]) == 2
    mock_consultation_service.get_consultation_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_consultation_history_with_limit(mock_consultation_service):
    """Test getting consultation history with custom limit."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/patient/patient-123?limit=5")

    assert response.status_code == 200
    mock_consultation_service.get_consultation_history.assert_called_once()


@pytest.mark.asyncio
async def test_get_consultation_history_invalid_limit():
    """Test getting consultation history with invalid limit."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/patient/patient-123?limit=0")

    assert response.status_code == 400

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/patient/patient-123?limit=101")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_consultation_by_id(mock_consultation_service):
    """Test getting a consultation by ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/consult-1")

    assert response.status_code == 200
    data = response.json()
    assert data["consultation_id"] == "consult-1"
    assert data["patient_id"] == "patient-123"
    assert data["status"] == "closed"
    mock_consultation_service.get_consultation.assert_called_once()


@pytest.mark.asyncio
async def test_get_consultation_not_found():
    """Test getting a non-existent consultation."""
    mock_service = Mock()
    mock_service.get_consultation = AsyncMock(return_value=None)

    app.dependency_overrides[get_consultation_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/nonexistent")

    app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_consultation_summary(mock_consultation_service):
    """Test getting detailed consultation summary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/consult-1/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["consultation_id"] == "consult-1"
    assert "message_count" in data
    assert "intents_detected" in data
    assert "duration_minutes" in data
    mock_consultation_service.get_consultation_summary.assert_called_once()


@pytest.mark.asyncio
async def test_get_consultation_history_empty():
    """Test getting consultation history for a patient with no history."""
    mock_service = Mock()
    mock_service.get_consultation_history = AsyncMock(return_value=[])

    app.dependency_overrides[get_consultation_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/consultations/patient/new-patient")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert len(data["consultations"]) == 0
