"""
Consultation queries.

Defines queries for consultation-related read operations.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GetConsultationHistoryQuery:
    """Query to get consultation history for a patient."""

    patient_id: str
    limit: int = 10

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.patient_id:
            raise ValueError("patient_id is required")
        if self.limit <= 0 or self.limit > 100:
            raise ValueError("limit must be between 1 and 100")


@dataclass(frozen=True)
class GetPatientHealthProfileQuery:
    """Query to get patient health profile."""

    patient_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.patient_id:
            raise ValueError("patient_id is required")


@dataclass(frozen=True)
class GetHealthPlanQuery:
    """Query to get health plan by ID."""

    plan_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.plan_id:
            raise ValueError("plan_id is required")


@dataclass(frozen=True)
class GetPatientHealthPlansQuery:
    """Query to get all health plans for a patient."""

    patient_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.patient_id:
            raise ValueError("patient_id is required")


@dataclass(frozen=True)
class GetConsultationMessagesQuery:
    """Query to get messages for a consultation."""

    consultation_id: str
    limit: int = 100
    before_id: str | None = None

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.consultation_id:
            raise ValueError("consultation_id is required")
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")


@dataclass(frozen=True)
class GetConsultationSummaryQuery:
    """Query to get consultation summary."""

    consultation_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.consultation_id:
            raise ValueError("consultation_id is required")
