"""
Consultation command handlers.

Handles commands for consultation-related operations.
"""
import logging
from typing import Any

from src.application.commands.consultation_commands import (
    AssessHealthCommand,
    CreateHealthPlanCommand,
    SaveConversationCommand,
    SendMessageCommand,
    CloseConsultationCommand,
)
from src.application.services.chat_service import ChatApplicationService
from src.application.services.health_assessment_service import (
    HealthAssessmentApplicationService,
)
from src.application.services.health_plan_service import HealthPlanApplicationService
from src.application.services.consultation_service import ConsultationApplicationService

logger = logging.getLogger(__name__)


class ConsultationCommandHandlers:
    """
    Handlers for consultation-related commands.

    Coordinates with application services to execute commands.
    """

    def __init__(
        self,
        chat_service: ChatApplicationService,
        health_assessment_service: HealthAssessmentApplicationService,
        health_plan_service: HealthPlanApplicationService,
        consultation_service: ConsultationApplicationService,
    ) -> None:
        """
        Initialize consultation command handlers.

        Args:
            chat_service: Chat application service
            health_assessment_service: Health assessment service
            health_plan_service: Health plan service
            consultation_service: Consultation service
        """
        self._chat_service = chat_service
        self._health_assessment_service = health_assessment_service
        self._health_plan_service = health_plan_service
        self._consultation_service = consultation_service

    async def handle_assess_health(
        self,
        command: AssessHealthCommand,
    ) -> dict[str, Any]:
        """
        Handle health assessment command.

        Args:
            command: AssessHealthCommand

        Returns:
            Health assessment result
        """
        logger.info(f"Handling health assessment for patient {command.patient_id}")

        result = await self._health_assessment_service.assess_vital_signs(
            patient_id=command.patient_id,
            vital_signs_data=command.vital_signs_data,
        )

        logger.info(f"Health assessment completed: {result['assessment_id']}")

        return result

    async def handle_create_health_plan(
        self,
        command: CreateHealthPlanCommand,
    ) -> dict[str, Any]:
        """
        Handle health plan creation command.

        Args:
            command: CreateHealthPlanCommand

        Returns:
            Created health plan data
        """
        logger.info(f"Handling health plan creation for patient {command.patient_id}")

        result = await self._health_plan_service.generate_health_plan(
            patient_id=command.patient_id,
            assessment_data=command.assessment_data,
            plan_type=command.plan_type,
        )

        logger.info(f"Health plan created: {result['plan_id']}")

        return result

    async def handle_save_conversation(
        self,
        command: SaveConversationCommand,
    ) -> dict[str, Any]:
        """
        Handle save conversation command.

        Args:
            command: SaveConversationCommand

        Returns:
            Saved conversation data
        """
        logger.info(f"Saving conversation for consultation {command.consultation_id}")

        result = await self._consultation_service.save_conversation(
            consultation_id=command.consultation_id,
            messages=command.messages,
        )

        logger.info(f"Saved {len(command.messages)} messages")

        return result

    async def handle_send_message(
        self,
        command: SendMessageCommand,
    ) -> dict[str, Any]:
        """
        Handle send message command.

        Args:
            command: SendMessageCommand

        Returns:
            Message response data
        """
        logger.info(f"Sending message for patient {command.patient_id}")

        result = await self._chat_service.send_message(
            patient_id=command.patient_id,
            message_content=command.message_content,
            consultation_id=command.consultation_id,
        )

        logger.info(f"Message sent in consultation {result['consultation_id']}")

        return result

    async def handle_close_consultation(
        self,
        command: CloseConsultationCommand,
    ) -> bool:
        """
        Handle close consultation command.

        Args:
            command: CloseConsultationCommand

        Returns:
            True if consultation was closed
        """
        logger.info(f"Closing consultation {command.consultation_id}")

        result = await self._consultation_service.close_consultation(
            consultation_id=command.consultation_id,
        )

        if result:
            logger.info(f"Consultation {command.consultation_id} closed")

        return result
