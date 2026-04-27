"""Medication Prescription entity."""
from dataclasses import dataclass
from typing import Any

from src.domain.health_plan.entities.prescriptions.prescription import (
    Prescription,
    PrescriptionType,
)


@dataclass
class MedicationPrescription(Prescription):
    """Prescription for medication."""

    drug_name: str
    dosage: str
    frequency: str
    duration: str | None = None

    def __post_init__(self):
        super().__post_init__()
        self.prescription_type = PrescriptionType.MEDICATION
        if not self.drug_name:
            raise ValueError("drug_name cannot be empty")
        if not self.dosage:
            raise ValueError("dosage cannot be empty")
        if not self.frequency:
            raise ValueError("frequency cannot be empty")

    def get_details(self) -> dict[str, Any]:
        """Get medication prescription details."""
        return {
            "drug_name": self.drug_name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "duration": self.duration,
        }

    def validate(self) -> bool:
        """Validate medication prescription data."""
        return bool(
            self.drug_name and
            self.dosage and
            self.frequency
        )

    def get_id(self) -> str:
        """Get the unique identifier for this entity."""
        return self.prescription_id
