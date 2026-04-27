"""Base Prescription entity."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.domain.common.entities import Entity


class PrescriptionType(Enum):
    """Types of prescriptions available."""
    DIET = "diet"
    EXERCISE = "exercise"
    SLEEP = "sleep"
    MEDICATION = "medication"
    PSYCHOLOGICAL = "psychological"


@dataclass
class Prescription(Entity, ABC):
    """Base class for all prescription types."""

    prescription_id: str
    prescription_type: PrescriptionType
    created_at: datetime

    def __post_init__(self):
        if not self.prescription_id:
            raise ValueError("prescription_id cannot be empty")
        if not isinstance(self.prescription_type, PrescriptionType):
            raise ValueError("prescription_type must be a PrescriptionType enum")

    @abstractmethod
    def get_details(self) -> dict:
        """Get prescription-specific details."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate prescription data."""
        pass
