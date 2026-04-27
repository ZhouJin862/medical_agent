"""
Unified Skills Repository.

Integrates Claude Skills (file system) with Database Skills (legacy),
providing a single interface for skill access.
"""
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.models.skill_models import (
    SkillMetadata,
    SkillDefinition,
    SkillSource,
)
from src.domain.shared.services.skills_registry import SkillsRegistry
from src.infrastructure.persistence.models.skill_models import SkillModel

logger = logging.getLogger(__name__)


class SkillInfo:
    """Unified skill information."""

    def __init__(
        self,
        id: str,
        name: str,
        source: SkillSource,
        description: str,
        enabled: bool = True,
        layer: str = "domain",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.name = name
        self.source = source
        self.description = description
        self.enabled = enabled
        self.layer = layer
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source.value,
            "description": self.description,
            "enabled": self.enabled,
            "layer": self.layer,
            "metadata": self.metadata,
        }


class DatabaseSkillAdapter:
    """
    Adapter to convert database skills to skill models.
    """

    @staticmethod
    def to_metadata(skill: SkillModel) -> SkillMetadata:
        """Convert database skill to metadata."""
        # Use a dummy directory for database skills
        dummy_dir = Path(f"/db_skills/{skill.name}")

        return SkillMetadata(
            name=skill.name,
            description=skill.description or skill.display_name,
            directory=dummy_dir,
            source=SkillSource.DATABASE,
            enabled=skill.enabled,
            version=skill.version,
            # Map database fields to tags
            tags=skill.intent_keywords or [],
            # Map skill type to layer
            layer=DatabaseSkillAdapter._map_type_to_layer(skill.type),
        )

    @staticmethod
    def to_definition(skill: SkillModel) -> SkillDefinition:
        """Convert database skill to definition."""
        metadata = DatabaseSkillAdapter.to_metadata(skill)

        # Build content from database fields
        content = f"# {skill.display_name}\n\n"
        if skill.description:
            content += f"{skill.description}\n\n"

        # Add intent keywords
        if skill.intent_keywords:
            content += "## Intent Keywords\n\n"
            content += ", ".join(skill.intent_keywords) + "\n\n"

        # Add rule enhancement info if present
        if skill.config and skill.config.get("rule_enhancement"):
            rule_config = skill.config["rule_enhancement"]
            if rule_config.get("enabled"):
                content += "## Rule Enhancement\n\n"
                content += f"- Categories: {', '.join(rule_config.get('categories', []))}\n"
                if rule_config.get("disease_code"):
                    content += f"- Disease: {rule_config.get('disease_code')}\n"

        return SkillDefinition(
            metadata=metadata,
            content=content,
            reference_files=[],
            examples_files=[],
            scripts=[],
        )

    @staticmethod
    def _map_type_to_layer(skill_type: str) -> str:
        """Map database skill type to layer."""
        type_lower = skill_type.lower()
        if "generic" in type_lower:
            return "basic"
        elif "disease" in type_lower:
            return "domain"
        else:
            return "domain"


class UnifiedSkillsRepository:
    """
    Unified skills repository.

    Provides a single interface for accessing skills from both:
    - Claude Skills (file system)
    - Database Skills (legacy)
    """

    def __init__(self, session: AsyncSession, skills_dir: str = "skills"):
        """
        Initialize the unified repository.

        Args:
            session: Database session
            skills_dir: Directory for Claude Skills
        """
        self._session = session
        self._file_registry = SkillsRegistry(skills_dir)
        self._adapter = DatabaseSkillAdapter()

        # Cache for unified skill list
        self._unified_cache: Dict[str, SkillInfo] = {}
        self._cache_dirty = True

    async def list_skills(
        self,
        source: Optional[SkillSource] = None,
        enabled_only: bool = True,
        force_refresh: bool = False,
    ) -> List[SkillInfo]:
        """
        List all skills from both sources.

        Args:
            source: Filter by source (None = all)
            enabled_only: Only return enabled skills
            force_refresh: Force cache refresh

        Returns:
            List of skill information
        """
        if self._cache_dirty or force_refresh:
            await self._rebuild_cache()

        skills = list(self._unified_cache.values())

        # Apply filters
        if source:
            skills = [s for s in skills if s.source == source]

        if enabled_only:
            skills = [s for s in skills if s.enabled]

        # Sort: file skills first, then database; within each, by name
        skills.sort(key=lambda s: (s.source.value, s.name))

        return skills

    async def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """
        Get skill definition by ID.

        Auto-detects source and loads appropriately.

        Args:
            skill_id: Skill identifier

        Returns:
            Skill definition or None
        """
        # Try file registry first
        file_skill = self._file_registry.load_skill(skill_id)
        if file_skill:
            return file_skill

        # Try database
        db_skill = await self._load_database_skill(skill_id)
        if db_skill:
            return self._adapter.to_definition(db_skill)

        return None

    async def get_skill_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """
        Get skill metadata without loading full content.

        Args:
            skill_id: Skill identifier

        Returns:
            Skill metadata or None
        """
        # Try file registry first
        file_metadata = self._file_registry.get_skill_metadata(skill_id)
        if file_metadata:
            return file_metadata

        # Try database
        db_skill = await self._load_database_skill(skill_id)
        if db_skill:
            return self._adapter.to_metadata(db_skill)

        return None

    async def search_skills(
        self,
        query: str,
        source: Optional[SkillSource] = None,
    ) -> List[SkillInfo]:
        """
        Search skills by name or description.

        Args:
            query: Search query
            source: Filter by source

        Returns:
            Matching skills
        """
        skills = await self.list_skills(source=source, enabled_only=False)

        query_lower = query.lower()

        # Filter by matching name or description
        results = []
        for skill in skills:
            if (query_lower in skill.name.lower() or
                query_lower in skill.description.lower()):
                results.append(skill)

        return results

    async def get_skills_prompt(self) -> str:
        """
        Get formatted prompt listing all available skills.

        Useful for including in LLM system prompts.

        Returns:
            Formatted skill descriptions
        """
        skills = await self.list_skills(enabled_only=True)

        if not skills:
            return "No skills available."

        lines = ["## Available Skills\n"]

        # Group by layer
        by_layer: Dict[str, List[SkillInfo]] = {
            "basic": [],
            "domain": [],
            "composite": [],
        }

        for skill in skills:
            by_layer.setdefault(skill.layer, []).append(skill)

        for layer in ["basic", "domain", "composite"]:
            layer_skills = by_layer.get(layer, [])
            if not layer_skills:
                continue

            layer_name = layer.capitalize()
            lines.append(f"\n### {layer_name} Skills\n")

            for skill in layer_skills:
                source_tag = f"[{skill.source.value}]" if skill.source == SkillSource.DATABASE else ""
                lines.append(f"- **{skill.name}**: {skill.description} {source_tag}")

        return "\n".join(lines)

    async def load_reference_file(
        self,
        skill_name: str,
        filename: str,
    ) -> Optional[str]:
        """
        Load a reference file for a skill.

        Args:
            skill_name: Name of the skill
            filename: Name of the reference file

        Returns:
            File content or None
        """
        # Only file skills have reference files
        return self._file_registry.load_reference_file(skill_name, filename)

    def invalidate_cache(self, skill_id: Optional[str] = None):
        """
        Invalidate the unified cache.

        Args:
            skill_id: Specific skill to invalidate, or None for all
        """
        if skill_id:
            self._unified_cache.pop(skill_id, None)
            self._file_registry.invalidate_cache(skill_id)
        else:
            self._unified_cache.clear()
            self._file_registry.invalidate_cache()

        self._cache_dirty = True

    async def _rebuild_cache(self):
        """Rebuild the unified skills cache."""
        self._unified_cache.clear()

        # Add file skills
        for metadata in self._file_registry.scan_skills():
            self._unified_cache[metadata.name] = SkillInfo(
                id=metadata.name,
                name=metadata.name,
                source=metadata.source,
                description=metadata.description,
                enabled=metadata.enabled,
                layer=metadata.layer.value,
            )

        # Add database skills (avoid duplicates)
        try:
            stmt = select(SkillModel).where(SkillModel.enabled == True)
            result = await self._session.execute(stmt)
            db_skills = result.scalars().all()

            for skill in db_skills:
                # Skip if file skill with same name exists
                if skill.name in self._unified_cache:
                    continue

                self._unified_cache[skill.name] = SkillInfo(
                    id=str(skill.id),
                    name=skill.name,
                    source=SkillSource.DATABASE,
                    description=skill.description or skill.display_name,
                    enabled=skill.enabled,
                    layer=DatabaseSkillAdapter._map_type_to_layer(skill.type),
                    metadata={
                        "display_name": skill.display_name,
                        "version": skill.version,
                        "intent_keywords": skill.intent_keywords,
                    },
                )
        except Exception as e:
            logger.error(f"Error loading database skills: {e}")

        self._cache_dirty = False
        logger.info(f"Unified cache rebuilt: {len(self._unified_cache)} skills")

    async def _load_database_skill(self, skill_id: str) -> Optional[SkillModel]:
        """Load a skill from the database."""
        try:
            # Try by name first
            stmt = select(SkillModel).where(
                SkillModel.name == skill_id,
                SkillModel.enabled == True,
            )
            result = await self._session.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill:
                # Try by ID
                stmt = select(SkillModel).where(
                    SkillModel.id == skill_id,
                    SkillModel.enabled == True,
                )
                result = await self._session.execute(stmt)
                skill = result.scalar_one_or_none()

            return skill

        except Exception as e:
            logger.error(f"Error loading database skill {skill_id}: {e}")
            return None
