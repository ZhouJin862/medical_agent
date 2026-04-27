"""BMI (Body Mass Index) value object."""

from dataclasses import dataclass
from datetime import datetime

from ..exceptions.invalid_vital_signs import InvalidVitalSignsException
from .vital_signs import VitalSigns


@dataclass(frozen=True)
class BMI(VitalSigns):
    """
    Body Mass Index value object.

    BMI = weight (kg) / height² (m²)

    Chinese BMI classification:
    - Underweight: < 18.5
    - Normal: 18.5 - 23.9
    - Overweight: 24.0 - 27.9
    - Obese: ≥ 28.0
    """

    value: float  # BMI value
    measured_at: datetime
    source: str | None = None

    def __post_init__(self) -> None:
        """Validate BMI values."""
        if not (10 <= self.value <= 60):
            raise InvalidVitalSignsException(
                f"BMI must be between 10 and 60, got {self.value}"
            )

    @classmethod
    def calculate(
        cls,
        weight_kg: float,
        height_m: float,
        measured_at: datetime | None = None,
        source: str | None = None,
    ) -> "BMI":
        """
        Calculate BMI from weight and height.

        Args:
            weight_kg: Weight in kilograms
            height_m: Height in meters
            measured_at: When the measurement was taken
            source: Source of the measurement

        Returns:
            BMI value object
        """
        if not (30 <= weight_kg <= 300):
            raise InvalidVitalSignsException(
                f"Weight must be between 30 and 300 kg, got {weight_kg}"
            )
        if not (1.0 <= height_m <= 2.5):
            raise InvalidVitalSignsException(
                f"Height must be between 1.0 and 2.5 meters, got {height_m}"
            )

        bmi_value = round(weight_kg / (height_m**2), 1)
        return cls(
            value=bmi_value,
            measured_at=measured_at or datetime.now(),
            source=source,
        )

    def is_normal(self) -> bool:
        """Check if BMI is within normal range."""
        return 18.5 <= self.value < 24.0

    def classify(self) -> str:
        """
        Classify BMI according to Chinese guidelines.

        Returns:
            Classification: 正常/超重/肥胖/偏瘦
        """
        if self.value < 18.5:
            return "偏瘦"
        elif self.value < 24.0:
            return "正常"
        elif self.value < 28.0:
            return "超重"
        else:
            return "肥胖"

    def get_classification(self) -> str:
        """Get the classification category for this vital sign."""
        return self.classify()

    def get_health_risk(self) -> str:
        """Get health risk level associated with BMI."""
        if self.value < 18.5:
            return "营养不良风险"
        elif self.value < 24.0:
            return "低风险"
        elif self.value < 28.0:
            return "增加风险"
        else:
            return "高风险"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "value": self.value,
            "unit": "kg/m²",
            "classification": self.classify(),
            "health_risk": self.get_health_risk(),
            "measured_at": self.measured_at.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BMI":
        """Create BMI from dictionary."""
        return cls(
            value=data["value"],
            measured_at=datetime.fromisoformat(data["measured_at"]),
            source=data.get("source"),
        )
