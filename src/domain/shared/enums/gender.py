"""Gender enumeration."""

from enum import Enum


class GenderEnum(str, Enum):
    """Patient gender enumeration."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "GenderEnum":
        """Parse gender from string value."""
        normalized = value.lower().strip()
        for gender in cls:
            if gender.value == normalized:
                return gender
        raise ValueError(f"Invalid gender value: {value}")
