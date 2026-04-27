"""
Health API routes.

Provides endpoints for health assessment operations.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, status, HTTPException

from src.application.services.health_assessment_service import (
    HealthAssessmentApplicationService,
)
from src.interface.api.dto.request import HealthAssessmentRequest
from src.interface.api.dto.response import HealthProfileResponse
from src.interface.api.dependencies import get_health_assessment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


@router.post("/assess", response_model=HealthProfileResponse, status_code=status.HTTP_200_OK)
async def assess_health(
    request: HealthAssessmentRequest,
    service: HealthAssessmentApplicationService = Depends(get_health_assessment_service),
) -> HealthProfileResponse:
    """
    Assess patient health from vital signs.

    Args:
        request: Health assessment request with vital signs data
        service: Injected health assessment service

    Returns:
        Health profile with assessments and recommendations
    """
    vital_signs_data = {
        "systolic": request.systolic,
        "diastolic": request.diastolic,
        "fasting_glucose": request.fasting_glucose,
        "random_glucose": request.random_glucose,
        "total_cholesterol": request.total_cholesterol,
        "ldl_cholesterol": request.ldl_cholesterol,
        "hdl_cholesterol": request.hdl_cholesterol,
        "triglycerides": request.triglycerides,
        "uric_acid": request.uric_acid,
        "height": request.height,
        "weight": request.weight,
    }

    # Remove None values
    vital_signs_data = {k: v for k, v in vital_signs_data.items() if v is not None}

    if not vital_signs_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one vital sign measurement is required",
        )

    result = await service.assess_vital_signs(
        patient_id=request.patient_id,
        vital_signs_data=vital_signs_data,
    )

    return HealthProfileResponse(**result)


@router.get("/{patient_id}", response_model=dict)
async def get_patient_health_profile(
    patient_id: str,
    service: HealthAssessmentApplicationService = Depends(get_health_assessment_service),
) -> dict[str, Any]:
    """
    Get patient health profile.

    Args:
        patient_id: Patient identifier
        service: Injected health assessment service

    Returns:
        Patient health profile data
    """
    result = await service.get_patient_health_profile(
        patient_id=patient_id,
    )

    return result
