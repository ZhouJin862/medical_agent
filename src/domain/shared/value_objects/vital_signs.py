"""Vital signs base value object."""

from abc import ABC, abstractmethod
from datetime import datetime


class VitalSigns(ABC):
    """Base class for vital signs value objects.

    Note: This is NOT a dataclass because Python dataclasses don't handle
    inheritance well when mixing required and optional fields.
    Subclasses should be dataclasses with their own field definitions.
    """

    @abstractmethod
    def is_normal(self) -> bool:
        """Check if the vital sign is within normal range."""

    @abstractmethod
    def get_classification(self) -> str:
        """Get the classification category for this vital sign."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
