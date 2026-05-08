"""
System Prompt Service.

Manages system prompts with DB persistence, in-memory caching,
versioning, and template formatting.
"""
import json
import logging
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models.system_prompt_models import SystemPromptModel
from src.infrastructure.database import get_session_maker

logger = logging.getLogger(__name__)


class SystemPromptService:
    """
    Service for managing system prompts.

    Provides cached access to active prompts, CRUD operations,
    version management, and template formatting.
    """

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._loaded = False

    async def _ensure_cache(self) -> None:
        """Load all active prompts into memory cache if not already loaded."""
        if self._loaded:
            return

        try:
            session_maker = get_session_maker()
            async with session_maker() as session:
                result = await session.execute(
                    select(SystemPromptModel).where(SystemPromptModel.is_active == True)
                )
                prompts = result.scalars().all()
                self._cache = {p.prompt_key: p.prompt_content for p in prompts}
                self._loaded = True
                logger.info(f"Loaded {len(self._cache)} active system prompts into cache")
        except Exception as e:
            logger.warning(f"Failed to load system prompts from DB, using empty cache: {e}")
            self._loaded = True  # Mark as loaded to avoid retrying on every call

    async def get_prompt(self, key: str) -> Optional[str]:
        """
        Get active prompt content by key.

        Returns None if not found.
        """
        await self._ensure_cache()
        return self._cache.get(key)

    async def get_prompt_with_fallback(self, key: str, fallback: str) -> str:
        """
        Get active prompt content by key, returning fallback if not found.

        This is the primary method consumers should use.
        """
        content = await self.get_prompt(key)
        if content is not None:
            return content
        logger.warning(f"System prompt '{key}' not found in DB, using fallback")
        return fallback

    async def format_prompt(self, key: str, **kwargs) -> Optional[str]:
        """
        Get active prompt and format it with provided variables.

        Returns None if prompt not found. Variables not provided will be left as-is.
        """
        content = await self.get_prompt(key)
        if content is None:
            return None
        try:
            return content.format(**kwargs)
        except KeyError:
            # If some variables are missing, just return as-is
            return content

    def invalidate_cache(self) -> None:
        """Clear the in-memory cache. Next access will reload from DB."""
        self._cache.clear()
        self._loaded = False
        logger.info("System prompt cache invalidated")

    async def list_prompts(self) -> list[dict]:
        """
        List all active prompts with metadata.

        Returns list of dicts with key, description, version, updated_at.
        """
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                select(SystemPromptModel).where(SystemPromptModel.is_active == True)
                .order_by(SystemPromptModel.prompt_key)
            )
            prompts = result.scalars().all()
            return [
                {
                    "prompt_key": p.prompt_key,
                    "description": p.prompt_desc,
                    "version": p.prompt_version,
                    "variables": p.get_variables_list(),
                    "updated_at": p.updated_date.isoformat() if p.updated_date else None,
                    "id": p.id,
                }
                for p in prompts
            ]

    async def get_prompt_detail(self, key: str) -> Optional[dict]:
        """Get full details of the active version for a key."""
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                select(SystemPromptModel).where(
                    and_(
                        SystemPromptModel.prompt_key == key,
                        SystemPromptModel.is_active == True,
                    )
                )
            )
            prompt = result.scalar_one_or_none()
            if not prompt:
                return None
            data = prompt.to_dict()
            data["variables"] = prompt.get_variables_list() or None
            return data

    async def update_prompt(self, key: str, content: str, description: str | None = None) -> SystemPromptModel:
        """
        Create a new version of a prompt and activate it.

        Deactivates the previous active version for this key.
        """
        session_maker = get_session_maker()
        async with session_maker() as session:
            # Get current max version
            result = await session.execute(
                select(SystemPromptModel).where(
                    and_(
                        SystemPromptModel.prompt_key == key,
                        SystemPromptModel.is_active == True,
                    )
                )
            )
            current = result.scalar_one_or_none()

            new_version = 1
            old_description = ""
            variables = None

            if current:
                new_version = current.prompt_version + 1
                old_description = current.prompt_desc
                # Deactivate old version
                current.is_active = False

            if description is not None:
                old_description = description

            # Detect template variables
            variables = self._detect_variables(content)

            # Create new version
            new_prompt = SystemPromptModel(
                prompt_key=key,
                prompt_desc=old_description,
                prompt_content=content,
                prompt_version=new_version,
                is_active=True,
                prompt_variables=json.dumps(variables) if variables else None,
            )
            session.add(new_prompt)
            await session.commit()
            await session.refresh(new_prompt)

            # Invalidate cache
            self.invalidate_cache()

            logger.info(f"Created prompt '{key}' v{new_version}")
            return new_prompt

    async def activate_version(self, prompt_id: str) -> Optional[SystemPromptModel]:
        """Activate a specific version by its ID."""
        session_maker = get_session_maker()
        async with session_maker() as session:
            # Get the target version
            result = await session.execute(
                select(SystemPromptModel).where(SystemPromptModel.id == int(prompt_id))
            )
            target = result.scalar_one_or_none()
            if not target:
                return None

            # Deactivate all versions for this key
            result = await session.execute(
                select(SystemPromptModel).where(
                    and_(
                        SystemPromptModel.prompt_key == target.prompt_key,
                        SystemPromptModel.is_active == True,
                    )
                )
            )
            for active in result.scalars().all():
                active.is_active = False

            # Activate target
            target.is_active = True
            await session.commit()
            await session.refresh(target)

            self.invalidate_cache()

            logger.info(f"Activated prompt '{target.prompt_key}' v{target.prompt_version}")
            return target

    async def get_history(self, key: str) -> list[dict]:
        """Get version history for a prompt key."""
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                select(SystemPromptModel)
                .where(SystemPromptModel.prompt_key == key)
                .order_by(SystemPromptModel.prompt_version.desc())
            )
            prompts = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "prompt_key": p.prompt_key,
                    "version": p.prompt_version,
                    "is_active": p.is_active,
                    "description": p.prompt_desc,
                    "updated_at": p.updated_date.isoformat() if p.updated_date else None,
                }
                for p in prompts
            ]

    async def delete_version(self, prompt_id: str) -> bool:
        """Delete a specific version. Cannot delete active version."""
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                select(SystemPromptModel).where(SystemPromptModel.id == int(prompt_id))
            )
            target = result.scalar_one_or_none()
            if not target:
                return False
            if target.is_active:
                logger.warning(f"Cannot delete active version of '{target.prompt_key}'")
                return False

            await session.delete(target)
            await session.commit()
            logger.info(f"Deleted prompt '{target.prompt_key}' v{target.prompt_version}")
            return True

    @staticmethod
    def _detect_variables(content: str) -> list[str]:
        """Detect {variable} placeholders in content."""
        import re
        return list(set(re.findall(r'\{(\w+)\}', content)))


# Singleton instance for easy access
_prompt_service: SystemPromptService | None = None


def get_system_prompt_service() -> SystemPromptService:
    """Get or create the singleton SystemPromptService."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = SystemPromptService()
    return _prompt_service
