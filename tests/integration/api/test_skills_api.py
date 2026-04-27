"""
Integration tests for Skills Management API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock

from src.interface.api.main import app
from src.interface.api.dependencies import get_skill_service


@pytest.fixture
def mock_skill_service():
    """Create mock skill service."""
    service = Mock()

    # Mock list_skills
    service.list_skills = AsyncMock(return_value=[
        {
            "id": "skill-1",
            "name": "hypertension_assessment",
            "display_name": "高血压评估",
            "description": "高血压风险评估",
            "type": "disease_specific",
            "category": "health_assessment",
            "enabled": True,
            "version": "1.0.0",
            "intent_keywords": ["高血压", "血压"],
            "config": None,
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
        },
    ])

    # Mock get_skill
    service.get_skill = AsyncMock(return_value={
        "id": "skill-1",
        "name": "hypertension_assessment",
        "display_name": "高血压评估",
        "description": "高血压风险评估",
        "type": "disease_specific",
        "category": "health_assessment",
        "enabled": True,
        "version": "1.0.0",
        "intent_keywords": ["高血压", "血压"],
        "config": None,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    })

    # Mock create_skill
    service.create_skill = AsyncMock(return_value={
        "id": "new-skill-1",
        "name": "diabetes_assessment",
        "display_name": "糖尿病评估",
        "description": "糖尿病风险评估",
        "type": "disease_specific",
        "category": "health_assessment",
        "enabled": True,
        "version": "1.0.0",
        "intent_keywords": ["糖尿病", "血糖"],
        "config": None,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    })

    # Mock update_skill
    service.update_skill = AsyncMock(return_value={
        "id": "skill-1",
        "name": "hypertension_assessment",
        "display_name": "高血压评估（更新版）",
        "description": "更新的高血压风险评估",
        "type": "disease_specific",
        "category": "health_assessment",
        "enabled": True,
        "version": "1.0.1",
        "intent_keywords": ["高血压", "血压", "头晕"],
        "config": None,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T11:00:00",
    })

    # Mock enable_skill
    service.enable_skill = AsyncMock(return_value={
        "id": "skill-1",
        "name": "hypertension_assessment",
        "display_name": "高血压评估",
        "description": "高血压风险评估",
        "type": "disease_specific",
        "category": "health_assessment",
        "enabled": True,
        "version": "1.0.0",
        "intent_keywords": ["高血压", "血压"],
        "config": None,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    })

    # Mock disable_skill
    service.disable_skill = AsyncMock(return_value={
        "id": "skill-1",
        "name": "hypertension_assessment",
        "display_name": "高血压评估",
        "description": "高血压风险评估",
        "type": "disease_specific",
        "category": "health_assessment",
        "enabled": False,
        "version": "1.0.0",
        "intent_keywords": ["高血压", "血压"],
        "config": None,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    })

    # Mock delete_skill
    service.delete_skill = AsyncMock(return_value=True)

    # Mock get_skill_prompts
    service.get_skill_prompts = AsyncMock(return_value=[
        {
            "id": "prompt-1",
            "skill_id": "skill-1",
            "prompt_type": "system",
            "content": "你是一位专业的健康管理助手...",
            "version": "1.0.0",
            "created_at": "2024-01-15T10:00:00",
        },
    ])

    # Mock update_skill_prompt
    service.update_skill_prompt = AsyncMock(return_value={
        "id": "prompt-1",
        "skill_id": "skill-1",
        "prompt_type": "system",
        "content": "更新后的系统提示词...",
        "version": "1.0.1",
        "created_at": "2024-01-15T10:00:00",
    })

    app.dependency_overrides[get_skill_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_skills(mock_skill_service):
    """Test listing all skills."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v2/skills")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total_count"] >= 1
    mock_skill_service.list_skills.assert_called_once()


@pytest.mark.asyncio
async def test_list_skills_with_filters(mock_skill_service):
    """Test listing skills with filters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v2/skills?skill_type=disease_specific&category=health_assessment&enabled_only=true",
        )

    assert response.status_code == 200
    mock_skill_service.list_skills.assert_called_once()


@pytest.mark.asyncio
async def test_get_skill_by_id(mock_skill_service):
    """Test getting a skill by ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v2/skills/skill-1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "skill-1"
    assert data["name"] == "hypertension_assessment"
    mock_skill_service.get_skill.assert_called_once()


@pytest.mark.asyncio
async def test_create_skill(mock_skill_service):
    """Test creating a new skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v2/skills",
            json={
                "name": "diabetes_assessment",
                "display_name": "糖尿病评估",
                "description": "糖尿病风险评估",
                "skill_type": "disease_specific",
                "category": "health_assessment",
                "intent_keywords": ["糖尿病", "血糖"],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "new-skill-1"
    assert data["name"] == "diabetes_assessment"
    mock_skill_service.create_skill.assert_called_once()


@pytest.mark.asyncio
async def test_create_skill_validation_error():
    """Test creating a skill with invalid data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v2/skills",
            json={
                "name": "test_skill",
                "display_name": "测试技能",
                "skill_type": "invalid_type",  # Invalid skill type
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_skill(mock_skill_service):
    """Test updating a skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v2/skills/skill-1",
            json={
                "display_name": "高血压评估（更新版）",
                "description": "更新的高血压风险评估",
                "intent_keywords": ["高血压", "血压", "头晕"],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "高血压评估（更新版）"
    mock_skill_service.update_skill.assert_called_once()


@pytest.mark.asyncio
async def test_enable_skill(mock_skill_service):
    """Test enabling a skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v2/skills/skill-1/enable")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    mock_skill_service.enable_skill.assert_called_once()


@pytest.mark.asyncio
async def test_disable_skill(mock_skill_service):
    """Test disabling a skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v2/skills/skill-1/disable")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    mock_skill_service.disable_skill.assert_called_once()


@pytest.mark.asyncio
async def test_delete_skill(mock_skill_service):
    """Test deleting a skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/v2/skills/skill-1")

    assert response.status_code == 204
    mock_skill_service.delete_skill.assert_called_once()


@pytest.mark.asyncio
async def test_get_skill_prompts(mock_skill_service):
    """Test getting prompts for a skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v2/skills/skill-1/prompts")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    mock_skill_service.get_skill_prompts.assert_called_once()


@pytest.mark.asyncio
async def test_update_skill_prompt(mock_skill_service):
    """Test updating a skill prompt."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v2/skills/skill-1/prompts",
            json={
                "prompt_type": "system",
                "content": "更新后的系统提示词...",
            },
        )

    assert response.status_code == 200
    mock_skill_service.update_skill_prompt.assert_called_once()
