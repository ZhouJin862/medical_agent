"""
SQLAlchemy ORM models.

Import all models here so they get registered with SQLAlchemy's metadata.
This file should be imported before calling Base.metadata.create_all().
"""

# Import base model first
from .base import Base, BaseModel

# Import all domain models
from .rule_models import (
    RuleModel,
    RuleExecutionHistoryModel,
    VitalSignStandardModel,
    RiskScoreRuleModel,
)

# Import skill models
from .skill_models import (
    SkillModel,
    SkillPromptModel,
    SkillModelConfigModel,
)

# Import consultation models
from .consultation_models import (
    ConsultationModel,
    MessageModel,
)

# Import patient models
from .patient_models import PatientHealthProfile

# Import guideline models
from .guideline_models import GuidelineModel, GuidelineCategory

# Import system prompt models
from .system_prompt_models import SystemPromptModel

# Import assessment insight models
from .assessment_insight import AssessmentInsightModel

# Import questionnaire models
from .questionnaire import QuestionnaireModel

# Export Base and all models
__all__ = [
    "Base",
    "BaseModel",
    "RuleModel",
    "RuleExecutionHistoryModel",
    "VitalSignStandardModel",
    "RiskScoreRuleModel",
    "SkillModel",
    "SkillPromptModel",
    "SkillModelConfigModel",
    "ConsultationModel",
    "MessageModel",
    "PatientHealthProfile",
    "GuidelineModel",
    "GuidelineCategory",
    "SystemPromptModel",
    "AssessmentInsightModel",
    "QuestionnaireModel",
]
