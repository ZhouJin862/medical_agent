"""
Health plan API routes.

Provides endpoints for health plan operations.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, status, HTTPException

from src.application.services.health_plan_service import HealthPlanApplicationService
from src.interface.api.dto.request import CreateHealthPlanRequest
from src.interface.api.dto.response import HealthPlanResponse
from src.interface.api.dependencies import get_health_plan_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plan", tags=["plan"])


@router.post("/generate", response_model=dict, status_code=status.HTTP_201_CREATED)
async def generate_health_plan(
    request: CreateHealthPlanRequest,
    service: HealthPlanApplicationService = Depends(get_health_plan_service),
) -> dict[str, Any]:
    """
    Generate a new health plan for a patient.

    Args:
        request: Health plan creation request
        service: Injected health plan service

    Returns:
        Generated health plan data
    """
    result = await service.generate_health_plan(
        patient_id=request.patient_id,
        assessment_data=None,  # Could be fetched from assessment_id if provided
        plan_type=request.plan_type,
    )

    return result


@router.get("/{plan_id}", response_model=HealthPlanResponse)
async def get_health_plan(
    plan_id: str,
    service: HealthPlanApplicationService = Depends(get_health_plan_service),
) -> HealthPlanResponse | None:
    """
    Get health plan by ID.

    Args:
        plan_id: Health plan identifier
        service: Injected health plan service

    Returns:
        Health plan data or None
    """
    result = await service.get_health_plan(
        plan_id=plan_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health plan {plan_id} not found",
        )

    return HealthPlanResponse(**result)


@router.get("/patient/{patient_id}", response_model=list[HealthPlanResponse])
async def get_patient_health_plans(
    patient_id: str,
    service: HealthPlanApplicationService = Depends(get_health_plan_service),
) -> list[HealthPlanResponse]:
    """
    Get all health plans for a patient.

    Args:
        patient_id: Patient identifier
        service: Injected health plan service

    Returns:
        List of health plan data
    """
    result = await service.get_patient_health_plans(
        patient_id=patient_id,
    )

    return [HealthPlanResponse(**plan) for plan in result]
