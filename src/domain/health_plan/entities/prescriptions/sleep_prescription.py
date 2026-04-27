"""Sleep Prescription entity."""
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.domain.health_plan.entities.prescriptions.prescription import (
    Prescription,
    PrescriptionType,
)


class SleepQualityRating(Enum):
    """Sleep quality ratings."""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass
class SleepPrescription(Prescription):
    """Prescription for sleep recommendations."""

    sleep_duration: str | None = None  # e.g., "7-8 hours"
    sleep_quality: SleepQualityRating | None = None
    recommendations: list[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.prescription_type = PrescriptionType.SLEEP
        if self.recommendations is None:
            self.recommendations = []

    def get_details(self) -> dict[str, Any]:
        """Get sleep prescription details."""
        return {
            "sleep_duration": self.sleep_duration,
            "sleep_quality": self.sleep_quality.value if self.sleep_quality else None,
            "recommendations": self.recommendations,
        }

    def validate(self) -> bool:
        """Validate sleep prescription data."""
        return bool(self.sleep_duration or self.recommendations)

    def add_recommendation(self, recommendation: str) -> None:
        """Add a sleep recommendation."""
        if recommendation and recommendation not in self.recommendations:
            self.recommendations.append(recommendation)

    def get_id(self) -> str:
        """Get the unique identifier for this entity."""
        return self.prescription_id
