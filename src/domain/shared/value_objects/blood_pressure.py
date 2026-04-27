"""Blood pressure value object."""

from dataclasses import dataclass
from datetime import datetime

from ..exceptions.invalid_vital_signs import InvalidVitalSignsException
from .vital_signs import VitalSigns


@dataclass(frozen=True)
class BloodPressure(VitalSigns):
    """Blood pressure value object with systolic and diastolic values."""

    systolic: int  # 收缩压 (mmHg)
    diastolic: int  # 舒张压 (mmHg)
    measured_at: datetime
    source: str | None = None

    def __post_init__(self) -> None:
        """Validate blood pressure values."""
        if not (50 <= self.systolic <= 300):
            raise InvalidVitalSignsException(
                f"Systolic pressure must be between 50 and 300 mmHg, got {self.systolic}"
            )
        if not (30 <= self.diastolic <= 200):
            raise InvalidVitalSignsException(
                f"Diastolic pressure must be between 30 and 200 mmHg, got {self.diastolic}"
            )
        if self.systolic <= self.diastolic:
            raise InvalidVitalSignsException(
                f"Systolic ({self.systolic}) must be greater than diastolic ({self.diastolic})"
            )

    def is_normal(self) -> bool:
        """Check if blood pressure is within normal range."""
        return self.systolic < 120 and self.diastolic < 80

    def classify(self) -> str:
        """
        Classify blood pressure according to Chinese guidelines.

        Returns:
            Classification as string:
            - 正常: < 120/80 mmHg
            - 正常高值: 120-139/80-89 mmHg
            - 1级高血压: 140-159/90-99 mmHg
            - 2级高血压: 160-179/100-109 mmHg
            - 3级高血压: ≥ 180/110 mmHg
        """
        if self.systolic >= 180 or self.diastolic >= 110:
            return "3级"
        elif self.systolic >= 160 or self.diastolic >= 100:
            return "2级"
        elif self.systolic >= 140 or self.diastolic >= 90:
            return "1级"
        elif self.systolic >= 120 or self.diastolic >= 80:
            return "正常高值"
        else:
            return "正常"

    def get_classification(self) -> str:
        """Get the classification category for this vital sign."""
        return self.classify()

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "systolic": self.systolic,
            "diastolic": self.diastolic,
            "classification": self.classify(),
            "measured_at": self.measured_at.isoformat(),
            "source": self.source,
        }

    @property
    def pulse_pressure(self) -> int:
        """Calculate pulse pressure (systolic - diastolic)."""
        return self.systolic - self.diastolic

    @property
    def mean_arterial_pressure(self) -> float:
        """Calculate mean arterial pressure."""
        return self.diastolic + (self.pulse_pressure / 3)

    @classmethod
    def from_dict(cls, data: dict) -> "BloodPressure":
        """Create BloodPressure from dictionary."""
        return cls(
            systolic=data["systolic"],
            diastolic=data["diastolic"],
            measured_at=datetime.fromisoformat(data["measured_at"]),
            source=data.get("source"),
        )
