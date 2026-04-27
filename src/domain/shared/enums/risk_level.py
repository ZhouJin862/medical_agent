"""Risk level enumeration."""

from enum import Enum


class RiskLevel(str, Enum):
    """Risk level enumeration for health conditions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @classmethod
    def from_string(cls, value: str) -> "RiskLevel":
        """Parse RiskLevel from string value."""
        normalized = value.lower().strip().replace("-", "_").replace(" ", "_")
        for level in cls:
            if level.value == normalized:
                return level
        raise ValueError(f"Invalid RiskLevel value: {value}")

    @property
    def display_name(self) -> str:
        """Get Chinese display name for the risk level."""
        display_names = {
            RiskLevel.LOW: "低风险",
            RiskLevel.MEDIUM: "中风险",
            RiskLevel.HIGH: "高风险",
            RiskLevel.VERY_HIGH: "极高风险",
        }
        return display_names.get(self, self.value)

    @property
    def numeric_value(self) -> int:
        """Get numeric value for comparison (0-3, higher is more severe)."""
        return {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.VERY_HIGH: 3,
        }[self]
