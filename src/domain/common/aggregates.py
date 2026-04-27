"""
AggregateRoot - Base class for all domain aggregates.

Provides:
- Domain event management
- Entity equality
- Base aggregate functionality
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Any
from datetime import datetime


@dataclass
class DomainEvent:
    """
    Base class for domain events.

    Domain events are immutable - once created they cannot be modified.

    Attributes:
        event_id: Unique event identifier
        occurred_at: When the event occurred
        aggregate_id: ID of the aggregate that raised this event
        event_type: Type name of the event
    """

    event_id: str
    occurred_at: datetime = field(default_factory=datetime.now)
    aggregate_id: str = ""
    event_type: str = ""

    def __post_init__(self):
        """Set event type from class name if not provided."""
        if not self.event_type:
            self.event_type = self.__class__.__name__


class AggregateRoot(ABC):
    """
    Base class for all aggregate roots.

    Provides:
    - Domain event management
    - Entity equality by ID
    - Version tracking
    """

    def __init__(self):
        """Initialize the aggregate root."""
        self._domain_events: List[DomainEvent] = []
        self._version: int = 0

    def _add_domain_event(self, event: DomainEvent) -> None:
        """
        Add a domain event to the pending list.

        Args:
            event: Domain event to add
        """
        self._domain_events.append(event)
        self._version += 1

    def pull_domain_events(self) -> List[DomainEvent]:
        """
        Pull all pending domain events.

        Returns:
            List of domain events and clears the pending list
        """
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    @property
    def domain_events(self) -> List[DomainEvent]:
        """Get read-only view of domain events."""
        return list(self._domain_events)

    @property
    def version(self) -> int:
        """Get the current aggregate version."""
        return self._version

    def clear_domain_events(self) -> None:
        """Clear all pending domain events without publishing them."""
        self._domain_events.clear()

    @abstractmethod
    def get_id(self) -> str:
        """Get the unique identifier for this aggregate."""
        pass
