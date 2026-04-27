"""
Consultation repository interface.

Defines the contract for consultation persistence operations.
"""
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from src.infrastructure.persistence.models.consultation_models import (
    ConsultationStatus,
    MessageRole,
)


class IConsultationRepository(ABC):
    """
    Interface for Consultation repository.

    Defines methods for managing consultation sessions and messages.
    """

    @abstractmethod
    async def create_consultation(
        self,
        consultation_id: str,
        patient_id: str,
        status: ConsultationStatus = ConsultationStatus.ACTIVE,
    ) -> dict[str, Any]:
        """
        Create a new consultation session.

        Args:
            consultation_id: Unique consultation identifier
            patient_id: Patient identifier
            status: Initial status of the consultation

        Returns:
            Created consultation data as dictionary
        """

    @abstractmethod
    async def get_consultation_by_id(
        self, consultation_id: str
    ) -> dict[str, Any] | None:
        """
        Get consultation by ID.

        Args:
            consultation_id: Consultation identifier

        Returns:
            Consultation data or None if not found
        """

    @abstractmethod
    async def get_active_consultation(
        self, patient_id: str
    ) -> dict[str, Any] | None:
        """
        Get active consultation for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            Active consultation data or None if not found
        """

    @abstractmethod
    async def update_consultation_status(
        self, consultation_id: str, status: ConsultationStatus
    ) -> bool:
        """
        Update consultation status.

        Args:
            consultation_id: Consultation identifier
            status: New status

        Returns:
            True if updated successfully
        """

    @abstractmethod
    async def add_message(
        self,
        consultation_id: str,
        role: MessageRole,
        content: str,
        intent: str | None = None,
        structured_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Add a message to a consultation.

        Args:
            consultation_id: Consultation identifier
            role: Message role (user/assistant/system)
            content: Message content
            intent: Classified intent
            structured_metadata: Structured data from AI response

        Returns:
            Created message data
        """

    @abstractmethod
    async def get_messages(
        self,
        consultation_id: str,
        limit: int = 100,
        before_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get messages for a consultation.

        Args:
            consultation_id: Consultation identifier
            limit: Maximum number of messages to return
            before_id: Get messages before this message ID (for pagination)

        Returns:
            List of message dictionaries
        """

    @abstractmethod
    async def get_conversation_history(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get recent conversation history for a patient.

        Args:
            patient_id: Patient identifier
            limit: Maximum number of consultations to return

        Returns:
            List of consultation summaries with message count
        """

    @abstractmethod
    async def delete_consultation(self, consultation_id: str) -> bool:
        """
        Delete a consultation (cascade deletes messages).

        Args:
            consultation_id: Consultation identifier

        Returns:
            True if deleted successfully
        """

    @abstractmethod
    async def archive_consultation(self, consultation_id: str) -> bool:
        """
        Archive a consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            True if archived successfully
        """

    @abstractmethod
    async def count_patient_consultations(self, patient_id: str) -> int:
        """
        Count total consultations for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            Number of consultations
        """

    @abstractmethod
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
