"""
ConsultationStatus Value Object - Status of a consultation.

Defines the possible states of a consultation session.
"""

from dataclasses import dataclass
from enum import Enum


class ConsultationStatusEnum(Enum):
    """Status values for a consultation."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass(frozen=True)
class ConsultationStatus:
    """
    Value object representing consultation status.

    Attributes:
        status: The current status
        reason: Optional reason for status change
        updated_at: When status was last updated
    """

    status: ConsultationStatusEnum
    reason: str | None = None

    def is_active(self) -> bool:
        """Check if consultation is still active."""
        return self.status in (
            ConsultationStatusEnum.CREATED,
            ConsultationStatusEnum.IN_PROGRESS,
            ConsultationStatusEnum.WAITING_FOR_INPUT,
            ConsultationStatusEnum.PROCESSING,
        )

    def is_terminal(self) -> bool:
        """Check if consultation is in a terminal state."""
        return self.status in (
            ConsultationStatusEnum.COMPLETED,
            ConsultationStatusEnum.CANCELLED,
            ConsultationStatusEnum.ERROR,
        )

    def can_add_message(self) -> bool:
        """Check if messages can be added to this consultation."""
        return self.is_active()

    def transition_to(self, new_status: ConsultationStatusEnum, reason: str | None = None) -> "ConsultationStatus":
        """Create a new status with the transition."""
        return ConsultationStatus(status=new_status, reason=reason)
