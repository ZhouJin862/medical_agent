"""Exercise Prescription entity."""
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.domain.health_plan.entities.prescriptions.prescription import (
    Prescription,
    PrescriptionType,
)


class ExerciseType(Enum):
    """Types of exercises."""
    CARDIO = "cardio"
    STRENGTH = "strength"
    FLEXIBILITY = "flexibility"
    BALANCE = "balance"
    AEROBIC = "aerobic"
    ANAEROBIC = "anaerobic"


class IntensityLevel(Enum):
    """Exercise intensity levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ExercisePrescription(Prescription):
    """Prescription for exercise recommendations."""

    exercise_type: ExerciseType | None = None
    frequency: str | None = None  # e.g., "3 times per week"
    duration: str | None = None  # e.g., "30 minutes"
    intensity: IntensityLevel | None = None
    precautions: list[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.prescription_type = PrescriptionType.EXERCISE
        if self.precautions is None:
            self.precautions = []

    def get_details(self) -> dict[str, Any]:
        """Get exercise prescription details."""
        return {
            "exercise_type": self.exercise_type.value if self.exercise_type else None,
            "frequency": self.frequency,
            "duration": self.duration,
            "intensity": self.intensity.value if self.intensity else None,
            "precautions": self.precautions,
        }

    def validate(self) -> bool:
        """Validate exercise prescription data."""
        return bool(self.exercise_type)

    def add_precaution(self, precaution: str) -> None:
        """Add a precaution for the exercise."""
        if precaution and precaution not in self.precautions:
            self.precautions.append(precaution)

    def get_id(self) -> str:
        """Get the unique identifier for this entity."""
        return self.prescription_id
