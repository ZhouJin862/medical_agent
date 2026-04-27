"""
Integration tests for Health Plan API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock

from src.interface.api.main import app
from src.interface.api.dependencies import get_health_plan_service


@pytest.fixture
def mock_health_plan_service():
    """Create mock health plan service."""
    service = Mock()

    # Mock generate_health_plan
    service.generate_health_plan = AsyncMock(return_value={
        "plan_id": "plan-1",
        "patient_id": "patient-123",
        "plan_type": "preventive",
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
        "total_prescriptions": 3,
        "prescriptions_by_type": {
            "diet": 1,
            "exercise": 1,
            "sleep": 1,
        },
        "prescription_details": [],
        "target_goals": {
            "total": 3,
            "active": 3,
            "achieved": 0,
        },
    })

    # Mock get_health_plan
    service.get_health_plan = AsyncMock(return_value={
        "plan_id": "plan-1",
        "patient_id": "patient-123",
        "plan_type": "preventive",
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
        "total_prescriptions": 3,
        "prescriptions_by_type": {
            "diet": 1,
            "exercise": 1,
            "sleep": 1,
        },
        "prescription_details": [],
        "target_goals": {
            "total": 3,
            "active": 3,
            "achieved": 0,
        },
    })

    # Mock get_patient_health_plans
    service.get_patient_health_plans = AsyncMock(return_value=[
        {
            "plan_id": "plan-1",
            "patient_id": "patient-123",
            "plan_type": "preventive",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "total_prescriptions": 3,
            "prescriptions_by_type": {},
            "prescription_details": [],
            "target_goals": {},
        },
    ])

    app.dependency_overrides[get_health_plan_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_health_plan_success(mock_health_plan_service):
    """Test generating a health plan successfully."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/plan/generate",
            json={
                "patient_id": "patient-123",
                "plan_type": "preventive",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["plan_id"] == "plan-1"
    assert data["plan_type"] == "preventive"
    assert data["total_prescriptions"] == 3
    mock_health_plan_service.generate_health_plan.assert_called_once()


@pytest.mark.asyncio
async def test_generate_health_plan_all_types(mock_health_plan_service):
    """Test generating different types of health plans."""
    plan_types = ["preventive", "treatment", "recovery", "chronic_management", "wellness"]

    for plan_type in plan_types:
        mock_health_plan_service.generate_health_plan.reset_mock()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/plan/generate",
                json={
                    "patient_id": "patient-123",
                    "plan_type": plan_type,
                },
            )

        assert response.status_code == 201
        mock_health_plan_service.generate_health_plan.assert_called_once()


@pytest.mark.asyncio
async def test_generate_health_plan_invalid_type():
    """Test generating a health plan with invalid type."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/plan/generate",
            json={
                "patient_id": "patient-123",
                "plan_type": "invalid_type",
            },
        )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_health_plan_by_id(mock_health_plan_service):
    """Test getting a health plan by ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/plan/plan-1")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "plan-1"
    assert data["patient_id"] == "patient-123"
    mock_health_plan_service.get_health_plan.assert_called_once()


@pytest.mark.asyncio
async def test_get_health_plan_not_found():
    """Test getting a non-existent health plan."""
    mock_service = Mock()
    mock_service.get_health_plan = AsyncMock(return_value=None)

    app.dependency_overrides[get_health_plan_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/plan/nonexistent-plan")

    app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_patient_health_plans(mock_health_plan_service):
    """Test getting all health plans for a patient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/plan/patient/patient-123")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    mock_health_plan_service.get_patient_health_plans.assert_called_once()


@pytest.mark.asyncio
async def test_get_patient_health_plans_empty():
    """Test getting health plans for a patient with no plans."""
    mock_service = Mock()
    mock_service.get_patient_health_plans = AsyncMock(return_value=[])

    app.dependency_overrides[get_health_plan_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/plan/patient/patient-no-plans")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
