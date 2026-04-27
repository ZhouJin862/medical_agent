"""
ValueObject - Base class for value objects.

Provides:
- Value object equality based on all attributes
- Base value object functionality
"""

from abc import ABC


class ValueObject(ABC):
    """
    Base class for value objects.

    Value objects are identified by their attributes rather than an ID.
    Two value objects are equal if all their attributes are equal.
    """

    def __eq__(self, other: object) -> bool:
        """
        Check equality based on all attributes.

        Args:
            other: Another object to compare with

        Returns:
            True if both are value objects with the same attributes
        """
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """
        Hash based on all attributes.

        Returns:
            Hash of the value object's attributes
        """
        return hash(tuple(sorted(self.__dict__.items())))

    def __repr__(self) -> str:
        """String representation of the value object."""
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"
