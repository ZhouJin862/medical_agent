"""Blood glucose value object."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..exceptions.invalid_vital_signs import InvalidVitalSignsException
from .vital_signs import VitalSigns


class GlucoseMeasurementType(str, Enum):
    """Type of blood glucose measurement."""

    FASTING = "fasting"  # 空腹血糖
    POSTPRANDIAL_2H = "postprandial_2h"  # 餐后2小时血糖
    RANDOM = "random"  # 随机血糖
    HBA1C = "hba1c"  # 糖化血红蛋白 (%)


@dataclass(frozen=True)
class BloodGlucose(VitalSigns):
    """Blood glucose value object."""

    value: float  # mmol/L (or % for HbA1c)
    measurement_type: GlucoseMeasurementType
    measured_at: datetime
    source: str | None = None

    def __post_init__(self) -> None:
        """Validate blood glucose values."""
        if self.value < 0:
            raise InvalidVitalSignsException(
                f"Blood glucose value cannot be negative, got {self.value}"
            )

        if self.measurement_type == GlucoseMeasurementType.HBA1C:
            if not (3 <= self.value <= 15):
                raise InvalidVitalSignsException(
                    f"HbA1c must be between 3% and 15%, got {self.value}%"
                )
        else:
            if not (0.5 <= self.value <= 40):
                raise InvalidVitalSignsException(
                    f"Blood glucose must be between 0.5 and 40 mmol/L, got {self.value}"
                )

    def is_normal(self) -> bool:
        """Check if blood glucose is within normal range."""
        if self.measurement_type == GlucoseMeasurementType.FASTING:
            return self.value < 6.1
        elif self.measurement_type == GlucoseMeasurementType.POSTPRANDIAL_2H:
            return self.value < 7.8
        elif self.measurement_type == GlucoseMeasurementType.HBA1C:
            return self.value < 5.7
        else:  # RANDOM
            return self.value < 11.1

    def classify(self) -> str:
        """
        Classify blood glucose according to Chinese guidelines.

        Returns:
            Classification as string based on measurement type.
        """
        if self.measurement_type == GlucoseMeasurementType.FASTING:
            return self._classify_fasting()
        elif self.measurement_type == GlucoseMeasurementType.POSTPRANDIAL_2H:
            return self._classify_postprandial()
        elif self.measurement_type == GlucoseMeasurementType.HBA1C:
            return self._classify_hba1c()
        else:  # RANDOM
            return self._classify_random()

    def _classify_fasting(self) -> str:
        """Classify fasting blood glucose."""
        if self.value < 6.1:
            return "正常"
        elif self.value < 7.0:
            return "空腹血糖受损"
        else:
            return "糖尿病"

    def _classify_postprandial(self) -> str:
        """Classify postprandial (2-hour) blood glucose."""
        if self.value < 7.8:
            return "正常"
        elif self.value < 11.1:
            return "糖耐量受损"
        else:
            return "糖尿病"

    def _classify_random(self) -> str:
        """Classify random blood glucose."""
        if self.value < 11.1:
            return "正常"
        else:
            return "糖尿病可能"

    def _classify_hba1c(self) -> str:
        """Classify HbA1c."""
        if self.value < 5.7:
            return "正常"
        elif self.value < 6.5:
            return "糖尿病前期"
        else:
            return "糖尿病"

    def get_classification(self) -> str:
        """Get the classification category for this vital sign."""
        return self.classify()

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "value": self.value,
            "unit": "%" if self.measurement_type == GlucoseMeasurementType.HBA1C else "mmol/L",
            "measurement_type": self.measurement_type.value,
            "classification": self.classify(),
            "measured_at": self.measured_at.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BloodGlucose":
        """Create BloodGlucose from dictionary."""
        return cls(
            value=data["value"],
            measurement_type=GlucoseMeasurementType(data["measurement_type"]),
            measured_at=datetime.fromisoformat(data["measured_at"]),
            source=data.get("source"),
        )
