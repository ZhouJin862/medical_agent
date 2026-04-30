"""
Consultation repository implementation.

Implements IConsultationRepository using SQLAlchemy ORM.
"""
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.consultation.repositories.consultation_repository import (
    IConsultationRepository,
)
from src.infrastructure.persistence.models.consultation_models import (
    ConsultationModel,
    MessageModel,
    ConsultationStatus,
    MessageRole,
)

logger = logging.getLogger(__name__)


class ConsultationRepositoryImpl(IConsultationRepository):
    """
    Implementation of IConsultationRepository.

    Uses SQLAlchemy async session for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create_consultation(
        self,
        consultation_id: str,
        patient_id: str,
        status: ConsultationStatus = ConsultationStatus.ACTIVE,
    ) -> dict[str, Any]:
        """Create a new consultation session."""
        consultation = ConsultationModel(
            id=uuid4().hex,
            consultation_id=consultation_id,
            patient_id=patient_id,
            consult_status=status,
        )
        self._session.add(consultation)
        await self._session.flush()
        # Refresh to load all attributes (created_date, updated_date)
        await self._session.refresh(consultation)
        return consultation.to_dict()

    async def get_consultation_by_id(
        self, consultation_id: str
    ) -> dict[str, Any] | None:
        """Get consultation by ID."""
        stmt = select(ConsultationModel).where(
            ConsultationModel.consultation_id == consultation_id
        )
        result = await self._session.execute(stmt)
        consultation = result.scalar_one_or_none()
        return consultation.to_dict() if consultation else None

    async def get_active_consultation(
        self, patient_id: str
    ) -> dict[str, Any] | None:
        """Get active consultation for a patient."""
        stmt = (
            select(ConsultationModel)
            .where(
                ConsultationModel.patient_id == patient_id,
                ConsultationModel.consult_status == ConsultationStatus.ACTIVE,
            )
            .order_by(desc(ConsultationModel.created_date))
        )
        result = await self._session.execute(stmt)
        consultation = result.scalar_one_or_none()
        return consultation.to_dict() if consultation else None

    async def update_consultation_status(
        self, consultation_id: str, status: ConsultationStatus
    ) -> bool:
        """Update consultation status."""
        stmt = select(ConsultationModel).where(
            ConsultationModel.consultation_id == consultation_id
        )
        result = await self._session.execute(stmt)
        consultation = result.scalar_one_or_none()
        if consultation:
            consultation.consult_status = status
            return True
        return False

    async def add_message(
        self,
        consultation_id: str,
        role: MessageRole,
        content: str,
        intent: str | None = None,
        structured_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a message to a consultation."""
        # Get the consultation's internal ID
        stmt = select(ConsultationModel.id).where(
            ConsultationModel.consultation_id == consultation_id
        )
        result = await self._session.execute(stmt)
        consultation_internal_id = result.scalar_one_or_none()

        if not consultation_internal_id:
            raise ValueError(f"Consultation {consultation_id} not found")

        message = MessageModel(
            id=uuid4().hex,
            consultation_id=consultation_internal_id,
            role=role,
            msg_content=content,
            intent=intent,
            structured_metadata=structured_metadata,
        )
        self._session.add(message)
        await self._session.flush()
        # Refresh to load all attributes (created_date)
        await self._session.refresh(message)
        return message.to_dict()

    async def get_messages(
        self,
        consultation_id: str,
        limit: int = 100,
        before_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get messages for a consultation."""
        # Get consultation's internal ID
        stmt = select(ConsultationModel.id).where(
            ConsultationModel.consultation_id == consultation_id
        )
        result = await self._session.execute(stmt)
        consultation_internal_id = result.scalar_one_or_none()

        if not consultation_internal_id:
            return []

        stmt = select(MessageModel).where(
            MessageModel.consultation_id == consultation_internal_id
        )

        if before_id:
            before_stmt = select(MessageModel.created_date).where(
                MessageModel.id == int(before_id)
            )
            before_result = await self._session.execute(before_stmt)
            before_time = before_result.scalar_one_or_none()
            if before_time:
                stmt = stmt.where(MessageModel.created_date < before_time)

        stmt = stmt.order_by(MessageModel.created_date).limit(limit)
        result = await self._session.execute(stmt)
        messages = result.scalars().all()
        return [msg.to_dict() for msg in messages]

    async def get_conversation_history(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent conversation history for a patient."""
        stmt = (
            select(ConsultationModel)
            .where(ConsultationModel.patient_id == patient_id)
            .order_by(desc(ConsultationModel.created_date))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        consultations = result.scalars().all()

        history = []
        for consultation in consultations:
            # Count messages
            count_stmt = (
                select(func.count(MessageModel.id))
                .where(MessageModel.consultation_id == consultation.id)
            )
            count_result = await self._session.execute(count_stmt)
            message_count = count_result.scalar()

            data = consultation.to_dict()
            data["message_count"] = message_count
            history.append(data)

        return history

    async def delete_consultation(self, consultation_id: str) -> bool:
        """Delete a consultation (cascade deletes messages)."""
        stmt = select(ConsultationModel).where(
            ConsultationModel.consultation_id == consultation_id
        )
        result = await self._session.execute(stmt)
        consultation = result.scalar_one_or_none()
        if consultation:
            await self._session.delete(consultation)
            return True
        return False

    async def archive_consultation(self, consultation_id: str) -> bool:
        """Archive a consultation."""
        return await self.update_consultation_status(
            consultation_id, ConsultationStatus.ARCHIVED
        )

    async def count_patient_consultations(self, patient_id: str) -> int:
        """Count total consultations for a patient."""
        stmt = (
            select(func.count(ConsultationModel.id))
            .where(ConsultationModel.patient_id == patient_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_messages_by_intent(
        self,
        consultation_id: str,
        intent: str,
    ) -> list[dict[str, Any]]:
        """Get messages filtered by intent."""
        stmt = select(ConsultationModel.id).where(
            ConsultationModel.consultation_id == consultation_id
        )
        result = await self._session.execute(stmt)
        consultation_internal_id = result.scalar_one_or_none()

        if not consultation_internal_id:
            return []

        stmt = select(MessageModel).where(
            MessageModel.consultation_id == consultation_internal_id,
            MessageModel.intent == intent,
        )
        stmt = stmt.order_by(MessageModel.created_date)
        result = await self._session.execute(stmt)
        messages = result.scalars().all()
        return [msg.to_dict() for msg in messages]
