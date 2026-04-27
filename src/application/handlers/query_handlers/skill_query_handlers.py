"""
Skill query handlers.

Handles queries for skill-related read operations.
"""
import logging
from typing import Any

from src.application.queries.skill_queries import (
    GetSkillListQuery,
    GetSkillByIdQuery,
    GetSkillPromptsQuery,
    GetSkillModelConfigQuery,
)
from src.application.services.skill_management_service import (
    SkillManagementApplicationService,
    SkillNotFoundException,
)

logger = logging.getLogger(__name__)


class SkillQueryHandlers:
    """
    Handlers for skill-related queries.

    Coordinates with skill management service to execute queries.
    """

    def __init__(
        self,
        skill_service: SkillManagementApplicationService,
    ) -> None:
        """
        Initialize skill query handlers.

        Args:
            skill_service: Skill management service
        """
        self._skill_service = skill_service

    async def handle_get_skill_list(
        self,
        query: GetSkillListQuery,
    ) -> list[dict[str, Any]]:
        """
        Handle get skill list query.

        Args:
            query: GetSkillListQuery

        Returns:
            List of skill data
        """
        logger.info(
            f"Getting skill list with filters: "
            f"type={query.skill_type}, category={query.category}, "
            f"enabled_only={query.enabled_only}"
        )

        result = await self._skill_service.list_skills(
            skill_type=query.skill_type,
            category=query.category,
            enabled_only=query.enabled_only,
        )

        logger.info(f"Retrieved {len(result)} skills")

        return result

    async def handle_get_skill_by_id(
        self,
        query: GetSkillByIdQuery,
    ) -> dict[str, Any]:
        """
        Handle get skill by ID query.

        Args:
            query: GetSkillByIdQuery

        Returns:
            Skill data
        """
        logger.info(f"Getting skill {query.skill_id}")

        try:
            result = await self._skill_service.get_skill(
                skill_id=query.skill_id,
            )
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {query.skill_id}")
            raise

    async def handle_get_skill_prompts(
        self,
        query: GetSkillPromptsQuery,
    ) -> list[dict[str, Any]]:
        """
        Handle get skill prompts query.

        Args:
            query: GetSkillPromptsQuery

        Returns:
            List of prompt data
        """
        logger.info(f"Getting prompts for skill {query.skill_id}")

        try:
            result = await self._skill_service.get_skill_prompts(
                skill_id=query.skill_id,
            )
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {query.skill_id}")
            raise

    async def handle_get_skill_model_config(
        self,
        query: GetSkillModelConfigQuery,
    ) -> dict[str, Any] | None:
        """
        Handle get skill model config query.

        Args:
            query: GetSkillModelConfigQuery

        Returns:
            Model config data or None
        """
        logger.info(f"Getting model config for skill {query.skill_id}")

        try:
            result = await self._skill_service.get_skill_model_config(
                skill_id=query.skill_id,
            )
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {query.skill_id}")
            raise
