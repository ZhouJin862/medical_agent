"""
Integration tests for Skills v2 API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from src.interface.api.main import app
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
)
from src.domain.shared.models.skill_models import SkillSource, SkillLayer


@pytest.fixture
def mock_unified_repository():
    """Create mock unified skills repository."""
    repo = Mock()

    # Create mock skill info - don't use real enums, just mock the value property
    mock_skill = Mock()
    mock_skill.to_dict = Mock(return_value={
        "id": "skill-1",
        "name": "hypertension_assessment",
        "description": "高血压风险评估",
        "source": "file",
        "layer": "domain",
        "enabled": True,
        "version": "1.0.0",
        "author": "test",
        "tags": ["health", "assessment"],
        "requires": [],
    })
    # Mock the source enum's value property
    mock_source = Mock()
    mock_source.value = "file"
    mock_skill.source = mock_source
    mock_skill.layer = "domain"  # String value for layer

    # Mock list_skills
    repo.list_skills = AsyncMock(return_value=[mock_skill])

    # Mock get_skill
    mock_skill_full = Mock()
    mock_skill_full.metadata.name = "hypertension_assessment"
    mock_skill_full.metadata.description = "高血压风险评估"
    # Mock source enum for metadata
    mock_metadata_source = Mock()
    mock_metadata_source.value = "file"
    mock_skill_full.metadata.source = mock_metadata_source
    # Mock layer enum for metadata
    mock_metadata_layer = Mock()
    mock_metadata_layer.value = "domain"
    mock_skill_full.metadata.layer = mock_metadata_layer
    mock_skill_full.metadata.enabled = True
    mock_skill_full.content = "Skill content here"
    mock_skill_full.reference_files = ["reference.md"]
    mock_skill_full.examples_files = ["examples.md"]
    mock_skill_full.scripts = ["script.py"]
    mock_skill_full.metadata.to_dict = Mock(return_value={
        "name": "hypertension_assessment",
        "description": "高血压风险评估",
        "source": "file",
        "layer": "domain",
        "enabled": True,
        "version": "1.0.0",
    })
    # Also set source/layer on the full skill object for consistency
    mock_skill_full.source = mock_source
    mock_skill_full.layer = "domain"

    repo.get_skill = AsyncMock(return_value=mock_skill_full)

    # Mock get_skill_metadata
    mock_metadata = Mock()
    mock_metadata.name = "hypertension_assessment"
    mock_metadata.description = "高血压风险评估"
    mock_metadata.source = mock_metadata_source
    mock_metadata.layer = mock_metadata_layer
    mock_metadata.enabled = True
    mock_metadata.version = "1.0.0"
    mock_metadata.author = "test"
    mock_metadata.tags = ["health"]
    mock_metadata.requires = []

    repo.get_skill_metadata = AsyncMock(return_value=mock_metadata)

    # Mock search_skills
    repo.search_skills = AsyncMock(return_value=[mock_skill])

    # Mock load_reference_file
    repo.load_reference_file = AsyncMock(return_value="Reference content here")

    # Mock get_reference_files
    repo.get_reference_files = AsyncMock(return_value=["reference.md"])

    # Mock get_skills_prompt
    repo.get_skills_prompt = AsyncMock(return_value="Skills prompt here")

    # Mock invalidate_cache
    repo.invalidate_cache = Mock()
    repo._cache_dirty = False
    repo._file_registry = Mock()
    repo._file_registry._skills_dir = Path("skills")

    # Import the dependency function from the module
    from src.interface.api.routes import skills_v2

    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_skills_v2(mock_unified_repository):
    """Test listing all skills via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v3/skills")

    assert response.status_code == 200
    data = response.json()
    # The endpoint returns skills field (not items)
    assert "skills" in data
    assert "total" in data
    assert isinstance(data["skills"], list)


@pytest.mark.asyncio
async def test_list_skills_v2_with_source_filter():
    """Test listing skills with source filter."""
    # Set up mock and override inline
    repo = Mock()
    mock_skill = Mock()
    mock_skill.to_dict = Mock(return_value={
        "id": "skill-1",
        "name": "hypertension_assessment",
        "description": "高血压风险评估",
        "source": "file",
        "layer": "domain",
        "enabled": True,
        "version": "1.0.0",
    })
    mock_source = Mock()
    mock_source.value = "file"
    mock_skill.source = mock_source
    mock_skill.layer = "domain"
    repo.list_skills = AsyncMock(return_value=[mock_skill])

    from src.interface.api.routes import skills_v2
    app.dependency_overrides.clear()  # Clear any existing overrides first
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v3/skills?source=file")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_skills_v2_invalid_source():
    """Test listing skills with invalid source filter."""
    # Set up a mock that will be used
    repo = Mock()
    mock_skill = Mock()
    mock_skill.to_dict = Mock(return_value={
        "id": "skill-1",
        "name": "test_skill",
        "description": "Test skill",
        "source": "file",
        "layer": "domain",
        "enabled": True,
        "version": "1.0.0",
    })
    mock_source = Mock()
    mock_source.value = "file"
    mock_skill.source = mock_source
    mock_skill.layer = "domain"
    repo.list_skills = AsyncMock(return_value=[mock_skill])

    from src.interface.api.routes import skills_v2
    app.dependency_overrides.clear()
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v3/skills?source=invalid")

        # Note: SkillSource(str, Enum) accepts any string as a constructor
        # but the endpoint validates it and returns 400 for invalid values
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_skill_v2_by_name():
    """Test getting skill details by name via v2 API."""
    # Set up mock and override inline
    repo = Mock()
    mock_skill_full = Mock()
    mock_skill_full.metadata.name = "hypertension_assessment"
    mock_skill_full.metadata.description = "高血压风险评估"
    mock_metadata_source = Mock()
    mock_metadata_source.value = "file"
    mock_skill_full.metadata.source = mock_metadata_source
    mock_metadata_layer = Mock()
    mock_metadata_layer.value = "domain"
    mock_skill_full.metadata.layer = mock_metadata_layer
    mock_skill_full.metadata.enabled = True
    mock_skill_full.content = "Skill content here"
    mock_skill_full.reference_files = ["reference.md"]
    mock_skill_full.examples_files = ["examples.md"]
    mock_skill_full.scripts = ["script.py"]
    mock_skill_full.metadata.to_dict = Mock(return_value={
        "name": "hypertension_assessment",
        "description": "高血压风险评估",
        "source": "file",
        "layer": "domain",
        "enabled": True,
        "version": "1.0.0",
    })
    mock_skill_full.source = mock_metadata_source
    mock_skill_full.layer = "domain"

    repo.get_skill = AsyncMock(return_value=mock_skill_full)

    from src.interface.api.routes import skills_v2
    app.dependency_overrides.clear()  # Clear any existing overrides first
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v3/skills/hypertension_assessment")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "hypertension_assessment"
        assert data["source"] == "file"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_skill_v2_not_found():
    """Test getting non-existent skill via v2 API."""
    mock_repo = Mock()
    mock_repo.get_skill = AsyncMock(return_value=None)

    from src.interface.api.routes import skills_v2
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: mock_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v3/skills/nonexistent_skill")

    app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_skill_metadata_v2(mock_unified_repository):
    """Test getting skill metadata via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v3/skills/hypertension_assessment/metadata")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "description" in data
    assert "version" in data
    mock_unified_repository.get_skill_metadata.assert_called_once()


@pytest.mark.asyncio
async def test_search_skills_v2(mock_unified_repository):
    """Test searching skills via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v3/skills/search",
            json={"query": "hypertension"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    mock_unified_repository.search_skills.assert_called_once()


@pytest.mark.asyncio
async def test_search_skills_v2_with_validation_error():
    """Test searching skills with invalid query."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v3/skills/search",
            json={},  # Missing query
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_reference_file_v2(mock_unified_repository):
    """Test getting skill reference file via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v3/skills/hypertension_assessment/reference/reference.md"
        )

    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert "content" in data
    mock_unified_repository.load_reference_file.assert_called_once()


@pytest.mark.asyncio
async def test_get_reference_file_v2_not_found():
    """Test getting non-existent reference file via v2 API."""
    mock_repo = Mock()
    mock_repo.load_reference_file = AsyncMock(return_value=None)

    from src.interface.api.routes import skills_v2
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: mock_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v3/skills/hypertension_assessment/reference/nonexistent.md"
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_reference_files_v2(mock_unified_repository):
    """Test listing reference files for a skill via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v3/skills/hypertension_assessment/references"
        )

    assert response.status_code == 200
    data = response.json()
    assert "skill_name" in data
    assert "reference_files" in data


@pytest.mark.asyncio
async def test_get_skills_prompt_v2(mock_unified_repository):
    """Test getting skills prompt for LLM via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v3/skills/prompt/llm")

    assert response.status_code == 200
    data = response.json()
    assert "prompt" in data
    assert "skill_count" in data
    mock_unified_repository.get_skills_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_skill_cache_v2():
    """Test refreshing skill cache via v2 API."""
    mock_repo = Mock()
    mock_repo.invalidate_cache = Mock()

    from src.interface.api.routes import skills_v2
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: mock_repo

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v3/skills/cache/refresh")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_get_skills_stats_v2(mock_unified_repository):
    """Test getting skills statistics via v2 API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v3/skills/stats/summary")

    assert response.status_code == 200
    data = response.json()
    assert "total_skills" in data
    assert "enabled_skills" in data
    assert "by_source" in data


@pytest.mark.asyncio
async def test_skills_health_check_v2():
    """Test skills health check via v2 API."""
    # Set up mock and override inline
    repo = Mock()
    mock_skill = Mock()
    mock_skill.to_dict = Mock(return_value={
        "id": "skill-1",
        "name": "test_skill",
        "enabled": True,
    })
    mock_source = Mock()
    mock_source.value = "file"
    mock_skill.source = mock_source
    mock_skill.layer = "domain"
    repo.list_skills = AsyncMock(return_value=[mock_skill])

    from src.interface.api.routes import skills_v2
    app.dependency_overrides.clear()  # Clear any existing overrides first
    app.dependency_overrides[skills_v2.get_unified_repository] = lambda: repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v3/skills/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "total_skills" in data
    finally:
        app.dependency_overrides.clear()
