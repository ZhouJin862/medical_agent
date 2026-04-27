"""
Consultation API routes.

Provides endpoints for consultation history and management.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, status, HTTPException

from src.application.services.consultation_service import ConsultationApplicationService
from src.interface.api.dto.response import ConsultationSummary, ConsultationHistoryResponse
from src.interface.api.dependencies import get_consultation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.get("/patient/{patient_id}", response_model=ConsultationHistoryResponse)
async def get_consultation_history(
    patient_id: str,
    limit: int = 10,
    consultation_service: ConsultationApplicationService = Depends(get_consultation_service),
) -> ConsultationHistoryResponse:
    """
    Get consultation history for a patient.

    Args:
        patient_id: Patient identifier
        limit: Maximum number of consultations to return
        consultation_service: Injected consultation service

    Returns:
        Consultation history with summaries
    """
    if limit <= 0 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100",
        )

    consultations = await consultation_service.get_consultation_history(
        patient_id=patient_id,
        limit=limit,
    )

    # Get message count for each consultation is included in the result

    return ConsultationHistoryResponse(
        consultations=[ConsultationSummary(**c) for c in consultations],
        total_count=len(consultations),
        patient_id=patient_id,
    )


@router.get("/{consultation_id}", response_model=ConsultationSummary)
async def get_consultation(
    consultation_id: str,
    consultation_service: ConsultationApplicationService = Depends(get_consultation_service),
) -> ConsultationSummary | None:
    """
    Get consultation by ID.

    Args:
        consultation_id: Consultation identifier
        consultation_service: Injected consultation service

    Returns:
        Consultation summary or None
    """
    consultation = await consultation_service.get_consultation(
        consultation_id=consultation_id,
    )

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

    return ConsultationSummary(**consultation)


@router.get("/{consultation_id}/summary", response_model=dict)
async def get_consultation_summary(
    consultation_id: str,
    consultation_service: ConsultationApplicationService = Depends(get_consultation_service),
) -> dict[str, Any]:
    """
    Get detailed consultation summary.

    Args:
        consultation_id: Consultation identifier
        consultation_service: Injected consultation service

    Returns:
        Detailed consultation summary with statistics
    """
    summary = await consultation_service.get_consultation_summary(
        consultation_id=consultation_id,
    )

    return summary
