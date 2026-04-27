"""HealthPlan aggregate root."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.domain.common.aggregates import AggregateRoot
from src.domain.health_plan.entities.prescriptions.diet_prescription import (
    DietPrescription,
)
from src.domain.health_plan.entities.prescriptions.exercise_prescription import (
    ExercisePrescription,
)
from src.domain.health_plan.entities.prescriptions.medication_prescription import (
    MedicationPrescription,
)
from src.domain.health_plan.entities.prescriptions.prescription import (
    Prescription,
    PrescriptionType,
)
from src.domain.health_plan.entities.prescriptions.psychological_prescription import (
    PsychologicalPrescription,
)
from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
    SleepPrescription,
)
from src.domain.health_plan.events.health_plan_generated import HealthPlanGenerated
from src.domain.health_plan.value_objects.health_plan_id import HealthPlanId
from src.domain.health_plan.value_objects.target_goals import TargetGoals


class PlanType(Enum):
    """Types of health plans."""
    PREVENTIVE = "preventive"
    TREATMENT = "treatment"
    RECOVERY = "recovery"
    CHRONIC_MANAGEMENT = "chronic_management"
    WELLNESS = "wellness"


@dataclass
class HealthPlan(AggregateRoot):
    """Aggregate root for health plan management."""

    plan_id: HealthPlanId
    patient_id: str
    plan_type: PlanType
    prescriptions: list[Prescription] = field(default_factory=list)
    target_goals: TargetGoals = field(default_factory=TargetGoals)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Initialize the AggregateRoot base class."""
        # Call parent class __init__ explicitly since dataclass doesn't do it
        AggregateRoot.__init__(self)

    def add_prescription(self, prescription: Prescription) -> None:
        """Add a prescription to the health plan."""
        if not prescription.validate():
            raise ValueError(f"Invalid prescription: {prescription.prescription_id}")

        # Check for duplicate prescription IDs
        existing_ids = {p.prescription_id for p in self.prescriptions}
        if prescription.prescription_id in existing_ids:
            raise ValueError(
                f"Prescription with ID {prescription.prescription_id} already exists"
            )

        self.prescriptions.append(prescription)
        self.updated_at = datetime.now()

    def get_prescriptions_by_type(
        self, prescription_type: PrescriptionType
    ) -> list[Prescription]:
        """Get all prescriptions of a specific type."""
        return [
            p for p in self.prescriptions if p.prescription_type == prescription_type
        ]

    def remove_prescription(self, prescription_id: str) -> bool:
        """Remove a prescription by ID."""
        original_length = len(self.prescriptions)
        self.prescriptions = [
            p for p in self.prescriptions if p.prescription_id != prescription_id
        ]
        removed = len(self.prescriptions) < original_length
        if removed:
            self.updated_at = datetime.now()
        return removed

    def generate_summary(self) -> dict[str, Any]:
        """Generate a summary of the health plan."""
        summary = {
            "plan_id": str(self.plan_id),
            "patient_id": self.patient_id,
            "plan_type": self.plan_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_prescriptions": len(self.prescriptions),
            "prescriptions_by_type": {},
            "target_goals": {
                "total": len(self.target_goals),
                "active": len(self.target_goals.active_goals),
                "achieved": len(self.target_goals.achieved_goals),
            },
        }

        # Count prescriptions by type
        for p in self.prescriptions:
            ptype = p.prescription_type.value
            summary["prescriptions_by_type"][ptype] = (
                summary["prescriptions_by_type"].get(ptype, 0) + 1
            )

        # Add brief details for each prescription
        summary["prescription_details"] = [
            {
                "id": p.prescription_id,
                "type": p.prescription_type.value,
                "created_at": p.created_at.isoformat(),
                "details": p.get_details(),
            }
            for p in self.prescriptions
        ]

        return summary

    def mark_as_generated(self) -> None:
        """Mark the health plan as generated and raise event."""
        self.updated_at = datetime.now()
        self._add_domain_event(
            HealthPlanGenerated(
                event_id=f"health_plan_generated_{self.plan_id.value}",
                occurred_at=datetime.now(),
                plan_id=self.plan_id.value,
                patient_id=self.patient_id,
                plan_type=self.plan_type.value,
            )
        )

    def update_target_goals(self, new_goals: TargetGoals) -> None:
        """Update the target goals for this health plan."""
        self.target_goals = new_goals
        self.updated_at = datetime.now()

    def get_id(self) -> str:
        """Get the unique identifier for this aggregate."""
        return self.plan_id.value
