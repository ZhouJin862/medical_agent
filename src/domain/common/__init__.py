"""
Domain Common - Shared domain components.

Contains:
- AggregateRoot base class
- Domain events
- Repository interfaces
- Entity base class
- ValueObject base class
"""

from .aggregates import AggregateRoot
from .entities import Entity
from .events import DomainEvent
from .value_objects import ValueObject

__all__ = ["AggregateRoot", "Entity", "DomainEvent", "ValueObject"]
