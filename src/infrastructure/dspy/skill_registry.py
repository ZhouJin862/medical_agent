"""
Skill Registry - Dynamic skill loading and management.

The SkillRegistry is responsible for:
- Loading skill definitions from database
- Managing skill lifecycle (enable/disable/reload)
- Providing skill lookup by name or intent
- Caching skill instances
"""

import logging
from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field

from .base_skill import BaseSkill, SkillConfig
from .signatures.base import BaseSignature, SignatureRegistry
from ..llm import ModelProvider

logger = logging.getLogger(__name__)


@dataclass
class SkillDefinition:
    """
    Skill definition as stored in the database.

    Attributes:
        id: Skill ID
        name: Unique skill name
        description: Human-readable description
        signature_name: Name of the DSPy signature to use
        model_provider: LLM provider to use
        model_config: Model configuration (temperature, max_tokens, etc.)
        enabled: Whether the skill is enabled
        intent_keywords: Keywords that trigger this skill
        knowledge_base_ids: Associated knowledge base IDs
        prompt_template: Optional custom prompt template
        system_prompt: Optional custom system prompt
    """

    id: str
    name: str
    description: str
    signature_name: str
    model_provider: str = "anthropic"
    model_config: dict = field(default_factory=dict)
    enabled: bool = True
    intent_keywords: list[str] = field(default_factory=list)
    knowledge_base_ids: list[str] = field(default_factory=list)
    prompt_template: Optional[str] = None
    system_prompt: Optional[str] = None


class SkillRegistry:
    """
    Registry for managing health assessment skills.

    Provides:
    - Dynamic skill loading from database
    - Skill instance caching
    - Intent-based skill lookup
    - Skill enable/disable management
    """

    _instance: Optional["SkillRegistry"] = None
    _skills: Dict[str, BaseSkill] = {}
    _definitions: Dict[str, SkillDefinition] = {}

    def __new__(cls) -> "SkillRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the registry."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            logger.info("SkillRegistry initialized")

    @classmethod
    async def load_from_database(cls, db_session) -> None:
        """
        Load skill definitions from the database.

        Args:
            db_session: Database session for querying skills
        """
        registry = cls()

        try:
            # Query skills from database
            from src.infrastructure.persistence.models.skill_models import Skill

            skills = db_session.query(Skill).filter(Skill.is_enabled == True).all()

            for skill in skills:
                definition = SkillDefinition(
                    id=str(skill.id),
                    name=skill.skill_name,
                    description=skill.skill_desc or "",
                    signature_name=skill.skill_type or "default",
                    model_provider=skill.model_provider or "anthropic",
                    model_config=skill.skill_config or {},
                    enabled=skill.is_enabled,
                    intent_keywords=skill.intent_keywords or [],
                    knowledge_base_ids=[
                        str(kb.id) for kb in skill.knowledge_bases
                    ] if skill.knowledge_bases else [],
                    prompt_template=skill.prompt_template,
                    system_prompt=skill.system_prompt,
                )

                registry._definitions[definition.name] = definition
                logger.info(f"Loaded skill definition: {definition.name}")

        except Exception as e:
            logger.error(f"Failed to load skills from database: {e}")

    @classmethod
    async def load_from_config(cls, skills_config: List[dict]) -> None:
        """
        Load skill definitions from configuration.

        Args:
            skills_config: List of skill configuration dictionaries
        """
        registry = cls()

        for config in skills_config:
            definition = SkillDefinition(
                id=config.get("id", config["name"]),
                name=config["name"],
                description=config.get("description", ""),
                signature_name=config.get("signature_name", "default"),
                model_provider=config.get("model_provider", "anthropic"),
                model_config=config.get("model_config", {}),
                enabled=config.get("enabled", True),
                intent_keywords=config.get("intent_keywords", []),
                knowledge_base_ids=config.get("knowledge_base_ids", []),
                prompt_template=config.get("prompt_template"),
                system_prompt=config.get("system_prompt"),
            )

            registry._definitions[definition.name] = definition
            logger.info(f"Loaded skill config: {definition.name}")

    def register(self, skill: BaseSkill) -> None:
        """
        Register a skill instance.

        Args:
            skill: Skill instance to register
        """
        self._skills[skill.config.name] = skill
        logger.info(f"Registered skill: {skill.config.name}")

    def unregister(self, name: str) -> None:
        """
        Unregister a skill.

        Args:
            name: Name of the skill to unregister
        """
        if name in self._skills:
            del self._skills[name]
            logger.info(f"Unregistered skill: {name}")

    def get(self, name: str) -> Optional[BaseSkill]:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            Skill instance or None if not found
        """
        # Return cached instance if available
        if name in self._skills:
            return self._skills[name]

        # Try to create from definition
        if name in self._definitions:
            from .skill_factory import SkillFactory
            skill = SkillFactory.create_from_definition(self._definitions[name])
            if skill:
                self._skills[name] = skill
            return skill

        return None

    def find_by_intent(self, user_input: str) -> List[BaseSkill]:
        """
        Find skills that can handle the given input.

        Args:
            user_input: User's input text

        Returns:
            List of matching skills (ordered by priority)
        """
        matches = []

        # Check for @skill_name syntax first
        for name, skill in self._skills.items():
            if f"@{name}" in user_input:
                return [skill]  # Exact match takes priority

        # Check intent keywords
        for skill in self._skills.values():
            if skill.can_handle(user_input):
                matches.append(skill)

        return matches

    def list_all(self) -> List[str]:
        """Get list of all registered skill names."""
        return list(self._skills.keys())

    def list_enabled(self) -> List[str]:
        """Get list of enabled skill names."""
        return [
            name for name, skill in self._skills.items()
            if skill.config.enabled
        ]

    def enable(self, name: str) -> bool:
        """
        Enable a skill.

        Args:
            name: Skill name

        Returns:
            True if successful
        """
        skill = self.get(name)
        if skill:
            skill.config.enabled = True
            logger.info(f"Enabled skill: {name}")
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        Disable a skill.

        Args:
            name: Skill name

        Returns:
            True if successful
        """
        skill = self.get(name)
        if skill:
            skill.config.enabled = False
            logger.info(f"Disabled skill: {name}")
            return True
        return False

    async def reload(self, name: str) -> Optional[BaseSkill]:
        """
        Reload a skill from its definition.

        Args:
            name: Skill name

        Returns:
            Reloaded skill instance or None
        """
        if name not in self._definitions:
            logger.error(f"Cannot reload skill '{name}': no definition found")
            return None

        # Remove cached instance
        if name in self._skills:
            del self._skills[name]

        # Recreate from definition
        return self.get(name)

    async def reload_all(self) -> None:
        """Reload all skills from their definitions."""
        logger.info("Reloading all skills...")
        self._skills.clear()

        for name in self._definitions:
            await self.reload(name)

        logger.info(f"Reloaded {len(self._skills)} skills")

    def get_skill_info(self, name: str) -> Optional[dict]:
        """
        Get information about a skill.

        Args:
            name: Skill name

        Returns:
            Skill information dictionary or None
        """
        skill = self.get(name)
        if skill:
            return skill.get_info()
        return None

    def get_all_info(self) -> List[dict]:
        """Get information about all registered skills."""
        return [
            self.get_skill_info(name)
            for name in self.list_all()
            if self.get_skill_info(name) is not None
        ]


def get_skill_registry() -> SkillRegistry:
    """
    Get the global SkillRegistry instance.

    Returns:
        SkillRegistry singleton
    """
    return SkillRegistry()
