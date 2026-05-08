"""Service for querying and persisting assessment insights."""
import logging
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models.assessment_insight import AssessmentInsightModel

logger = logging.getLogger(__name__)


class InsightService:
    """Service for assessment insight operations."""

    @staticmethod
    async def get_latest_by_party_id(session: AsyncSession, party_id: str) -> Optional[AssessmentInsightModel]:
        """Get the latest insight for a party_id."""
        stmt = (
            select(AssessmentInsightModel)
            .where(AssessmentInsightModel.party_id == party_id)
            .order_by(AssessmentInsightModel.created_date.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def save(
        session: AsyncSession,
        party_id: str,
        skill_name: str,
        structured_result: Dict[str, Any],
    ) -> None:
        """Persist an assessment insight record. Silently logs errors, never raises."""
        try:
            if not structured_result:
                return

            record = AssessmentInsightModel(
                party_id=party_id,
                skill_name=skill_name,
                created_by="system",
                updated_by="system",
                risk_level="",
                population_classification=structured_result.get("population_classification"),
                abnormal_indicators=structured_result.get("abnormal_indicators"),
                recommended_data_collection=structured_result.get("recommended_data_collection"),
                disease_prediction=structured_result.get("disease_prediction"),
                intervention_prescriptions=structured_result.get("intervention_prescriptions"),
                full_result=structured_result,
            )
            session.add(record)
            await session.flush()
            logger.info(f"Saved insight for party_id={party_id}, skill={skill_name}")
        except Exception as e:
            logger.warning(f"Failed to save insight for party_id={party_id}: {e}")
