"""Uric acid value object."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..exceptions.invalid_vital_signs import InvalidVitalSignsException
from .vital_signs import VitalSigns


class GenderEnum(str, Enum):
    """Gender for uric acid reference ranges."""

    MALE = "male"
    FEMALE = "female"


@dataclass(frozen=True)
class UricAcid(VitalSigns):
    """
    Uric acid value object.

    Normal ranges differ by gender:
    - Male: < 420 μmol/L
    - Female: < 360 μmol/L
    """

    value: float  # μmol/L
    measured_at: datetime
    gender: GenderEnum | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        """Validate uric acid values."""
        if not (50 <= self.value <= 1000):
            raise InvalidVitalSignsException(
                f"Uric acid must be between 50 and 1000 μmol/L, got {self.value}"
            )

    @property
    def reference_upper(self) -> float:
        """Get the upper reference limit based on gender."""
        return 420 if self.gender == GenderEnum.MALE else 360

    def is_normal(self) -> bool:
        """Check if uric acid is within normal range."""
        upper_limit = self.reference_upper if self.gender else 420
        return self.value < upper_limit

    def classify(self) -> str:
        """
        Classify uric acid level.

        Returns:
            Classification based on value and gender.
        """
        upper_limit = self.reference_upper if self.gender else 420

        if self.value < upper_limit:
            return "正常"
        elif self.value < upper_limit + 60:
            return "轻度升高"
        elif self.value < upper_limit + 120:
            return "中度升高"
        else:
            return "重度升高"

    def get_risk_level(self) -> str:
        """Get gout risk level based on uric acid."""
        if not self.is_normal():
            if self.value >= 540:
                return "高风险"
            elif self.value >= 480:
                return "中风险"
            else:
                return "低风险"
        return "正常"

    def get_classification(self) -> str:
        """Get the classification category for this vital sign."""
        return self.classify()

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "value": self.value,
            "unit": "μmol/L",
            "gender": self.gender.value if self.gender else None,
            "reference_upper": self.reference_upper,
            "classification": self.classify(),
            "risk_level": self.get_risk_level(),
            "measured_at": self.measured_at.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UricAcid":
        """Create UricAcid from dictionary."""
        gender = data.get("gender")
        return cls(
            value=data["value"],
            measured_at=datetime.fromisoformat(data["measured_at"]),
            gender=GenderEnum(gender) if gender else None,
            source=data.get("source"),
        )
