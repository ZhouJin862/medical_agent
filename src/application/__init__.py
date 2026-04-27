"""Application layer module."""

from src.application.services import (
    ChatApplicationService,
    HealthAssessmentApplicationService,
    HealthPlanApplicationService,
    ConsultationApplicationService,
    SkillManagementApplicationService,
)
from src.application.commands import (
    AssessHealthCommand,
    CreateHealthPlanCommand,
    SaveConversationCommand,
    SendMessageCommand,
    CloseConsultationCommand,
    CreateSkillCommand,
    UpdateSkillCommand,
    EnableSkillCommand,
    DisableSkillCommand,
    ReloadSkillCommand,
    DeleteSkillCommand,
    UpdateSkillPromptCommand,
    UpdateSkillModelConfigCommand,
)
from src.application.queries import (
    GetConsultationHistoryQuery,
    GetPatientHealthProfileQuery,
    GetHealthPlanQuery,
    GetPatientHealthPlansQuery,
    GetConsultationMessagesQuery,
    GetConsultationSummaryQuery,
    GetSkillListQuery,
    GetSkillByIdQuery,
    GetSkillPromptsQuery,
    GetSkillModelConfigQuery,
)
from src.application.handlers import (
    ConsultationCommandHandlers,
    SkillCommandHandlers,
    ConsultationQueryHandlers,
    SkillQueryHandlers,
)

__all__ = [
    # Services
    "ChatApplicationService",
    "HealthAssessmentApplicationService",
    "HealthPlanApplicationService",
    "ConsultationApplicationService",
    "SkillManagementApplicationService",
    # Commands
    "AssessHealthCommand",
    "CreateHealthPlanCommand",
    "SaveConversationCommand",
    "SendMessageCommand",
    "CloseConsultationCommand",
    "CreateSkillCommand",
    "UpdateSkillCommand",
    "EnableSkillCommand",
    "DisableSkillCommand",
    "ReloadSkillCommand",
    "DeleteSkillCommand",
    "UpdateSkillPromptCommand",
    "UpdateSkillModelConfigCommand",
    # Queries
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
    # Handlers
    "ConsultationCommandHandlers",
    "SkillCommandHandlers",
    "ConsultationQueryHandlers",
    "SkillQueryHandlers",
]
