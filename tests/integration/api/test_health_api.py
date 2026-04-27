"""
Integration tests for Health Assessment API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock

from src.interface.api.main import app
from src.interface.api.dependencies import get_health_assessment_service


@pytest.fixture
def mock_health_assessment_service():
    """Create mock health assessment service."""
    service = Mock()
    service.assess_vital_signs = AsyncMock(return_value={
        "assessment_id": "assess-1",
        "patient_id": "patient-123",
        "vital_signs": {
            "blood_pressure": {"systolic": 140, "diastolic": 90},
        },
        "assessments": {
            "blood_pressure": {
                "value": "140/90 mmHg",
                "classification": "高血压1级",
                "is_normal": False,
                "risk_level": "high_risk",
            },
        },
        "overall_risk": "high_risk",
        "recommendations": [
            {
                "category": "blood_pressure",
                "priority": "high",
                "title": "血压管理建议",
                "description": "建议减少钠盐摄入，增加运动",
            },
        ],
        "assessed_at": "2024-01-15T10:00:00",
    })
    service.get_patient_health_profile = AsyncMock(return_value={
        "patient_id": "patient-123",
        "name": "张三",
        "age": 45,
        "gender": "male",
        "phone": "13800138000",
    })

    app.dependency_overrides[get_health_assessment_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assess_health_success(mock_health_assessment_service):
    """Test health assessment with valid data."""
    mock_health_assessment_service.assess_vital_signs = AsyncMock(return_value={
        "assessment_id": "assess-1",
        "patient_id": "patient-123",
        "vital_signs": {
            "blood_pressure": {"systolic": 140, "diastolic": 90},
        },
        "assessments": {
            "blood_pressure": {
                "value": "140/90 mmHg",
                "classification": "高血压1级",
                "is_normal": False,
                "risk_level": "high_risk",
            },
        },
        "overall_risk": "high_risk",
        "recommendations": [
            {
                "category": "blood_pressure",
                "priority": "high",
                "title": "血压管理建议",
                "description": "建议减少钠盐摄入，增加运动",
            },
        ],
        "assessed_at": "2024-01-15T10:00:00",
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/health/assess",
            json={
                "patient_id": "patient-123",
                "systolic": 140,
                "diastolic": 90,
                "fasting_glucose": 6.5,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["assessment_id"] == "assess-1"
    assert data["overall_risk"] == "high_risk"
    assert len(data["recommendations"]) > 0
    mock_health_assessment_service.assess_vital_signs.assert_called_once()


@pytest.mark.asyncio
async def test_assess_health_multiple_vitals(mock_health_assessment_service):
    """Test health assessment with multiple vital signs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/health/assess",
            json={
                "patient_id": "patient-123",
                "systolic": 135,
                "diastolic": 85,
                "fasting_glucose": 5.8,
                "total_cholesterol": 5.5,
                "ldl_cholesterol": 3.5,
                "hdl_cholesterol": 1.2,
                "triglycerides": 1.8,
                "uric_acid": 380,
                "height": 175,
                "weight": 75,
            },
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_assess_health_no_vitals():
    """Test health assessment with no vital signs data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/health/assess",
            json={
                "patient_id": "patient-123",
                # No vital signs provided
            },
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_assess_health_invalid_values():
    """Test health assessment with invalid vital sign values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/health/assess",
            json={
                "patient_id": "patient-123",
                "systolic": 400,  # Invalid: exceeds max
            },
        )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_patient_health_profile(mock_health_assessment_service):
    """Test getting patient health profile."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/health/patient-123",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "patient-123"
    mock_health_assessment_service.get_patient_health_profile.assert_called_once()


@pytest.mark.asyncio
async def test_assess_health_lipid_profile_only(mock_health_assessment_service):
    """Test health assessment with only lipid profile data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/health/assess",
            json={
                "patient_id": "patient-123",
                "total_cholesterol": 6.2,
                "ldl_cholesterol": 4.1,
                "hdl_cholesterol": 0.9,
                "triglycerides": 2.5,
            },
        )

    assert response.status_code == 200
    mock_health_assessment_service.assess_vital_signs.assert_called_once()


@pytest.mark.asyncio
async def test_assess_health_bmi_only(mock_health_assessment_service):
    """Test health assessment with only BMI data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/health/assess",
            json={
                "patient_id": "patient-123",
                "height": 165,
                "weight": 70,
            },
        )

    assert response.status_code == 200
