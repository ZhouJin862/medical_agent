"""HealthPlanGenerated domain event."""
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.common.aggregates import DomainEvent


@dataclass
class HealthPlanGenerated(DomainEvent):
    """Event raised when a health plan is generated."""

    plan_id: str = ""
    patient_id: str = ""
    plan_type: str = ""

    def __str__(self) -> str:
        return (
            f"HealthPlanGenerated(id={self.event_id}, "
            f"plan_id={self.plan_id}, patient_id={self.patient_id}, "
            f"plan_type={self.plan_type})"
        )
