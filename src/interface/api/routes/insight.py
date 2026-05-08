"""Insight query API route."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.domain.insight.services.insight_service import InsightService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["insight"])


@router.get("/insight/{party_id}")
async def get_insight(party_id: str, session: AsyncSession = Depends(get_db_session)):
    """Get the latest assessment insight for a customer."""
    record = await InsightService.get_latest_by_party_id(session, party_id)
    if not record:
        raise HTTPException(status_code=404, detail="未找到该客户的洞察记录")

    return JSONResponse(content={
        "code": 200,
        "success": True,
        "data": {
            "party_id": record.party_id,
            "skill_name": record.skill_name,
            "risk_level": record.risk_level,
            "population_classification": record.population_classification,
            "abnormal_indicators": record.abnormal_indicators or [],
            "recommended_data_collection": record.recommended_data_collection or [],
            "disease_prediction": record.disease_prediction or [],
            "intervention_prescriptions": record.intervention_prescriptions or [],
            "assessed_at": record.created_date.isoformat() if record.created_date else "",
        },
    })
