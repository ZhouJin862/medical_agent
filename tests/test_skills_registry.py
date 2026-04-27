"""
Tests for SkillsRegistry service.

Verifies the progressive disclosure mechanism and skill loading.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.domain.shared.services.skills_registry import SkillsRegistry
from src.domain.shared.models.skill_models import SkillSource, SkillLayer


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory for testing."""
    temp_dir = tempfile.mkdtemp()
    skills_dir = Path(temp_dir) / "skills"
    skills_dir.mkdir()

    # Create test skill
    test_skill_dir = skills_dir / "test-skill"
    test_skill_dir.mkdir()

    # Create SKILL.md
    skill_md = test_skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
version: 1.0.0
layer: domain
tags: [test, example]
author: Test Author
---

# Test Skill

This is a test skill for testing the skills registry.

## Quick Start

Use this skill for testing.

## Advanced Features

See [reference/guide.md](reference/guide.md) for more details.
""")

    # Create reference file
    reference_dir = test_skill_dir / "reference"
    reference_dir.mkdir()
    guide_md = reference_dir / "guide.md"
    guide_md.write_text("# Test Guide\n\nThis is a test guide.")

    # Create scripts directory
    scripts_dir = test_skill_dir / "scripts"
    scripts_dir.mkdir()
    test_script = scripts_dir / "test.py"
    test_script.write_text("#!/usr/bin/env python3\nprint('Hello')")

    yield skills_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def registry(temp_skills_dir):
    """Create a SkillsRegistry instance for testing."""
    return SkillsRegistry(skills_dir=str(temp_skills_dir))


class TestSkillsRegistry:
    """Tests for SkillsRegistry."""

    def test_scan_skills(self, registry):
        """Test scanning skills directory."""
        skills = registry.scan_skills()

        assert len(skills) == 1
        assert skills[0].name == "test-skill"
        assert skills[0].description == "A test skill for unit testing"
        assert skills[0].layer == SkillLayer.DOMAIN
        assert skills[0].tags == ["test", "example"]
        assert skills[0].author == "Test Author"

    def test_get_skill_metadata(self, registry):
        """Test getting skill metadata without loading full content."""
        metadata = registry.get_skill_metadata("test-skill")

        assert metadata is not None
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill for unit testing"
        assert metadata.enabled is True

    def test_load_skill_definition(self, registry):
        """Test loading full skill definition."""
        definition = registry.load_skill("test-skill")

        assert definition is not None
        assert definition.metadata.name == "test-skill"
        assert "Test Skill" in definition.content
        assert definition.reference_files == ["guide.md"]
        assert definition.scripts == ["test.py"]

    def test_load_reference_file(self, registry):
        """Test loading a reference file."""
        content = registry.load_reference_file("test-skill", "guide.md")

        assert content is not None
        assert "Test Guide" in content
        assert "test guide" in content.lower()

    def test_list_reference_files(self, registry):
        """Test listing reference files."""
        files = registry.list_reference_files("test-skill")

        assert files == ["guide.md"]

    def test_cache_invalidation(self, registry):
        """Test cache invalidation."""
        # First load
        definition1 = registry.load_skill("test-skill")
        assert definition1 is not None

        # Should be cached
        definition2 = registry.load_skill("test-skill", use_cache=True)
        assert definition2 is not None
        assert definition1 is definition2  # Same object

        # Invalidate cache
        registry.invalidate_cache("test-skill")

        # Should reload
        definition3 = registry.load_skill("test-skill", use_cache=True)
        assert definition3 is not None

    def test_nonexistent_skill(self, registry):
        """Test handling of nonexistent skill."""
        metadata = registry.get_skill_metadata("nonexistent")
        assert metadata is None

        definition = registry.load_skill("nonexistent")
        assert definition is None

    def test_find_skills_by_tag(self, registry):
        """Test finding skills by tag."""
        test_skills = registry.find_skills_by_tag("test")
        assert len(test_skills) == 1
        assert test_skills[0].name == "test-skill"

        no_skills = registry.find_skills_by_tag("nonexistent")
        assert len(no_skills) == 0

    def test_find_skills_by_layer(self, registry):
        """Test finding skills by layer."""
        domain_skills = registry.find_skills_by_layer(SkillLayer.DOMAIN)
        assert len(domain_skills) == 1

        basic_skills = registry.find_skills_by_layer(SkillLayer.BASIC)
        assert len(basic_skills) == 0


class TestSkillFileWatcher:
    """Tests for SkillFileWatcher."""

    def test_file_watcher_initialization(self, registry):
        """Test initializing file watcher."""
        from src.domain.shared.services.skills_registry import SkillFileWatcher

        watcher = SkillFileWatcher(registry)
        assert watcher is not None

    def test_detect_changes(self, registry, temp_skills_dir):
        """Test detecting file changes."""
        from src.domain.shared.services.skills_registry import SkillFileWatcher
        import time

        watcher = SkillFileWatcher(registry)

        # Initial scan - no changes
        modified = watcher.check_for_changes()
        assert len(modified) == 0

        # Modify skill file
        skill_md = temp_skills_dir / "test-skill" / "SKILL.md"
        original_content = skill_md.read_text()
        skill_md.write_text(original_content + "\n# Modified")

        time.sleep(0.1)  # Ensure different mtime

        # Check for changes
        modified = watcher.check_for_changes()
        assert "test-skill" in modified


@pytest.mark.asyncio
class TestUnifiedSkillsRepository:
    """Tests for UnifiedSkillsRepository."""

    async def test_list_skills(self, temp_skills_dir):
        """Test listing skills from unified repository."""
        from src.domain.shared.services.unified_skills_repository import UnifiedSkillsRepository
        from unittest.mock import AsyncMock

        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar.return_value = None

        repository = UnifiedSkillsRepository(
            session=mock_session,
            skills_dir=str(temp_skills_dir),
        )

        skills = await repository.list_skills()

        assert len(skills) >= 1
        test_skill = next((s for s in skills if s.name == "test-skill"), None)
        assert test_skill is not None
        assert test_skill.source == SkillSource.FILE

    async def test_get_skills_prompt(self, temp_skills_dir):
        """Test generating skills prompt for LLM."""
        from src.domain.shared.services.unified_skills_repository import UnifiedSkillsRepository
        from unittest.mock import AsyncMock

        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar.return_value = None

        repository = UnifiedSkillsRepository(
            session=mock_session,
            skills_dir=str(temp_skills_dir),
        )

        prompt = await repository.get_skills_prompt()

        assert "## Available Skills" in prompt
        assert "test-skill" in prompt
        assert "A test skill for unit testing" in prompt

    async def test_search_skills(self, temp_skills_dir):
        """Test searching skills."""
        from src.domain.shared.services.unified_skills_repository import UnifiedSkillsRepository
        from unittest.mock import AsyncMock

        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar.return_value = None

        repository = UnifiedSkillsRepository(
            session=mock_session,
            skills_dir=str(temp_skills_dir),
        )

        results = await repository.search_skills("test")

        assert len(results) >= 1
        assert any(s.name == "test-skill" for s in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
