"""
Patient ORM models.

Includes PatientHealthProfile for storing patient health data.
"""
from datetime import date
from typing import Any

from sqlalchemy import Date, String, Text
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import BaseModel
from src.domain.shared.enums.gender import GenderEnum


class PatientHealthProfile(BaseModel):
    """
    Patient health profile ORM model.

    Stores patient demographic and health information.
    """

    __tablename__ = "patient_health_profiles"

    patient_id: Mapped[str] = mapped_column(
        CHAR(36),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    age: Mapped[int | None] = mapped_column(
        String(10),
        nullable=True,
    )
    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    gender: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    emergency_contact: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    emergency_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    medical_history: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    allergies: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    chronic_conditions: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = super().to_dict()
        if self.birth_date:
            result["birth_date"] = self.birth_date.isoformat()
        return result
