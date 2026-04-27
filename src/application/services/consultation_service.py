"""
Consultation application service.

Orchestrates consultation session management and conversation history.
"""
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.domain.consultation.repositories.consultation_repository import (
    IConsultationRepository,
)
from src.infrastructure.persistence.models.consultation_models import (
    ConsultationStatus,
    MessageRole,
)
from src.infrastructure.mcp.client_factory import MCPClientFactory

logger = logging.getLogger(__name__)


class ConsultationApplicationService:
    """
    Application service for consultation operations.

    Coordinates consultation session management,
    message handling, and conversation history.
    """

    def __init__(
        self,
        consultation_repository: IConsultationRepository,
        mcp_client_factory: MCPClientFactory,
    ) -> None:
        """
        Initialize ConsultationApplicationService.

        Args:
            consultation_repository: Repository for consultation operations
            mcp_client_factory: Factory for creating MCP clients
        """
        self._consultation_repository = consultation_repository
        self._mcp_client_factory = mcp_client_factory

    async def create_consultation(
        self,
        patient_id: str,
    ) -> dict[str, Any]:
        """
        Create a new consultation session.

        Args:
            patient_id: Patient identifier

        Returns:
            Created consultation data
        """
        # Check for existing active consultation
        existing = await self._consultation_repository.get_active_consultation(
            patient_id
        )
        if existing:
            # Archive existing consultation
            await self._consultation_repository.update_consultation_status(
                consultation_id=existing["consultation_id"],
                status=ConsultationStatus.ARCHIVED,
            )

        # Create new consultation
        consultation_id = str(uuid4())
        consultation = await self._consultation_repository.create_consultation(
            consultation_id=consultation_id,
            patient_id=patient_id,
            status=ConsultationStatus.ACTIVE,
        )

        logger.info(f"Created consultation {consultation_id} for patient {patient_id}")

        return consultation

    async def get_consultation(
        self,
        consultation_id: str,
    ) -> dict[str, Any] | None:
        """
        Get consultation by ID.

        Args:
            consultation_id: Consultation identifier

        Returns:
            Consultation data or None
        """
        return await self._consultation_repository.get_consultation_by_id(
            consultation_id
        )

    async def get_active_consultation(
        self,
        patient_id: str,
    ) -> dict[str, Any] | None:
        """
        Get active consultation for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            Active consultation data or None
        """
        return await self._consultation_repository.get_active_consultation(
            patient_id
        )

    async def get_consultation_messages(
        self,
        consultation_id: str,
        limit: int = 100,
        before_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get messages for a consultation.

        Args:
            consultation_id: Consultation identifier
            limit: Maximum number of messages
            before_id: Get messages before this ID (pagination)

        Returns:
            List of message dictionaries
        """
        return await self._consultation_repository.get_messages(
            consultation_id=consultation_id,
            limit=limit,
            before_id=before_id,
        )

    async def get_consultation_history(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get consultation history for a patient.

        Args:
            patient_id: Patient identifier
            limit: Maximum number of consultations

        Returns:
            List of consultation summaries
        """
        return await self._consultation_repository.get_conversation_history(
            patient_id=patient_id,
            limit=limit,
        )

    async def save_conversation(
        self,
        consultation_id: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Save conversation messages to a consultation.

        Args:
            consultation_id: Consultation identifier
            messages: List of message dictionaries with role and content

        Returns:
            Updated consultation with messages
        """
        consultation = await self._consultation_repository.get_consultation_by_id(
            consultation_id
        )
        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        saved_messages = []
        for msg_data in messages:
            role = MessageRole(msg_data.get("role", "user"))
            content = msg_data.get("content", "")
            intent = msg_data.get("intent")
            metadata = msg_data.get("metadata")

            message = await self._consultation_repository.add_message(
                consultation_id=consultation_id,
                role=role,
                content=content,
                intent=intent,
                structured_metadata=metadata,
            )
            saved_messages.append(message)

        logger.info(f"Saved {len(saved_messages)} messages to consultation {consultation_id}")

        return {
            "consultation_id": consultation_id,
            "messages": saved_messages,
        }

    async def close_consultation(
        self,
        consultation_id: str,
    ) -> bool:
        """
        Close/complete a consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            True if consultation was closed
        """
        result = await self._consultation_repository.update_consultation_status(
            consultation_id=consultation_id,
            status=ConsultationStatus.COMPLETED,
        )

        if result:
            logger.info(f"Closed consultation {consultation_id}")

        return result

    async def archive_consultation(
        self,
        consultation_id: str,
    ) -> bool:
        """
        Archive a consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            True if consultation was archived
        """
        result = await self._consultation_repository.archive_consultation(
            consultation_id
        )

        if result:
            logger.info(f"Archived consultation {consultation_id}")

        return result

    async def delete_consultation(
        self,
        consultation_id: str,
    ) -> bool:
        """
        Delete a consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            True if consultation was deleted
        """
        result = await self._consultation_repository.delete_consultation(
            consultation_id
        )

        if result:
            logger.info(f"Deleted consultation {consultation_id}")

        return result

    async def get_consultation_summary(
        self,
        consultation_id: str,
    ) -> dict[str, Any]:
        """
        Get a summary of a consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            Consultation summary with statistics
        """
        consultation = await self._consultation_repository.get_consultation_by_id(
            consultation_id
        )
        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        messages = await self._consultation_repository.get_messages(
            consultation_id=consultation_id,
            limit=1000,
        )

        # Calculate statistics
        user_messages = [m for m in messages if m["role"] == MessageRole.USER]
        assistant_messages = [m for m in messages if m["role"] == MessageRole.ASSISTANT]

        # Extract unique intents
        intents = set()
        for msg in messages:
            if msg.get("intent"):
                intents.add(msg["intent"])

        summary = {
            "consultation_id": consultation_id,
            "patient_id": consultation["patient_id"],
            "status": consultation["status"],
            "created_at": consultation["created_at"],
            "updated_at": consultation["updated_at"],
            "total_messages": len(messages),
            "user_message_count": len(user_messages),
            "assistant_message_count": len(assistant_messages),
            "unique_intents": list(intents),
            "duration_minutes": self._calculate_duration_minutes(
                consultation["created_at"],
                consultation["updated_at"],
            ),
        }

        return summary

    def _calculate_duration_minutes(
        self,
        created_at: str,
        updated_at: str,
    ) -> int:
        """Calculate consultation duration in minutes."""
        try:
            created = datetime.fromisoformat(created_at)
            updated = datetime.fromisoformat(updated_at)
            duration = (updated - created).total_seconds() / 60
            return int(duration)
        except (ValueError, TypeError):
            return 0

    async def get_messages_by_intent(
        self,
        consultation_id: str,
        intent: str,
    ) -> list[dict[str, Any]]:
        """
        Get messages filtered by intent.

        Args:
            consultation_id: Consultation identifier
            intent: Intent to filter by

        Returns:
            List of messages with matching intent
        """
        return await self._consultation_repository.get_messages_by_intent(
            consultation_id=consultation_id,
            intent=intent,
        )

    async def get_patient_consultation_count(
        self,
        patient_id: str,
    ) -> int:
        """
        Get total consultation count for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            Number of consultations
        """
        return await self._consultation_repository.count_patient_consultations(
            patient_id
        )
