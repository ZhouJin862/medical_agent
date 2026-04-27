"""
Skill command handlers.

Handles commands for skill management operations.
"""
import logging
from typing import Any

from src.application.commands.skill_commands import (
    CreateSkillCommand,
    UpdateSkillCommand,
    EnableSkillCommand,
    DisableSkillCommand,
    ReloadSkillCommand,
    DeleteSkillCommand,
    UpdateSkillPromptCommand,
    UpdateSkillModelConfigCommand,
)
from src.application.services.skill_management_service import (
    SkillManagementApplicationService,
    SkillNotFoundException,
    SkillAlreadyExistsException,
)

logger = logging.getLogger(__name__)


class SkillCommandHandlers:
    """
    Handlers for skill-related commands.

    Coordinates with skill management service to execute commands.
    """

    def __init__(
        self,
        skill_service: SkillManagementApplicationService,
    ) -> None:
        """
        Initialize skill command handlers.

        Args:
            skill_service: Skill management service
        """
        self._skill_service = skill_service

    async def handle_create_skill(
        self,
        command: CreateSkillCommand,
    ) -> dict[str, Any]:
        """
        Handle create skill command.

        Args:
            command: CreateSkillCommand

        Returns:
            Created skill data
        """
        logger.info(f"Creating skill: {command.name}")

        try:
            result = await self._skill_service.create_skill(
                name=command.name,
                display_name=command.display_name,
                skill_type=command.skill_type,
                category=command.category,
                description=command.description,
                intent_keywords=command.intent_keywords,
                config=command.config,
                model_config=command.model_config,
                prompts=command.prompts,
            )

            logger.info(f"Skill created with ID: {result['id']}")
            return result

        except SkillAlreadyExistsException as e:
            logger.warning(f"Skill already exists: {command.name}")
            raise

    async def handle_update_skill(
        self,
        command: UpdateSkillCommand,
    ) -> dict[str, Any]:
        """
        Handle update skill command.

        Args:
            command: UpdateSkillCommand

        Returns:
            Updated skill data
        """
        logger.info(f"Updating skill: {command.skill_id}")

        try:
            result = await self._skill_service.update_skill(
                skill_id=command.skill_id,
                display_name=command.display_name,
                description=command.description,
                intent_keywords=command.intent_keywords,
                config=command.config,
            )

            logger.info(f"Skill updated: {command.skill_id}")
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise

    async def handle_enable_skill(
        self,
        command: EnableSkillCommand,
    ) -> dict[str, Any]:
        """
        Handle enable skill command.

        Args:
            command: EnableSkillCommand

        Returns:
            Updated skill data
        """
        logger.info(f"Enabling skill: {command.skill_id}")

        try:
            result = await self._skill_service.enable_skill(
                skill_id=command.skill_id,
            )

            logger.info(f"Skill enabled: {command.skill_id}")
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise

    async def handle_disable_skill(
        self,
        command: DisableSkillCommand,
    ) -> dict[str, Any]:
        """
        Handle disable skill command.

        Args:
            command: DisableSkillCommand

        Returns:
            Updated skill data
        """
        logger.info(f"Disabling skill: {command.skill_id}")

        try:
            result = await self._skill_service.disable_skill(
                skill_id=command.skill_id,
            )

            logger.info(f"Skill disabled: {command.skill_id}")
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise

    async def handle_reload_skill(
        self,
        command: ReloadSkillCommand,
    ) -> dict[str, Any]:
        """
        Handle reload skill command.

        Args:
            command: ReloadSkillCommand

        Returns:
            Reloaded skill data
        """
        logger.info(f"Reloading skill: {command.skill_id}")

        try:
            result = await self._skill_service.reload_skill(
                skill_id=command.skill_id,
            )

            logger.info(f"Skill reloaded: {command.skill_id}")
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise

    async def handle_delete_skill(
        self,
        command: DeleteSkillCommand,
    ) -> bool:
        """
        Handle delete skill command.

        Args:
            command: DeleteSkillCommand

        Returns:
            True if skill was deleted
        """
        logger.info(f"Deleting skill: {command.skill_id}")

        try:
            result = await self._skill_service.delete_skill(
                skill_id=command.skill_id,
            )

            if result:
                logger.info(f"Skill deleted: {command.skill_id}")

            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise

    async def handle_update_skill_prompt(
        self,
        command: UpdateSkillPromptCommand,
    ) -> dict[str, Any]:
        """
        Handle update skill prompt command.

        Args:
            command: UpdateSkillPromptCommand

        Returns:
            Updated prompt data
        """
        logger.info(
            f"Updating prompt {command.prompt_type} for skill {command.skill_id}"
        )

        try:
            result = await self._skill_service.update_skill_prompt(
                skill_id=command.skill_id,
                prompt_type=command.prompt_type,
                content=command.content,
            )

            logger.info(f"Prompt updated: {result['id']}")
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise

    async def handle_update_skill_model_config(
        self,
        command: UpdateSkillModelConfigCommand,
    ) -> dict[str, Any]:
        """
        Handle update skill model config command.

        Args:
            command: UpdateSkillModelConfigCommand

        Returns:
            Updated model config data
        """
        logger.info(f"Updating model config for skill {command.skill_id}")

        try:
            result = await self._skill_service.update_skill_model_config(
                skill_id=command.skill_id,
                model_config=command.model_config,
            )

            logger.info(f"Model config updated: {result['id']}")
            return result

        except SkillNotFoundException as e:
            logger.warning(f"Skill not found: {command.skill_id}")
            raise
