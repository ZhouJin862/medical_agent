"""
Base model for SQLAlchemy ORM.

Provides common fields and methods for all models.
"""
from datetime import datetime
from typing import Any
from uuid import uuid4
from enum import Enum

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        name = cls.__name__
        if name.endswith("Model"):
            name = name[:-5]
        # Convert CamelCase to snake_case
        result = []
        for i, c in enumerate(name):
            if c.isupper() and i > 0:
                result.append("_")
            result.append(c.lower())
        return "".join(result) + "s"

    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = []
        for key in self.__mapper__.columns.keys():
            if key not in ["created_at", "updated_at"]:
                value = getattr(self, key, None)
                if value is not None:
                    attrs.append(f"{key}={value!r}")
        return f"{class_name}({', '.join(attrs)})"


class BaseModel(Base):
    """Base model with common fields for all entities."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: uuid4().hex,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        for column in self.__mapper__.columns:
            value = getattr(self, column.key)
            if value is not None:
                if isinstance(value, datetime):
                    result[column.key] = value.isoformat()
                elif isinstance(value, Enum):
                    result[column.key] = value.value
                else:
                    result[column.key] = value
        return result

    def update(self, **kwargs: Any) -> None:
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ["id", "created_at"]:
                setattr(self, key, value)
