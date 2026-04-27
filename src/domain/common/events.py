"""
Domain Events - Base classes for domain events.

Contains:
- DomainEvent base class (imported from aggregates module)
"""

from src.domain.common.aggregates import DomainEvent

__all__ = ["DomainEvent"]
