"""Context snapshot value object for caching patient data."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .patient_data import PatientData


@dataclass(frozen=True)
class ContextSnapshot:
    """
    Context snapshot value object for caching patient-related data.

    This acts as a read-only cache of patient data, vital signs,
    and other context needed for consultation and analysis.
    """

    patient_data: PatientData
    vital_signs: dict[str, Any] = field(default_factory=dict)
    medical_history: list[dict[str, Any]] = field(default_factory=list)
    current_medications: list[dict[str, Any]] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    cached_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 3600  # Cache TTL: 1 hour default
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Check if the snapshot has expired."""
        now = current_time or datetime.now()
        age = (now - self.cached_at).total_seconds()
        return age > self.ttl_seconds

    def get_age_seconds(self, current_time: datetime | None = None) -> float:
        """Get the age of the snapshot in seconds."""
        now = current_time or datetime.now()
        return (now - self.cached_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "patient_data": self.patient_data.to_dict(),
            "vital_signs": self.vital_signs,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "allergies": self.allergies,
            "cached_at": self.cached_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "is_expired": self.is_expired(),
            "age_seconds": self.get_age_seconds(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextSnapshot":
        """Create ContextSnapshot from dictionary."""
        cached_at = data.get("cached_at")
        return cls(
            patient_data=PatientData.from_dict(data["patient_data"]),
            vital_signs=data.get("vital_signs", {}),
            medical_history=data.get("medical_history", []),
            current_medications=data.get("current_medications", []),
            allergies=data.get("allergies", []),
            cached_at=datetime.fromisoformat(cached_at) if cached_at else None,
            ttl_seconds=data.get("ttl_seconds", 3600),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        patient_data: PatientData,
        vital_signs: dict[str, Any] | None = None,
        medical_history: list[dict[str, Any]] | None = None,
        current_medications: list[dict[str, Any]] | None = None,
        allergies: list[str] | None = None,
        ttl_seconds: int = 3600,
    ) -> "ContextSnapshot":
        """Create a new context snapshot."""
        return cls(
            patient_data=patient_data,
            vital_signs=vital_signs or {},
            medical_history=medical_history or [],
            current_medications=current_medications or [],
            allergies=allergies or [],
            cached_at=datetime.now(),
            ttl_seconds=ttl_seconds,
        )
