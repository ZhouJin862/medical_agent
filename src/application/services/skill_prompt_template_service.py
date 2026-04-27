"""
Skill Prompt Template Service

Provides dynamic prompt template management for skills.
Supports loading prompt templates from database and caching them.
"""

import logging
import json
from typing import Any, Optional
from functools import lru_cache
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session_context
from src.infrastructure.persistence.models.skill_models import SkillPromptModel, SkillModel
from src.infrastructure.dspy.signatures.base import BaseSignature, InputField, OutputField, FieldType

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """
    Prompt template data container.

    Attributes:
        skill_id: Associated skill ID
        prompt_type: Type of prompt (system, user, etc.)
        content: Template content with placeholders
        version: Template version
        variables: List of variable names used in template
    """
    skill_id: str
    prompt_type: str
    content: str
    version: str
    variables: list[str]

    def format(self, **kwargs) -> str:
        """
        Format the template with provided values.

        Args:
            **kwargs: Values to substitute

        Returns:
            Formatted string
        """
        try:
            return self.content.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")


class SkillPromptTemplateService:
    """
    Service for managing skill prompt templates.

    Provides:
    - Loading prompts from database
    - Creating and updating prompts
    - Caching prompts for performance
    - Dynamic signature creation
    """

    _prompt_cache: dict[str, dict[str, PromptTemplate]] = {}

    @classmethod
    async def load_prompt_templates(
        cls,
        skill_id: str,
        session: Optional[AsyncSession] = None,
    ) -> dict[str, PromptTemplate]:
        """
        Load all prompt templates for a skill.

        Args:
            skill_id: Skill ID
            session: Optional database session

        Returns:
            Dict mapping prompt_type to PromptTemplate
        """
        # Check cache first
        if skill_id in cls._prompt_cache:
            return cls._prompt_cache[skill_id]

        async with get_db_session_context() as session:
            result = await session.execute(
                select(SkillPromptModel).where(
                    SkillPromptModel.skill_id == skill_id
                )
            )
            prompt_models = result.scalars().all()

        templates = {}
        for model in prompt_models:
            template = PromptTemplate(
                skill_id=model.skill_id,
                prompt_type=model.prompt_type,
                content=model.content,
                version=model.version,
                variables=model.variables or [],
            )
            templates[model.prompt_type] = template

        # Cache the results
        cls._prompt_cache[skill_id] = templates

        return templates

    @classmethod
    async def get_system_prompt(
        cls,
        skill_id: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[PromptTemplate]:
        """
        Get the system prompt for a skill.

        Args:
            skill_id: Skill ID
            session: Optional database session

        Returns:
            System prompt template or None
        """
        templates = await cls.load_prompt_templates(skill_id, session)
        return templates.get("system")

    @classmethod
    async def get_user_prompt(
        cls,
        skill_id: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[PromptTemplate]:
        """
        Get the user prompt template for a skill.

        Args:
            skill_id: Skill ID
            session: Optional database session

        Returns:
            User prompt template or None
        """
        templates = await cls.load_prompt_templates(skill_id, session)
        return templates.get("user")

    @classmethod
    def invalidate_cache(cls, skill_id: Optional[str] = None) -> None:
        """
        Invalidate cached prompt templates.

        Args:
            skill_id: Specific skill ID to invalidate, or None to clear all
        """
        if skill_id:
            cls._prompt_cache.pop(skill_id, None)
        else:
            cls._prompt_cache.clear()

    @classmethod
    async def create_prompt_template(
        cls,
        skill_id: str,
        prompt_type: str,
        content: str,
        version: str = "1.0.0",
        variables: Optional[list[str]] = None,
        session: Optional[AsyncSession] = None,
    ) -> PromptTemplate:
        """
        Create a new prompt template.

        Args:
            skill_id: Associated skill ID
            prompt_type: Type of prompt (system, user, etc.)
            content: Template content
            version: Template version
            variables: List of variable names
            session: Optional database session

        Returns:
            Created prompt template
        """
        if session is None:
            async with get_db_session_context() as session:
                return await cls._create_prompt_impl(
                    session, skill_id, prompt_type, content, version, variables
                )
        else:
            return await cls._create_prompt_impl(
                session, skill_id, prompt_type, content, version, variables
            )

    @classmethod
    async def _create_prompt_impl(
        cls,
        session: AsyncSession,
        skill_id: str,
        prompt_type: str,
        content: str,
        version: str,
        variables: Optional[list[str]],
    ) -> PromptTemplate:
        """Implementation of prompt creation."""
        # Extract variables from content if not provided
        if variables is None:
            variables = cls._extract_variables(content)

        model = SkillPromptModel(
            skill_id=skill_id,
            prompt_type=prompt_type,
            content=content,
            version=version,
            variables=variables,
        )
        session.add(model)
        await session.commit()

        # Invalidate cache for this skill
        cls.invalidate_cache(skill_id)

        return PromptTemplate(
            skill_id=model.skill_id,
            prompt_type=model.prompt_type,
            content=model.content,
            version=model.version,
            variables=model.variables,
        )

    @classmethod
    async def update_prompt_template(
        cls,
        skill_id: str,
        prompt_type: str,
        content: str,
        version: Optional[str] = None,
        variables: Optional[list[str]] = None,
        session: Optional[AsyncSession] = None,
    ) -> PromptTemplate:
        """
        Update an existing prompt template.

        Args:
            skill_id: Associated skill ID
            prompt_type: Type of prompt to update
            content: New template content
            version: New version (optional, auto-increments if not provided)
            variables: List of variable names
            session: Optional database session

        Returns:
            Updated prompt template
        """
        async with get_db_session_context() as sess:
            result = await sess.execute(
                select(SkillPromptModel).where(
                    SkillPromptModel.skill_id == skill_id,
                    SkillPromptModel.prompt_type == prompt_type,
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                raise ValueError(
                    f"Prompt template not found: skill_id={skill_id}, "
                    f"prompt_type={prompt_type}"
                )

            # Auto-increment version if not provided
            if version is None:
                major, minor = map(int, model.version.split("."))
                version = f"{major}.{minor + 1}.0"

            model.content = content
            model.version = version
            if variables is not None:
                model.variables = variables
            else:
                model.variables = cls._extract_variables(content)

            await sess.commit()

        # Invalidate cache
        cls.invalidate_cache(skill_id)

        return PromptTemplate(
            skill_id=model.skill_id,
            prompt_type=model.prompt_type,
            content=model.content,
            version=model.version,
            variables=model.variables,
        )

    @classmethod
    async def delete_prompt_template(
        cls,
        skill_id: str,
        prompt_type: str,
        session: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Delete a prompt template.

        Args:
            skill_id: Associated skill ID
            prompt_type: Type of prompt to delete
            session: Optional database session

        Returns:
            True if deleted, False if not found
        """
        async with get_db_session_context() as sess:
            result = await sess.execute(
                select(SkillPromptModel).where(
                    SkillPromptModel.skill_id == skill_id,
                    SkillPromptModel.prompt_type == prompt_type,
                )
            )
            model = result.scalar_one_or_none()

            if model:
                await sess.delete(model)
                await sess.commit()
                cls.invalidate_cache(skill_id)
                return True

            return False

    @classmethod
    def _extract_variables(cls, content: str) -> list[str]:
        """
        Extract variable names from template content.

        Looks for {variable} patterns in the template.

        Args:
            content: Template content

        Returns:
            List of unique variable names
        """
        import re

        pattern = r"\{(\w+)\}"
        variables = re.findall(pattern, content)
        return list(set(variables))

    @classmethod
    async def create_dynamic_signature(
        cls,
        skill_id: str,
        input_fields: list[dict],
        output_fields: list[dict],
        session: Optional[AsyncSession] = None,
    ) -> BaseSignature:
        """
        Create a dynamic signature with prompts from database.

        Args:
            skill_id: Skill ID to load prompts for
            input_fields: List of input field definitions
            output_fields: List of output field definitions
            session: Optional database session

        Returns:
            Dynamic signature class with loaded prompts
        """
        # Load prompt templates
        templates = await cls.load_prompt_templates(skill_id, session)

        # Convert field dicts to field objects
        input_field_objs = []
        for field_def in input_fields:
            field_type = FieldType(field_def.get("field_type", "string"))
            input_field_objs.append(
                InputField(
                    name=field_def["name"],
                    description=field_def["description"],
                    field_type=field_type,
                    required=field_def.get("required", True),
                )
            )

        output_field_objs = []
        for field_def in output_fields:
            field_type = FieldType(field_def.get("field_type", "json"))
            output_field_objs.append(
                OutputField(
                    name=field_def["name"],
                    description=field_def["description"],
                    field_type=field_type,
                    required=field_def.get("required", True),
                )
            )

        # Get system prompt and template from database
        system_prompt = templates.get("system", PromptTemplate(
            skill_id=skill_id,
            prompt_type="system",
            content="You are a helpful health assistant.",
            version="1.0.0",
            variables=[],
        )).content

        user_template = templates.get("user", PromptTemplate(
            skill_id=skill_id,
            prompt_type="user",
            content="Please analyze the following: {input}",
            version="1.0.0",
            variables=["input"],
        )).content

        # Create signature class using BaseSignature's dynamic creation
        from src.infrastructure.dspy.signatures.base import SignatureRegistry

        signature_name = f"Dynamic_{skill_id}"
        signature_class = SignatureRegistry.create_signature(
            signature_name,
            custom_fields={
                "inputs": input_field_objs,
                "outputs": output_field_objs,
                "system_prompt": system_prompt,
                "prompt_template": user_template,
            }
        )

        return signature_class

    @classmethod
    async def list_all_skill_prompts(
        cls,
        session: Optional[AsyncSession] = None,
    ) -> list[dict]:
        """
        List all prompt templates across all skills.

        Args:
            session: Optional database session

        Returns:
            List of prompt template info
        """
        async with get_db_session_context() as sess:
            result = await sess.execute(
                select(SkillPromptModel, SkillModel.name)
                .join(SkillModel, SkillPromptModel.skill_id == SkillModel.id)
            )
            rows = result.all()

        return [
            {
                "skill_id": row.SkillPromptModel.skill_id,
                "skill_name": row.name,
                "prompt_type": row.SkillPromptModel.prompt_type,
                "version": row.SkillPromptModel.version,
                "variables": row.SkillPromptModel.variables or [],
                "content_preview": row.SkillPromptModel.content[:100] + "...",
            }
            for row in rows
        ]
