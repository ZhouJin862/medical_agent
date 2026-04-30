"""
Skill management application service.

Orchestrates skill CRUD operations, enabling/disabling, and reloading.
"""
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models.skill_models import (
    SkillModel,
    SkillType,
    SkillCategory,
    SkillPromptModel,
    SkillModelConfigModel,
    ModelProvider,
)
from src.domain.shared.exceptions.domain_exception import DomainException

logger = logging.getLogger(__name__)


class SkillNotFoundException(DomainException):
    """Exception raised when a skill is not found."""

    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id
        super().__init__(f"Skill with ID '{skill_id}' not found")


class SkillAlreadyExistsException(DomainException):
    """Exception raised when a skill already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Skill with name '{name}' already exists")


class SkillManagementApplicationService:
    """
    Application service for skill management operations.

    Coordinates skill creation, updates, enabling/disabling,
    and reloading from database.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize SkillManagementApplicationService.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create_skill(
        self,
        name: str,
        display_name: str,
        skill_type: str,
        category: str | None = None,
        description: str | None = None,
        intent_keywords: list[str] | None = None,
        config: dict[str, Any] | None = None,
        model_config: dict[str, Any] | None = None,
        prompts: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new skill.

        Args:
            name: Unique skill name identifier
            display_name: Human-readable display name
            skill_type: Type of skill (generic, disease_specific, etc.)
            category: Category of skill
            description: Skill description
            intent_keywords: Keywords for intent matching
            config: Additional configuration
            model_config: LLM model configuration
            prompts: Prompt templates by type

        Returns:
            Created skill data
        """
        # Check if skill already exists
        existing = await self._get_skill_by_name(name)
        if existing:
            raise SkillAlreadyExistsException(name)

        # Create skill
        skill = SkillModel(
            skill_name=name,
            display_name=display_name,
            skill_desc=description,
            skill_type=SkillType(skill_type),
            category=SkillCategory(category) if category else None,
            is_enabled=True,
            skill_version="1.0.0",
            intent_keywords=intent_keywords,
            skill_config=config,
        )
        self._session.add(skill)
        await self._session.flush()

        # Create model config if provided
        if model_config:
            skill_model_config = SkillModelConfigModel(
                skill_id=skill.id,
                model_provider=ModelProvider(
                    model_config.get("provider", "internal")
                ),
                model_name=model_config.get("model_name", "glm-5"),
                temperature=model_config.get("temperature"),
                max_tokens=model_config.get("max_tokens"),
                top_p=model_config.get("top_p"),
                model_config=model_config.get("extra_config"),
            )
            self._session.add(skill_model_config)

        # Create prompts if provided
        if prompts:
            for prompt_type, content in prompts.items():
                prompt = SkillPromptModel(
                    skill_id=skill.id,
                    prompt_type=prompt_type,
                    prompt_content=content,
                    prompt_version="1.0.0",
                )
                self._session.add(prompt)

        logger.info(f"Created skill {name} with ID {skill.id}")

        # Commit and refresh before to_dict to avoid lazy-loading issues
        await self._session.commit()
        await self._session.refresh(skill)

        return skill.to_dict()

    async def get_skill(self, skill_id: str) -> dict[str, Any]:
        """
        Get skill by ID.

        Args:
            skill_id: Skill identifier

        Returns:
            Skill data

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        return skill.to_dict()

    async def list_skills(
        self,
        skill_type: str | None = None,
        category: str | None = None,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List skills with optional filtering.

        Args:
            skill_type: Filter by skill type
            category: Filter by category
            enabled_only: Only return enabled skills

        Returns:
            List of skill data
        """
        stmt = select(SkillModel)

        conditions = []
        if skill_type:
            conditions.append(SkillModel.skill_type == SkillType(skill_type))
        if category:
            conditions.append(SkillModel.category == SkillCategory(category))
        if enabled_only:
            conditions.append(SkillModel.is_enabled == True)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(SkillModel.created_date.desc())

        result = await self._session.execute(stmt)
        skills = result.scalars().all()

        return [skill.to_dict() for skill in skills]

    async def update_skill(
        self,
        skill_id: str,
        display_name: str | None = None,
        description: str | None = None,
        intent_keywords: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing skill.

        Args:
            skill_id: Skill identifier
            display_name: New display name
            description: New description
            intent_keywords: New intent keywords
            config: New configuration

        Returns:
            Updated skill data

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        if display_name is not None:
            skill.display_name = display_name
        if description is not None:
            skill.skill_desc = description
        if intent_keywords is not None:
            skill.intent_keywords = intent_keywords
        if config is not None:
            skill.skill_config = config

        # Update version
        self._increment_version(skill)

        await self._session.flush()

        logger.info(f"Updated skill {skill_id}")

        return skill.to_dict()

    async def enable_skill(self, skill_id: str) -> dict[str, Any]:
        """
        Enable a skill.

        Args:
            skill_id: Skill identifier

        Returns:
            Updated skill data

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        skill.is_enabled = True
        await self._session.flush()

        logger.info(f"Enabled skill {skill_id}")

        return skill.to_dict()

    async def disable_skill(self, skill_id: str) -> dict[str, Any]:
        """
        Disable a skill.

        Args:
            skill_id: Skill identifier

        Returns:
            Updated skill data

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        skill.is_enabled = False
        await self._session.flush()

        logger.info(f"Disabled skill {skill_id}")

        return skill.to_dict()

    async def reload_skill(self, skill_id: str) -> dict[str, Any]:
        """
        Reload a skill from database (refreshes cache if applicable).

        Args:
            skill_id: Skill identifier

        Returns:
            Reloaded skill data

        Raises:
            SkillNotFoundException: If skill not found
        """
        # Refresh from database
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        await self._session.refresh(skill)

        logger.info(f"Reloaded skill {skill_id}")

        return skill.to_dict()

    async def delete_skill(self, skill_id: str) -> bool:
        """
        Delete a skill.

        Args:
            skill_id: Skill identifier

        Returns:
            True if skill was deleted

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        await self._session.delete(skill)
        await self._session.flush()

        logger.info(f"Deleted skill {skill_id}")

        return True

    async def get_skill_prompts(self, skill_id: str) -> list[dict[str, Any]]:
        """
        Get all prompts for a skill.

        Args:
            skill_id: Skill identifier

        Returns:
            List of prompt data
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        stmt = select(SkillPromptModel).where(
            SkillPromptModel.skill_id == skill.id
        )
        result = await self._session.execute(stmt)
        prompts = result.scalars().all()

        return [prompt.to_dict() for prompt in prompts]

    async def update_skill_prompt(
        self,
        skill_id: str,
        prompt_type: str,
        content: str,
    ) -> dict[str, Any]:
        """
        Update or create a prompt for a skill.

        Args:
            skill_id: Skill identifier
            prompt_type: Type of prompt
            content: Prompt content

        Returns:
            Updated/created prompt data

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        # Check if prompt exists
        stmt = select(SkillPromptModel).where(
            and_(
                SkillPromptModel.skill_id == skill.id,
                SkillPromptModel.prompt_type == prompt_type,
            )
        )
        result = await self._session.execute(stmt)
        prompt = result.scalar_one_or_none()

        if prompt:
            # Update existing
            prompt.prompt_content = content
            self._increment_version(prompt)
        else:
            # Create new
            prompt = SkillPromptModel(
                skill_id=skill.id,
                prompt_type=prompt_type,
                prompt_content=content,
                prompt_version="1.0.0",
            )
            self._session.add(prompt)

        await self._session.flush()

        logger.info(f"Updated prompt {prompt_type} for skill {skill_id}")

        return prompt.to_dict()

    async def get_skill_model_config(self, skill_id: str) -> dict[str, Any] | None:
        """
        Get model configuration for a skill.

        Args:
            skill_id: Skill identifier

        Returns:
            Model config data or None
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        stmt = select(SkillModelConfigModel).where(
            SkillModelConfigModel.skill_id == skill.id
        )
        result = await self._session.execute(stmt)
        config = result.scalar_one_or_none()

        return config.to_dict() if config else None

    async def update_skill_model_config(
        self,
        skill_id: str,
        model_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update model configuration for a skill.

        Args:
            skill_id: Skill identifier
            model_config: New model configuration

        Returns:
            Updated model config data

        Raises:
            SkillNotFoundException: If skill not found
        """
        skill = await self._get_skill_by_id(skill_id)
        if not skill:
            raise SkillNotFoundException(skill_id)

        stmt = select(SkillModelConfigModel).where(
            SkillModelConfigModel.skill_id == skill.id
        )
        result = await self._session.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            # Update existing
            if "provider" in model_config:
                config.model_provider = ModelProvider(model_config["provider"])
            if "model_name" in model_config:
                config.model_name = model_config["model_name"]
            if "temperature" in model_config:
                config.temperature = model_config["temperature"]
            if "max_tokens" in model_config:
                config.max_tokens = model_config["max_tokens"]
            if "top_p" in model_config:
                config.top_p = model_config["top_p"]
            if "extra_config" in model_config:
                config.model_config = model_config["extra_config"]
        else:
            # Create new
            config = SkillModelConfigModel(
                skill_id=skill.id,
                model_provider=ModelProvider(
                    model_config.get("provider", "internal")
                ),
                model_name=model_config.get("model_name", "glm-5"),
                temperature=model_config.get("temperature"),
                max_tokens=model_config.get("max_tokens"),
                top_p=model_config.get("top_p"),
                model_config=model_config.get("extra_config"),
            )
            self._session.add(config)

        await self._session.flush()

        logger.info(f"Updated model config for skill {skill_id}")

        return config.to_dict()

    async def _get_skill_by_id(self, skill_id: str) -> SkillModel | None:
        """Get skill model by ID."""
        stmt = select(SkillModel).where(SkillModel.id == int(skill_id))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_skill_by_name(self, name: str) -> SkillModel | None:
        """Get skill model by name."""
        stmt = select(SkillModel).where(SkillModel.skill_name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _increment_version(self, model: Any) -> None:
        """Increment version of a model."""
        current_version = model.skill_version if hasattr(model, 'skill_version') else model.prompt_version
        try:
            major, minor, patch = current_version.split(".")
            patch = str(int(patch) + 1)
            new_version = f"{major}.{minor}.{patch}"
        except (ValueError, AttributeError):
            new_version = "2.0.0"
        if hasattr(model, 'skill_version'):
            model.skill_version = new_version
        else:
            model.prompt_version = new_version
