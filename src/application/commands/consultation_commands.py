"""
Consultation commands.

Defines commands for consultation-related operations.
"""
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AssessHealthCommand:
    """Command to assess patient health from vital signs."""

    patient_id: str
    vital_signs_data: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.patient_id:
            raise ValueError("patient_id is required")
        if not self.vital_signs_data:
            raise ValueError("vital_signs_data is required")


@dataclass(frozen=True)
class CreateHealthPlanCommand:
    """Command to create a new health plan."""

    patient_id: str
    assessment_data: dict[str, Any] | None = None
    plan_type: str = "preventive"

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.patient_id:
            raise ValueError("patient_id is required")
        valid_types = ["preventive", "treatment", "recovery", "chronic_management", "wellness"]
        if self.plan_type not in valid_types:
            raise ValueError(f"plan_type must be one of {valid_types}")


@dataclass(frozen=True)
class SaveConversationCommand:
    """Command to save conversation messages."""

    consultation_id: str
    messages: list[dict[str, Any]]

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.consultation_id:
            raise ValueError("consultation_id is required")
        if not self.messages:
            raise ValueError("messages is required")

        # Validate each message
        for msg in self.messages:
            if "role" not in msg:
                raise ValueError("Each message must have a 'role'")
            if "content" not in msg:
                raise ValueError("Each message must have 'content'")


@dataclass(frozen=True)
class SendMessageCommand:
    """Command to send a message in a consultation."""

    patient_id: str
    message_content: str
    consultation_id: str | None = None

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.patient_id:
            raise ValueError("patient_id is required")
        if not self.message_content:
            raise ValueError("message_content is required")


@dataclass(frozen=True)
class CloseConsultationCommand:
    """Command to close a consultation session."""

    consultation_id: str

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.consultation_id:
            raise ValueError("consultation_id is required")
