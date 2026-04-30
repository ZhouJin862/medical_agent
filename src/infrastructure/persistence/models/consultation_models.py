"""
Consultation ORM models.

Includes ConsultationModel and MessageModel for storing
consultation sessions and chat messages.
"""
import json
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, Enum as SQLEnum, String, Text, Index
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models.base import BaseModel


class ConsultationStatus(str, Enum):
    """Status of a consultation session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageRole(str, Enum):
    """Role of a message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConsultationModel(BaseModel):
    """
    Consultation aggregate root ORM model.

    Represents a consultation session between a patient and the AI assistant.
    """

    __tablename__ = "consultations"

    consultation_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    consult_status: Mapped[ConsultationStatus] = mapped_column(
        SQLEnum(ConsultationStatus),
        default=ConsultationStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="consultation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MessageModel.created_date",
        primaryjoin="ConsultationModel.id == MessageModel.consultation_id",
        foreign_keys="MessageModel.consultation_id",
    )

    __table_args__ = (
        Index("idx_consultation_patient_status", "patient_id", "consult_status"),
    )


class MessageModel(BaseModel):
    """
    Message entity ORM model.

    Represents a single message in a consultation conversation.
    """

    __tablename__ = "messages"

    consultation_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole),
        nullable=False,
    )
    msg_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    intent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    structured_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    consultation: Mapped["ConsultationModel"] = relationship(
        "ConsultationModel",
        back_populates="messages",
        primaryjoin="MessageModel.consultation_id == ConsultationModel.id",
        foreign_keys=[consultation_id],
    )

    __table_args__ = (
        Index("idx_message_consultation_created", "consultation_id", "created_date"),
    )

    def set_structured_metadata(self, data: dict[str, Any] | None) -> None:
        """Set structured metadata."""
        self.structured_metadata = data

    def get_structured_metadata(self) -> dict[str, Any] | None:
        """Get structured metadata."""
        if isinstance(self.structured_metadata, str):
            try:
                return json.loads(self.structured_metadata)
            except (json.JSONDecodeError, TypeError):
                return None
        return self.structured_metadata
