"""
Health Plan repository interface.

Defines the contract for health plan persistence operations.
"""
from abc import ABC, abstractmethod
from typing import Any

from src.infrastructure.persistence.models.health_plan_models import (
    HealthPlanType,
    PrescriptionType,
)


class IHealthPlanRepository(ABC):
    """
    Interface for HealthPlan repository.

    Defines methods for managing health plans and prescriptions.
    """

    @abstractmethod
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
        """
        Create a new health plan.

        Args:
            plan_id: Unique plan identifier
            patient_id: Patient identifier
            plan_type: Type of health plan
            disease_code: Associated disease code (for disease-specific plans)
            title: Plan title
            description: Plan description
            valid_from: Valid from date
            valid_until: Valid until date

        Returns:
            Created health plan data
        """

    @abstractmethod
    async def get_health_plan_by_id(self, plan_id: str) -> dict[str, Any] | None:
        """
        Get health plan by ID.

        Args:
            plan_id: Plan identifier

        Returns:
            Health plan data or None if not found
        """

    @abstractmethod
    async def get_active_health_plan(
        self, patient_id: str
    ) -> dict[str, Any] | None:
        """
        Get active health plan for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            Active health plan or None if not found
        """

    @abstractmethod
    async def get_health_plans_by_patient(
        self, patient_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get all health plans for a patient.

        Args:
            patient_id: Patient identifier
            limit: Maximum number of plans to return

        Returns:
            List of health plan data
        """

    @abstractmethod
    async def get_health_plans_by_disease(
        self, disease_code: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get health plans by disease code.

        Args:
            disease_code: Disease code
            limit: Maximum number of plans to return

        Returns:
            List of health plan data
        """

    @abstractmethod
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
        """
        Add a prescription to a health plan.

        Args:
            health_plan_id: Health plan identifier
            prescription_type: Type of prescription
            title: Prescription title
            content: Prescription content (structured data)
            priority: Priority level
            frequency: Execution frequency
            notes: Additional notes

        Returns:
            Created prescription data
        """

    @abstractmethod
    async def get_prescriptions(
        self, health_plan_id: str
    ) -> list[dict[str, Any]]:
        """
        Get all prescriptions for a health plan.

        Args:
            health_plan_id: Health plan identifier

        Returns:
            List of prescription data
        """

    @abstractmethod
    async def get_prescriptions_by_type(
        self,
        health_plan_id: str,
        prescription_type: PrescriptionType,
    ) -> list[dict[str, Any]]:
        """
        Get prescriptions filtered by type.

        Args:
            health_plan_id: Health plan identifier
            prescription_type: Type to filter by

        Returns:
            List of prescription data
        """

    @abstractmethod
    async def update_prescription(
        self,
        prescription_id: str,
        title: str | None = None,
        content: dict[str, Any] | None = None,
        priority: str | None = None,
        frequency: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Update a prescription.

        Args:
            prescription_id: Prescription identifier
            title: New title
            content: New content
            priority: New priority
            frequency: New frequency
            notes: New notes

        Returns:
            True if updated successfully
        """

    @abstractmethod
    async def delete_prescription(self, prescription_id: str) -> bool:
        """
        Delete a prescription.

        Args:
            prescription_id: Prescription identifier

        Returns:
            True if deleted successfully
        """

    @abstractmethod
    async def update_health_plan(
        self,
        plan_id: str,
        title: str | None = None,
        description: str | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
    ) -> bool:
        """
        Update health plan metadata.

        Args:
            plan_id: Plan identifier
            title: New title
            description: New description
            valid_from: New valid from date
            valid_until: New valid until date

        Returns:
            True if updated successfully
        """

    @abstractmethod
    async def delete_health_plan(self, plan_id: str) -> bool:
        """
        Delete a health plan (cascade deletes prescriptions).

        Args:
            plan_id: Plan identifier

        Returns:
            True if deleted successfully
        """

    @abstractmethod
    async def count_health_plans(self, patient_id: str) -> int:
        """
        Count total health plans for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            Number of health plans
        """

    @abstractmethod
    async def get_latest_prescription_by_type(
        self,
        patient_id: str,
        prescription_type: PrescriptionType,
    ) -> dict[str, Any] | None:
        """
        Get the latest prescription of a specific type for a patient.

        Args:
            patient_id: Patient identifier
            prescription_type: Type of prescription

        Returns:
            Latest prescription data or None
        """
