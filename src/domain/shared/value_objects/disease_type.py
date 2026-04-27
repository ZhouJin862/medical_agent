"""Disease type value object."""

from dataclasses import dataclass
from datetime import datetime

from ..enums.four_highs_type import FourHighsType
from .vital_signs import VitalSigns


@dataclass(frozen=True)
class DiseaseType(VitalSigns):
    """
    Disease type value object.

    Represents a diagnosed chronic condition from the four highs.
    """

    disease: FourHighsType
    diagnosed_at: datetime
    source: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Set measured_at to diagnosed_at for VitalSigns compatibility."""
        # This is handled by dataclass inheritance, measured_at is the same as diagnosed_at
        pass

    @property
    def measured_at(self) -> datetime:
        """Return diagnosed_at for VitalSigns compatibility."""
        return self.diagnosed_at

    def is_normal(self) -> bool:
        """Disease type is not 'normal' - always returns False."""
        return False

    def get_classification(self) -> str:
        """Get the disease classification."""
        return self.disease.display_name

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "disease": self.disease.value,
            "disease_name_cn": self.disease.display_name,
            "disease_name_en": self.disease.english_name,
            "diagnosed_at": self.diagnosed_at.isoformat(),
            "source": self.source,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiseaseType":
        """Create DiseaseType from dictionary."""
        return cls(
            disease=FourHighsType(data["disease"]),
            diagnosed_at=datetime.fromisoformat(data["diagnosed_at"]),
            source=data.get("source"),
            notes=data.get("notes"),
        )
