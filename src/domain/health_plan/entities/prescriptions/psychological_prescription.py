"""Psychological Prescription entity."""
from dataclasses import dataclass
from typing import Any

from src.domain.health_plan.entities.prescriptions.prescription import (
    Prescription,
    PrescriptionType,
)


@dataclass
class PsychologicalPrescription(Prescription):
    """Prescription for psychological interventions."""

    interventions: list[str] = None
    goals: list[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.prescription_type = PrescriptionType.PSYCHOLOGICAL
        if self.interventions is None:
            self.interventions = []
        if self.goals is None:
            self.goals = []

    def get_details(self) -> dict[str, Any]:
        """Get psychological prescription details."""
        return {
            "interventions": self.interventions,
            "goals": self.goals,
        }

    def validate(self) -> bool:
        """Validate psychological prescription data."""
        return bool(self.interventions or self.goals)

    def add_intervention(self, intervention: str) -> None:
        """Add a psychological intervention."""
        if intervention and intervention not in self.interventions:
            self.interventions.append(intervention)

    def add_goal(self, goal: str) -> None:
        """Add a therapy goal."""
        if goal and goal not in self.goals:
            self.goals.append(goal)

    def get_id(self) -> str:
        """Get the unique identifier for this entity."""
        return self.prescription_id
