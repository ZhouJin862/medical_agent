"""
Health Plan repository implementation.

Implements IHealthPlanRepository using SQLAlchemy ORM.
"""
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.health_plan.repositories.health_plan_repository import (
    IHealthPlanRepository,
)
from src.infrastructure.persistence.models.health_plan_models import (
    HealthPlanModel,
    PrescriptionModel,
    HealthPlanType,
    PrescriptionType,
)

logger = logging.getLogger(__name__)


class HealthPlanRepositoryImpl(IHealthPlanRepository):
    """
    Implementation of IHealthPlanRepository.

    Uses SQLAlchemy async session for database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create_health_plan(
        self,
        plan_id: str,
        patient_id: str,
        plan_type: HealthPlanType = HealthPlanType.COMPREHENSIVE,
        disease_code: str | None = None,
        title: str | None = None,
        description: str | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
    ) -> dict[str, Any]:
        """Create a new health plan."""
        health_plan = HealthPlanModel(
            id=uuid4().hex,
            plan_id=plan_id,
            patient_id=patient_id,
            plan_type=plan_type,
            disease_code=disease_code,
            title=title,
            plan_desc=description,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        self._session.add(health_plan)
        await self._session.flush()
        return health_plan.to_dict()

    async def get_health_plan_by_id(self, plan_id: str) -> dict[str, Any] | None:
        """Get health plan by ID."""
        stmt = select(HealthPlanModel).where(HealthPlanModel.plan_id == plan_id)
        result = await self._session.execute(stmt)
        health_plan = result.scalar_one_or_none()
        return health_plan.to_dict() if health_plan else None

    async def get_active_health_plan(
        self, patient_id: str
    ) -> dict[str, Any] | None:
        """Get active health plan for a patient."""
        stmt = (
            select(HealthPlanModel)
            .where(HealthPlanModel.patient_id == patient_id)
            .order_by(desc(HealthPlanModel.created_date))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        health_plan = result.scalar_one_or_none()
        return health_plan.to_dict() if health_plan else None

    async def get_health_plans_by_patient(
        self, patient_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get all health plans for a patient."""
        stmt = (
            select(HealthPlanModel)
            .where(HealthPlanModel.patient_id == patient_id)
            .order_by(desc(HealthPlanModel.created_date))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        health_plans = result.scalars().all()
        return [hp.to_dict() for hp in health_plans]

    async def get_health_plans_by_disease(
        self, disease_code: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get health plans by disease code."""
        stmt = (
            select(HealthPlanModel)
            .where(HealthPlanModel.disease_code == disease_code)
            .order_by(desc(HealthPlanModel.created_date))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        health_plans = result.scalars().all()
        return [hp.to_dict() for hp in health_plans]

    async def add_prescription(
        self,
        health_plan_id: str,
        prescription_type: PrescriptionType,
        title: str,
        content: dict[str, Any],
        priority: str | None = None,
        frequency: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a prescription to a health plan."""
        # Get health plan's internal ID
        stmt = select(HealthPlanModel.id).where(
            HealthPlanModel.plan_id == health_plan_id
        )
        result = await self._session.execute(stmt)
        health_plan_internal_id = result.scalar_one_or_none()

        if not health_plan_internal_id:
            raise ValueError(f"Health plan {health_plan_id} not found")

        prescription = PrescriptionModel(
            id=uuid4().hex,
            health_plan_id=health_plan_internal_id,
            prescription_type=prescription_type,
            title=title,
            prescription_content=content,
            prescription_priority=priority,
            frequency=frequency,
            notes=notes,
        )
        self._session.add(prescription)
        await self._session.flush()
        return prescription.to_dict()

    async def get_prescriptions(
        self, health_plan_id: str
    ) -> list[dict[str, Any]]:
        """Get all prescriptions for a health plan."""
        stmt = select(HealthPlanModel.id).where(
            HealthPlanModel.plan_id == health_plan_id
        )
        result = await self._session.execute(stmt)
        health_plan_internal_id = result.scalar_one_or_none()

        if not health_plan_internal_id:
            return []

        stmt = select(PrescriptionModel).where(
            PrescriptionModel.health_plan_id == health_plan_internal_id
        )
        stmt = stmt.order_by(PrescriptionModel.created_date)
        result = await self._session.execute(stmt)
        prescriptions = result.scalars().all()
        return [rx.to_dict() for rx in prescriptions]

    async def get_prescriptions_by_type(
        self,
        health_plan_id: str,
        prescription_type: PrescriptionType,
    ) -> list[dict[str, Any]]:
        """Get prescriptions filtered by type."""
        stmt = select(HealthPlanModel.id).where(
            HealthPlanModel.plan_id == health_plan_id
        )
        result = await self._session.execute(stmt)
        health_plan_internal_id = result.scalar_one_or_none()

        if not health_plan_internal_id:
            return []

        stmt = select(PrescriptionModel).where(
            and_(
                PrescriptionModel.health_plan_id == health_plan_internal_id,
                PrescriptionModel.prescription_type == prescription_type,
            )
        )
        stmt = stmt.order_by(PrescriptionModel.created_date)
        result = await self._session.execute(stmt)
        prescriptions = result.scalars().all()
        return [rx.to_dict() for rx in prescriptions]

    async def update_prescription(
        self,
        prescription_id: str,
        title: str | None = None,
        content: dict[str, Any] | None = None,
        priority: str | None = None,
        frequency: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """Update a prescription."""
        stmt = select(PrescriptionModel).where(
            PrescriptionModel.id == int(prescription_id)
        )
        result = await self._session.execute(stmt)
        prescription = result.scalar_one_or_none()

        if prescription:
            if title is not None:
                prescription.title = title
            if content is not None:
                prescription.prescription_content = content
            if priority is not None:
                prescription.prescription_priority = priority
            if frequency is not None:
                prescription.frequency = frequency
            if notes is not None:
                prescription.notes = notes
            return True
        return False

    async def delete_prescription(self, prescription_id: str) -> bool:
        """Delete a prescription."""
        stmt = select(PrescriptionModel).where(
            PrescriptionModel.id == int(prescription_id)
        )
        result = await self._session.execute(stmt)
        prescription = result.scalar_one_or_none()

        if prescription:
            await self._session.delete(prescription)
            return True
        return False

    async def update_health_plan(
        self,
        plan_id: str,
        title: str | None = None,
        description: str | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
    ) -> bool:
        """Update health plan metadata."""
        stmt = select(HealthPlanModel).where(HealthPlanModel.plan_id == plan_id)
        result = await self._session.execute(stmt)
        health_plan = result.scalar_one_or_none()

        if health_plan:
            if title is not None:
                health_plan.title = title
            if description is not None:
                health_plan.plan_desc = description
            if valid_from is not None:
                health_plan.valid_from = valid_from
            if valid_until is not None:
                health_plan.valid_until = valid_until
            return True
        return False

    async def delete_health_plan(self, plan_id: str) -> bool:
        """Delete a health plan (cascade deletes prescriptions)."""
        stmt = select(HealthPlanModel).where(HealthPlanModel.plan_id == plan_id)
        result = await self._session.execute(stmt)
        health_plan = result.scalar_one_or_none()

        if health_plan:
            await self._session.delete(health_plan)
            return True
        return False

    async def count_health_plans(self, patient_id: str) -> int:
        """Count total health plans for a patient."""
        stmt = (
            select(func.count(HealthPlanModel.id))
            .where(HealthPlanModel.patient_id == patient_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_latest_prescription_by_type(
        self,
        patient_id: str,
        prescription_type: PrescriptionType,
    ) -> dict[str, Any] | None:
        """Get the latest prescription of a specific type for a patient."""
        # First get the patient's latest health plan
        hp_stmt = (
            select(HealthPlanModel.id)
            .where(HealthPlanModel.patient_id == patient_id)
            .order_by(desc(HealthPlanModel.created_date))
            .limit(1)
        )
        hp_result = await self._session.execute(hp_stmt)
        health_plan_internal_id = hp_result.scalar_one_or_none()

        if not health_plan_internal_id:
            return None

        # Then get the latest prescription of the specified type
        stmt = (
            select(PrescriptionModel)
            .where(
                and_(
                    PrescriptionModel.health_plan_id == health_plan_internal_id,
                    PrescriptionModel.prescription_type == prescription_type,
                )
            )
            .order_by(desc(PrescriptionModel.created_date))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        prescription = result.scalar_one_or_none()
        return prescription.to_dict() if prescription else None
