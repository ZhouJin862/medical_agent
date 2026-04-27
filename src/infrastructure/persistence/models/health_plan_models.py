"""
Health Plan ORM models.

Includes HealthPlanModel and PrescriptionModel for storing
health management plans and prescriptions.
"""
import json
from enum import Enum
from typing import Any

from sqlalchemy import Enum as SQLEnum, ForeignKey, String, Text, Index
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models.base import BaseModel


class HealthPlanType(str, Enum):
    """Type of health plan."""

    COMPREHENSIVE = "comprehensive"
    DISEASE_SPECIFIC = "disease_specific"


class PrescriptionType(str, Enum):
    """Type of prescription."""

    DIET = "diet"
    EXERCISE = "exercise"
    SLEEP = "sleep"
    MEDICATION = "medication"
    PSYCHOLOGICAL = "psych"


class HealthPlanModel(BaseModel):
    """
    HealthPlan aggregate root ORM model.

    Represents a comprehensive health management plan for a patient.
    """

    __tablename__ = "health_plans"

    plan_id: Mapped[str] = mapped_column(
        CHAR(36),
        unique=True,
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        CHAR(36),
        nullable=False,
        index=True,
    )
    plan_type: Mapped[HealthPlanType] = mapped_column(
        SQLEnum(HealthPlanType),
        default=HealthPlanType.COMPREHENSIVE,
        nullable=False,
    )
    disease_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    valid_from: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    valid_until: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    prescriptions: Mapped[list["PrescriptionModel"]] = relationship(
        "PrescriptionModel",
        back_populates="health_plan",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PrescriptionModel.created_at",
    )

    __table_args__ = (
        Index("idx_health_plan_patient", "patient_id"),
        Index("idx_health_plan_disease", "disease_code"),
    )


class PrescriptionModel(BaseModel):
    """
    Prescription entity ORM model.

    Represents a specific prescription within a health plan.
    Can be diet, exercise, sleep, medication, or psychological prescription.
    """

    __tablename__ = "prescriptions"

    health_plan_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("health_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prescription_type: Mapped[PrescriptionType] = mapped_column(
        SQLEnum(PrescriptionType),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    frequency: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    health_plan: Mapped["HealthPlanModel"] = relationship(
        "HealthPlanModel",
        back_populates="prescriptions",
    )

    __table_args__ = (
        Index("idx_prescription_plan_type", "health_plan_id", "prescription_type"),
    )

    def set_content(self, data: dict[str, Any]) -> None:
        """Set prescription content."""
        self.content = data

    def get_content(self) -> dict[str, Any]:
        """Get prescription content."""
        if isinstance(self.content, str):
            try:
                return json.loads(self.content)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.content or {}
