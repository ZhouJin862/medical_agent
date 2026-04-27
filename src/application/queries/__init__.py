"""Application queries module."""

from src.application.queries.consultation_queries import (
    GetConsultationHistoryQuery,
    GetPatientHealthProfileQuery,
    GetHealthPlanQuery,
    GetPatientHealthPlansQuery,
    GetConsultationMessagesQuery,
    GetConsultationSummaryQuery,
)
from src.application.queries.skill_queries import (
    GetSkillListQuery,
    GetSkillByIdQuery,
    GetSkillPromptsQuery,
    GetSkillModelConfigQuery,
)

__all__ = [
    "GetConsultationHistoryQuery",
    "GetPatientHealthProfileQuery",
    "GetHealthPlanQuery",
    "GetPatientHealthPlansQuery",
    "GetConsultationMessagesQuery",
    "GetConsultationSummaryQuery",
    "GetSkillListQuery",
    "GetSkillByIdQuery",
    "GetSkillPromptsQuery",
    "GetSkillModelConfigQuery",
]
