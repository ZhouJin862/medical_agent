"""Four highs type enumeration."""

from enum import Enum


class FourHighsType(str, Enum):
    """Enumeration of the four common chronic conditions (四高)."""

    HYPERTENSION = "hypertension"
    DIABETES = "diabetes"
    DYSLIPIDEMIA = "dyslipidemia"
    GOUT = "gout"

    @classmethod
    def from_string(cls, value: str) -> "FourHighsType":
        """Parse FourHighsType from string value."""
        normalized = value.lower().strip()
        for disease_type in cls:
            if disease_type.value == normalized:
                return disease_type
        raise ValueError(f"Invalid FourHighsType value: {value}")

    @property
    def display_name(self) -> str:
        """Get Chinese display name for the disease type."""
        display_names = {
            FourHighsType.HYPERTENSION: "高血压",
            FourHighsType.DIABETES: "糖尿病",
            FourHighsType.DYSLIPIDEMIA: "血脂异常",
            FourHighsType.GOUT: "痛风",
        }
        return display_names.get(self, self.value)

    @property
    def english_name(self) -> str:
        """Get English name for the disease type."""
        english_names = {
            FourHighsType.HYPERTENSION: "Hypertension",
            FourHighsType.DIABETES: "Diabetes",
            FourHighsType.DYSLIPIDEMIA: "Dyslipidemia",
            FourHighsType.GOUT: "Gout",
        }
        return english_names.get(self, self.value.title())
