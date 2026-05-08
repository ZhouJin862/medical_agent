"""Service for querying questionnaire definitions."""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models.questionnaire import QuestionnaireModel

logger = logging.getLogger(__name__)


class QuestionnaireService:
    """Service for questionnaire operations."""

    @staticmethod
    async def get_by_type(session: AsyncSession, questionnaire_type: str) -> Optional[QuestionnaireModel]:
        """Get a questionnaire by its type identifier (e.g. 'cvd-basic')."""
        stmt = (
            select(QuestionnaireModel)
            .where(QuestionnaireModel.questionnaire_id == questionnaire_type)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
