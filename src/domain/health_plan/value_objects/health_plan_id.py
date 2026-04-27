"""Health Plan ID value object."""
from dataclasses import dataclass

from src.domain.common.value_objects import ValueObject


@dataclass(frozen=True)
class HealthPlanId(ValueObject):
    """Value object representing a health plan identifier."""

    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("HealthPlanId must be a non-empty string")

    def __str__(self) -> str:
        return f"HealthPlanId({self.value})"
