"""Diet Prescription entity."""
import json
from dataclasses import dataclass, field
from typing import Any

from src.domain.health_plan.entities.prescriptions.prescription import (
    Prescription,
    PrescriptionType,
)


@dataclass
class DietPrescription(Prescription):
    """Prescription for dietary recommendations."""

    daily_calories: int | None = None
    meals: dict = field(default_factory=dict)
    restrictions: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.prescription_type = PrescriptionType.DIET
        if self.daily_calories is not None and self.daily_calories <= 0:
            raise ValueError("daily_calories must be positive")

    def get_details(self) -> dict[str, Any]:
        """Get diet prescription details."""
        return {
            "daily_calories": self.daily_calories,
            "meals": self.meals,
            "restrictions": self.restrictions,
            "recommendations": self.recommendations,
        }

    def validate(self) -> bool:
        """Validate diet prescription data."""
        if self.daily_calories is not None and self.daily_calories < 500:
            return False
        return True

    def add_restriction(self, restriction: str) -> None:
        """Add a dietary restriction."""
        if restriction and restriction not in self.restrictions:
            self.restrictions.append(restriction)

    def add_meal(self, meal_type: str, meal_data: dict) -> None:
        """Add a meal plan."""
        self.meals[meal_type] = meal_data

    def get_id(self) -> str:
        """Get the unique identifier for this entity."""
        return self.prescription_id
