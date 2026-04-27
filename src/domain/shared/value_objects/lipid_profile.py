"""Lipid profile value object."""

from dataclasses import dataclass
from datetime import datetime

from ..exceptions.invalid_vital_signs import InvalidVitalSignsException
from .vital_signs import VitalSigns


@dataclass(frozen=True)
class LipidProfile(VitalSigns):
    """
    Lipid profile value object.

    Contains total cholesterol (TC), triglycerides (TG),
    LDL cholesterol (LDL-C), and HDL cholesterol (HDL-C).
    """

    tc: float | None = None  # 总胆固醇 (mmol/L)
    tg: float | None = None  # 甘油三酯 (mmol/L)
    ldl_c: float | None = None  # 低密度脂蛋白胆固醇 (mmol/L)
    hdl_c: float | None = None  # 高密度脂蛋白胆固醇 (mmol/L)
    measured_at: datetime | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        """Validate lipid profile values."""
        if all(v is None for v in [self.tc, self.tg, self.ldl_c, self.hdl_c]):
            raise InvalidVitalSignsException(
                "At least one lipid value must be provided"
            )

        # Validate individual values if present
        if self.tc is not None and not (1 <= self.tc <= 20):
            raise InvalidVitalSignsException(
                f"Total cholesterol must be between 1 and 20 mmol/L, got {self.tc}"
            )
        if self.tg is not None and not (0.2 <= self.tg <= 20):
            raise InvalidVitalSignsException(
                f"Triglycerides must be between 0.2 and 20 mmol/L, got {self.tg}"
            )
        if self.ldl_c is not None and not (0.5 <= self.ldl_c <= 15):
            raise InvalidVitalSignsException(
                f"LDL-C must be between 0.5 and 15 mmol/L, got {self.ldl_c}"
            )
        if self.hdl_c is not None and not (0.2 <= self.hdl_c <= 5):
            raise InvalidVitalSignsException(
                f"HDL-C must be between 0.2 and 5 mmol/L, got {self.hdl_c}"
            )

        # Set measured_at if not provided (required by VitalSigns)
        if self.measured_at is None:
            object.__setattr__(self, "measured_at", datetime.now())

    def is_normal(self) -> bool:
        """Check if all lipid values are within normal range."""
        return self.get_abnormal_count() == 0

    def get_abnormal_count(self) -> int:
        """Count how many lipid values are abnormal."""
        count = 0
        if self.tc is not None and self.tc >= 5.2:
            count += 1
        if self.tg is not None and self.tg >= 1.7:
            count += 1
        if self.ldl_c is not None and self.ldl_c >= 3.4:
            count += 1
        if self.hdl_c is not None and self.hdl_c < 1.0:  # Low HDL is abnormal
            count += 1
        return count

    def classify(self) -> str:
        """
        Classify lipid profile according to Chinese guidelines.

        Returns:
            Classification based on the number of abnormal values.
        """
        abnormal_count = self.get_abnormal_count()
        if abnormal_count == 0:
            return "正常"
        elif abnormal_count == 1:
            return "边缘异常"
        else:
            return "血脂异常"

    def get_classification(self) -> str:
        """Get the classification category for this vital sign."""
        return self.classify()

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "tc": self.tc,
            "tg": self.tg,
            "ldl_c": self.ldl_c,
            "hdl_c": self.hdl_c,
            "unit": "mmol/L",
            "classification": self.classify(),
            "measured_at": self.measured_at.isoformat() if self.measured_at else None,
            "source": self.source,
        }

    @property
    def tc_class(self) -> str:
        """Get TC classification."""
        if self.tc is None:
            return "未检测"
        elif self.tc < 5.2:
            return "合适"
        elif self.tc < 6.2:
            return "边缘升高"
        else:
            return "升高"

    @property
    def tg_class(self) -> str:
        """Get TG classification."""
        if self.tg is None:
            return "未检测"
        elif self.tg < 1.7:
            return "合适"
        elif self.tg < 2.3:
            return "边缘升高"
        else:
            return "升高"

    @property
    def ldl_c_class(self) -> str:
        """Get LDL-C classification."""
        if self.ldl_c is None:
            return "未检测"
        elif self.ldl_c < 3.4:
            return "合适"
        elif self.ldl_c < 4.1:
            return "边缘升高"
        else:
            return "升高"

    @property
    def hdl_c_class(self) -> str:
        """Get HDL-C classification."""
        if self.hdl_c is None:
            return "未检测"
        elif self.hdl_c >= 1.0:
            return "合适"
        else:
            return "降低"

    @classmethod
    def from_dict(cls, data: dict) -> "LipidProfile":
        """Create LipidProfile from dictionary."""
        measured_at = data.get("measured_at")
        if measured_at:
            measured_at = datetime.fromisoformat(measured_at)
        return cls(
            tc=data.get("tc"),
            tg=data.get("tg"),
            ldl_c=data.get("ldl_c"),
            hdl_c=data.get("hdl_c"),
            measured_at=measured_at,
            source=data.get("source"),
        )
