"""
Entity - Base class for all domain entities.

Provides:
- Entity equality by ID
- Base entity functionality
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class Entity(ABC):
    """
    Base class for all domain entities.

    Entities are identified by their ID and compared by equality of that ID.
    """

    @abstractmethod
    def get_id(self) -> str:
        """
        Get the unique identifier for this entity.

        Returns:
            Unique entity identifier
        """
        pass

    def __eq__(self, other: object) -> bool:
        """
        Check equality based on entity ID.

        Args:
            other: Another object to compare with

        Returns:
            True if both are entities with the same ID
        """
        if not isinstance(other, Entity):
            return False
        return self.get_id() == other.get_id()

    def __hash__(self) -> int:
        """
        Hash based on entity ID.

        Returns:
            Hash of the entity ID
        """
        return hash(self.get_id())

    def __repr__(self) -> str:
        """String representation of the entity."""
        return f"{self.__class__.__name__}(id={self.get_id()})"
