"""IHealthPlanRepository interface."""
from abc import ABC, abstractmethod

from src.domain.health_plan.entities.health_plan import HealthPlan
from src.domain.health_plan.value_objects.health_plan_id import HealthPlanId


class IHealthPlanRepository(ABC):
    """Repository interface for HealthPlan aggregate."""

    @abstractmethod
    async def save(self, health_plan: HealthPlan) -> None:
        """Save a health plan."""
        pass

    @abstractmethod
    async def find_by_id(self, plan_id: HealthPlanId) -> HealthPlan | None:
        """Find a health plan by its ID."""
        pass

    @abstractmethod
    async def find_by_patient_id(self, patient_id: str) -> list[HealthPlan]:
        """Find all health plans for a patient."""
        pass

    @abstractmethod
    async def delete(self, plan_id: HealthPlanId) -> bool:
        """Delete a health plan by its ID."""
        pass

    @abstractmethod
    async def exists(self, plan_id: HealthPlanId) -> bool:
        """Check if a health plan exists."""
        pass
