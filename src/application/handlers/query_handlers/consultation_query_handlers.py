"""
Consultation query handlers.

Handles queries for consultation-related read operations.
"""
import logging
from typing import Any

from src.application.queries.consultation_queries import (
    GetConsultationHistoryQuery,
    GetPatientHealthProfileQuery,
    GetHealthPlanQuery,
    GetPatientHealthPlansQuery,
    GetConsultationMessagesQuery,
    GetConsultationSummaryQuery,
)
from src.application.services.consultation_service import ConsultationApplicationService
from src.application.services.health_assessment_service import (
    HealthAssessmentApplicationService,
)
from src.application.services.health_plan_service import HealthPlanApplicationService

logger = logging.getLogger(__name__)


class ConsultationQueryHandlers:
    """
    Handlers for consultation-related queries.

    Coordinates with application services to execute queries.
    """

    def __init__(
        self,
        consultation_service: ConsultationApplicationService,
        health_assessment_service: HealthAssessmentApplicationService,
        health_plan_service: HealthPlanApplicationService,
    ) -> None:
        """
        Initialize consultation query handlers.

        Args:
            consultation_service: Consultation service
            health_assessment_service: Health assessment service
            health_plan_service: Health plan service
        """
        self._consultation_service = consultation_service
        self._health_assessment_service = health_assessment_service
        self._health_plan_service = health_plan_service

    async def handle_get_consultation_history(
        self,
        query: GetConsultationHistoryQuery,
    ) -> list[dict[str, Any]]:
        """
        Handle get consultation history query.

        Args:
            query: GetConsultationHistoryQuery

        Returns:
            List of consultation summaries
        """
        logger.info(f"Getting consultation history for patient {query.patient_id}")

        result = await self._consultation_service.get_consultation_history(
            patient_id=query.patient_id,
            limit=query.limit,
        )

        logger.info(f"Retrieved {len(result)} consultations")

        return result

    async def handle_get_patient_health_profile(
        self,
        query: GetPatientHealthProfileQuery,
    ) -> dict[str, Any]:
        """
        Handle get patient health profile query.

        Args:
            query: GetPatientHealthProfileQuery

        Returns:
            Patient health profile data
        """
        logger.info(f"Getting health profile for patient {query.patient_id}")

        result = await self._health_assessment_service.get_patient_health_profile(
            patient_id=query.patient_id,
        )

        return result

    async def handle_get_health_plan(
        self,
        query: GetHealthPlanQuery,
    ) -> dict[str, Any] | None:
        """
        Handle get health plan query.

        Args:
            query: GetHealthPlanQuery

        Returns:
            Health plan data or None
        """
        logger.info(f"Getting health plan {query.plan_id}")

        result = await self._health_plan_service.get_health_plan(
            plan_id=query.plan_id,
        )

        return result

    async def handle_get_patient_health_plans(
        self,
        query: GetPatientHealthPlansQuery,
    ) -> list[dict[str, Any]]:
        """
        Handle get patient health plans query.

        Args:
            query: GetPatientHealthPlansQuery

        Returns:
            List of health plan summaries
        """
        logger.info(f"Getting health plans for patient {query.patient_id}")

        result = await self._health_plan_service.get_patient_health_plans(
            patient_id=query.patient_id,
        )

        logger.info(f"Retrieved {len(result)} health plans")

        return result

    async def handle_get_consultation_messages(
        self,
        query: GetConsultationMessagesQuery,
    ) -> list[dict[str, Any]]:
        """
        Handle get consultation messages query.

        Args:
            query: GetConsultationMessagesQuery

        Returns:
            List of message data
        """
        logger.info(f"Getting messages for consultation {query.consultation_id}")

        result = await self._consultation_service.get_consultation_messages(
            consultation_id=query.consultation_id,
            limit=query.limit,
            before_id=query.before_id,
        )

        logger.info(f"Retrieved {len(result)} messages")

        return result

    async def handle_get_consultation_summary(
        self,
        query: GetConsultationSummaryQuery,
    ) -> dict[str, Any]:
        """
        Handle get consultation summary query.

        Args:
            query: GetConsultationSummaryQuery

        Returns:
            Consultation summary data
        """
        logger.info(f"Getting summary for consultation {query.consultation_id}")

        result = await self._consultation_service.get_consultation_summary(
            consultation_id=query.consultation_id,
        )

        return result
