"""
API response DTOs.

Defines Pydantic models for API responses.
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    consultation_id: str = Field(..., description="Consultation identifier")
    user_message: dict[str, Any] = Field(..., description="User message data")
    ai_response: dict[str, Any] = Field(..., description="AI response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    model_config = {"json_schema_extra": {"example": {
        "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_message": {
            "id": "msg-001",
            "role": "user",
            "content": "我今天感觉有点头晕",
        },
        "ai_response": {
            "id": "msg-002",
            "role": "assistant",
            "content": "请问您头晕持续多久了？有没有伴随其他症状...",
        },
    }}}


class VitalSignsAssessment(BaseModel):
    """Response model for vital signs assessment."""

    value: str = Field(..., description="Measured value")
    classification: str = Field(..., description="Classification category")
    is_normal: bool = Field(..., description="Whether value is normal")
    risk_level: str = Field(..., description="Risk level")


class Recommendation(BaseModel):
    """Response model for health recommendation."""

    category: str = Field(..., description="Recommendation category")
    priority: str = Field(..., description="Priority level")
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Recommendation description")


class HealthProfileResponse(BaseModel):
    """Response model for health profile endpoint."""

    assessment_id: str = Field(..., description="Assessment identifier")
    patient_id: str = Field(..., description="Patient identifier")
    vital_signs: dict[str, Any] = Field(..., description="Vital signs data")
    assessments: dict[str, VitalSignsAssessment] = Field(..., description="Assessment results")
    overall_risk: str = Field(..., description="Overall risk level")
    recommendations: list[Recommendation] = Field(default_factory=list, description="Health recommendations")
    assessed_at: str = Field(..., description="Assessment timestamp")

    model_config = {"json_schema_extra": {"example": {
        "assessment_id": "assess-001",
        "patient_id": "123e4567-e89b-12d3-a456-426614174000",
        "vital_signs": {
            "blood_pressure": {"systolic": 140, "diastolic": 90},
        },
        "assessments": {
            "blood_pressure": {
                "value": "140/90 mmHg",
                "classification": "高血压1级",
                "is_normal": False,
                "risk_level": "high_risk",
            },
        },
        "overall_risk": "high_risk",
        "recommendations": [
            {
                "category": "blood_pressure",
                "priority": "high",
                "title": "血压管理建议",
                "description": "建议减少钠盐摄入，增加运动...",
            },
        ],
        "assessed_at": "2024-01-15T10:30:00",
    }}}


class PrescriptionDetail(BaseModel):
    """Response model for prescription detail."""

    id: str = Field(..., description="Prescription identifier")
    type: str = Field(..., description="Prescription type")
    created_at: str = Field(..., description="Creation timestamp")
    details: dict[str, Any] = Field(..., description="Prescription details")


class HealthPlanResponse(BaseModel):
    """Response model for health plan endpoint."""

    plan_id: str = Field(..., description="Health plan identifier")
    patient_id: str = Field(..., description="Patient identifier")
    plan_type: str = Field(..., description="Type of health plan")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    total_prescriptions: int = Field(..., description="Total number of prescriptions")
    prescriptions_by_type: dict[str, int] = Field(default_factory=dict, description="Prescriptions grouped by type")
    prescription_details: list[PrescriptionDetail] = Field(default_factory=list, description="Prescription details")
    target_goals: dict[str, int] = Field(..., description="Target goals summary")

    model_config = {"json_schema_extra": {"example": {
        "plan_id": "plan-001",
        "patient_id": "123e4567-e89b-12d3-a456-426614174000",
        "plan_type": "preventive",
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00",
        "total_prescriptions": 4,
        "prescriptions_by_type": {
            "diet": 1,
            "exercise": 1,
            "sleep": 1,
            "psychological": 1,
        },
        "prescription_details": [],
        "target_goals": {
            "total": 3,
            "active": 3,
            "achieved": 0,
        },
    }}}


class MessageResponse(BaseModel):
    """Response model for a single message."""

    id: str = Field(..., description="Message identifier")
    consultation_id: str = Field(..., description="Consultation identifier")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    intent: str | None = Field(None, description="Classified intent")
    created_at: str = Field(..., description="Message timestamp")


class ConsultationSummary(BaseModel):
    """Response model for consultation summary."""

    consultation_id: str = Field(..., description="Consultation identifier")
    patient_id: str = Field(..., description="Patient identifier")
    status: str = Field(..., description="Consultation status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages")

    model_config = {"json_schema_extra": {"example": {
        "consultation_id": "consult-001",
        "patient_id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "active",
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:30:00",
        "message_count": 12,
    }}}


class ConsultationHistoryResponse(BaseModel):
    """Response model for consultation history endpoint."""

    consultations: list[ConsultationSummary] = Field(..., description="List of consultations")
    total_count: int = Field(..., description="Total number of consultations")
    patient_id: str = Field(..., description="Patient identifier")


class SkillResponse(BaseModel):
    """Response model for skill endpoint."""

    id: str = Field(..., description="Skill identifier")
    name: str = Field(..., description="Unique skill name")
    display_name: str = Field(..., description="Display name")
    description: str | None = Field(None, description="Skill description")
    type: str = Field(..., description="Skill type")
    category: str | None = Field(None, description="Skill category")
    enabled: bool = Field(..., description="Whether skill is enabled")
    version: str = Field(..., description="Skill version")
    intent_keywords: list[str] | None = Field(None, description="Intent keywords")
    config: dict[str, Any] | None = Field(None, description="Additional config")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = {"json_schema_extra": {"example": {
        "id": "skill-001",
        "name": "hypertension_assessment",
        "display_name": "高血压评估",
        "description": "高血压风险评估和健康建议",
        "type": "disease_specific",
        "category": "health_assessment",
        "enabled": True,
        "version": "1.0.0",
        "intent_keywords": ["高血压", "血压"],
        "config": None,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    }}}


class SkillListResponse(BaseModel):
    """Response model for skill list endpoint."""

    skills: list[SkillResponse] = Field(..., description="List of skills")
    total_count: int = Field(..., description="Total number of skills")


class ErrorResponse(BaseModel):
    """Response model for error responses."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# ── Standard Assessment API Response Types ──────────────────────────────


class PopulationClassification(BaseModel):
    category: str = Field(..., description="健康 | 亚健康 | 慢病 | 专病")
    label: str = Field(..., description="Human-readable label")
    basis: list[str] = Field(default_factory=list, description="Classification criteria")


class DataCollectionRecommendation(BaseModel):
    item: str = Field(..., description="Recommended test / indicator name")
    reason: str = Field(..., description="Why this data is recommended")
    priority: str = Field(default="recommended", description="recommended | optional")


class AbnormalIndicator(BaseModel):
    name: str = Field(..., description="Indicator name")
    value: Any = Field(..., description="Measured value")
    unit: str = Field(default="", description="Unit of measurement")
    reference_range: str = Field(default="", description="Normal range")
    severity: str = Field(default="", description="Severity level")
    clinical_note: str = Field(default="", description="Clinical interpretation")


class DiseasePrediction(BaseModel):
    disease_name: str = Field(..., description="Predicted disease")
    probability: str = Field(default="", description="Probability estimate")
    probability_range: str = Field(default="", description="Probability range")
    risk_level: str = Field(..., description="低危 | 中危 | 高危 | 很高危")
    timeframe: str = Field(default="", description="Prediction timeframe")
    risk_model: str = Field(default="", description="Risk model used")
    key_contributing_factors: list[str] = Field(default_factory=list)


class InterventionPrescription(BaseModel):
    type: str = Field(..., description="Prescription type (diet, exercise, sleep, monitoring, medication)")
    title: str = Field(..., description="Human-readable title")
    content: str = Field(..., description="Prescription details")
    priority: str = Field(default="medium", description="high | medium | low")


class AssessmentResult(BaseModel):
    population_classification: PopulationClassification | None = None
    recommended_data_collection: list[DataCollectionRecommendation] = Field(default_factory=list)
    abnormal_indicators: list[AbnormalIndicator] = Field(default_factory=list)
    disease_prediction: list[DiseasePrediction] = Field(default_factory=list)
    intervention_prescriptions: list[InterventionPrescription] = Field(default_factory=list)


class AssessmentMetadata(BaseModel):
    data_source: str = Field(..., description="ping_an_api | request_body")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    timestamp: str = Field(..., description="Assessment timestamp")
    skill_version: str = Field(default="1.0")


class AssessmentResponse(BaseModel):
    """Response model for standard assessment API."""
    code: int = Field(default=200)
    success: bool = Field(default=True)
    data: dict[str, Any] = Field(..., description="Assessment data envelope")

    model_config = {"json_schema_extra": {"example": {
        "error": "ValidationError",
        "message": "Invalid request data",
        "detail": "patient_id is required",
    }}}


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Current timestamp")
    services: dict[str, str] = Field(default_factory=dict, description="Service statuses")

    model_config = {"json_schema_extra": {"example": {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": "2024-01-15T10:00:00",
        "services": {
            "database": "connected",
            "redis": "connected",
        },
    }}}


# Streaming Chat Response Types

class StreamingChatChunk(BaseModel):
    """A single chunk in a streaming chat response."""

    type: str = Field(..., description="Chunk type: start|token|end|error")
    session_id: str | None = Field(None, description="Session identifier")
    content: str | None = Field(None, description="Content for token chunks")
    full_response: str | None = Field(None, description="Full response for end chunks")
    intent: str | None = Field(None, description="Classified intent")
    confidence: float | None = Field(None, description="Intent confidence")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Chunk timestamp")
    error: str | None = Field(None, description="Error message for error chunks")


class StreamingChatStartChunk(StreamingChatChunk):
    """Start chunk for streaming chat."""

    type: str = "start"
    session_id: str
    timestamp: str


class StreamingChatTokenChunk(StreamingChatChunk):
    """Token chunk for streaming chat."""

    type: str = "token"
    content: str


class StreamingChatEndChunk(StreamingChatChunk):
    """End chunk for streaming chat."""

    type: str = "end"
    full_response: str
    intent: str | None = None
    confidence: float | None = None
    suggested_skill: str | None = None
    skill_result: dict | None = None
    multi_skill_selection: dict | None = None
    multi_skill_result: dict | None = None


class StreamingChatErrorChunk(StreamingChatChunk):
    """Error chunk for streaming chat."""

    type: str = "error"
    error: str


# System Prompt Response Types

class SystemPromptResponse(BaseModel):
    """Response model for a system prompt."""

    id: str = Field(..., description="Prompt version identifier")
    prompt_key: str = Field(..., description="Unique prompt key")
    description: str = Field(..., description="Brief description of the prompt")
    content: str = Field(..., description="Full prompt text")
    version: int = Field(..., description="Version number")
    is_active: bool = Field(..., description="Whether this version is active")
    variables: list[str] | None = Field(None, description="Template variable names")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = {"json_schema_extra": {"example": {
        "id": "abc123",
        "prompt_key": "medical_assistant_streaming",
        "description": "流式聊天主 system prompt",
        "content": "你是一个专业的健康管理助手...",
        "version": 1,
        "is_active": True,
        "variables": None,
        "updated_at": "2024-01-15T10:00:00",
    }}}


class SystemPromptListItem(BaseModel):
    """List item for system prompts."""

    id: str = Field(..., description="Prompt version identifier")
    prompt_key: str = Field(..., description="Unique prompt key")
    description: str = Field(..., description="Brief description")
    version: int = Field(..., description="Current active version")
    variables: list[str] | None = Field(None, description="Template variables")
    updated_at: str = Field(..., description="Last update timestamp")


class SystemPromptListResponse(BaseModel):
    """Response model for listing system prompts."""

    prompts: list[SystemPromptListItem] = Field(..., description="List of active prompts")
    total_count: int = Field(..., description="Total number of prompts")


class SystemPromptHistoryItem(BaseModel):
    """History item for a prompt version."""

    id: str = Field(..., description="Version identifier")
    prompt_key: str = Field(..., description="Prompt key")
    version: int = Field(..., description="Version number")
    is_active: bool = Field(..., description="Whether this version is active")
    description: str = Field(..., description="Description")
    updated_at: str = Field(..., description="Last update timestamp")


class SystemPromptHistoryResponse(BaseModel):
    """Response model for prompt version history."""

    prompt_key: str = Field(..., description="Prompt key")
    versions: list[SystemPromptHistoryItem] = Field(..., description="Version history")


class SystemPromptUpdateRequest(BaseModel):
    """Request model for updating a system prompt."""

    content: str = Field(..., description="New prompt content")
    description: str | None = Field(None, description="Updated description")


class QuestionnaireDetailResponse(BaseModel):
    """Response model for questionnaire detail endpoint."""

    questionnaire_id: str = Field(..., description="Questionnaire business ID")
    title: str = Field(..., description="Questionnaire title")
    description: str | None = Field(None, description="Questionnaire description")
    skill_name: str | None = Field(None, description="Associated skill name")
    questions: list[dict[str, Any]] = Field(default_factory=list, description="Question list (frontend format)")
    version: int = Field(default=1, description="Questionnaire version")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = {"json_schema_extra": {"example": {
        "questionnaire_id": "cvd-basic",
        "title": "心血管基础问卷",
        "description": "心血管病风险评估基础信息采集",
        "skill_name": "cvd-risk-assessment",
        "questions": [],
        "version": 1,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-01-15T10:00:00",
    }}}


class InsightResponse(BaseModel):
    """Response model for insight query endpoint."""

    party_id: str = Field(..., description="Customer identifier")
    skill_name: str = Field(..., description="Assessment skill name")
    risk_level: str = Field(default="", description="Risk level label")
    population_classification: dict[str, Any] | None = Field(None)
    abnormal_indicators: list[dict[str, Any]] = Field(default_factory=list)
    recommended_data_collection: list[dict[str, Any]] = Field(default_factory=list)
    disease_prediction: list[dict[str, Any]] = Field(default_factory=list)
    intervention_prescriptions: list[dict[str, Any]] = Field(default_factory=list)
    assessed_at: str = Field(..., description="Assessment timestamp")

    model_config = {"json_schema_extra": {"example": {
        "party_id": "P001",
        "skill_name": "cvd-risk-assessment",
        "risk_level": "高危",
        "population_classification": {"category": "专病", "label": "高危", "basis": []},
        "abnormal_indicators": [],
        "recommended_data_collection": [],
        "disease_prediction": [],
        "intervention_prescriptions": [],
        "assessed_at": "2024-01-15T10:30:00",
    }}}
