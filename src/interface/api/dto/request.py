"""
API request DTOs.

Defines Pydantic models for API requests.
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    patient_id: str = Field(..., description="Patient identifier")
    message_content: str = Field(..., min_length=1, description="User message content")
    consultation_id: str | None = Field(None, description="Existing consultation ID")

    model_config = {"json_schema_extra": {"example": {
        "patient_id": "123e4567-e89b-12d3-a456-426614174000",
        "message_content": "我今天感觉有点头晕，血压有点高",
        "consultation_id": None,
    }}}


class HealthAssessmentRequest(BaseModel):
    """Request model for health assessment endpoint."""

    patient_id: str = Field(..., description="Patient identifier")
    systolic: float | None = Field(None, ge=0, le=300, description="Systolic blood pressure (mmHg)")
    diastolic: float | None = Field(None, ge=0, le=200, description="Diastolic blood pressure (mmHg)")
    fasting_glucose: float | None = Field(None, ge=0, le=50, description="Fasting blood glucose (mmol/L)")
    random_glucose: float | None = Field(None, ge=0, le=50, description="Random blood glucose (mmol/L)")
    total_cholesterol: float | None = Field(None, ge=0, le=30, description="Total cholesterol (mmol/L)")
    ldl_cholesterol: float | None = Field(None, ge=0, le=20, description="LDL cholesterol (mmol/L)")
    hdl_cholesterol: float | None = Field(None, ge=0, le=10, description="HDL cholesterol (mmol/L)")
    triglycerides: float | None = Field(None, ge=0, le=20, description="Triglycerides (mmol/L)")
    uric_acid: float | None = Field(None, ge=0, le=1000, description="Uric acid (μmol/L)")
    height: float | None = Field(None, gt=0, le=300, description="Height (cm)")
    weight: float | None = Field(None, gt=0, le=500, description="Weight (kg)")

    @field_validator('systolic', 'diastolic')
    @classmethod
    def validate_blood_pressure(cls, v: float | None, info) -> float | None:
        """Validate blood pressure values are provided together."""
        if info.field_name == 'systolic' and v is not None:
            # Check if diastolic is also provided when calling
            # This is a simplified check - in real implementation would check both
            pass
        return v

    model_config = {"json_schema_extra": {"example": {
        "patient_id": "123e4567-e89b-12d3-a456-426614174000",
        "systolic": 140,
        "diastolic": 90,
        "fasting_glucose": 6.5,
        "total_cholesterol": 5.8,
        "ldl_cholesterol": 3.9,
        "hdl_cholesterol": 1.1,
        "triglycerides": 2.1,
        "uric_acid": 450,
        "height": 175,
        "weight": 80,
    }}}


class CreateHealthPlanRequest(BaseModel):
    """Request model for health plan creation endpoint."""

    patient_id: str = Field(..., description="Patient identifier")
    plan_type: str = Field("preventive", description="Type of health plan")
    assessment_id: str | None = Field(None, description="Health assessment ID to base plan on")

    @field_validator('plan_type')
    @classmethod
    def validate_plan_type(cls, v: str) -> str:
        """Validate plan type."""
        valid_types = ["preventive", "treatment", "recovery", "chronic_management", "wellness"]
        if v not in valid_types:
            raise ValueError(f"plan_type must be one of {valid_types}")
        return v

    model_config = {"json_schema_extra": {"example": {
        "patient_id": "123e4567-e89b-12d3-a456-426614174000",
        "plan_type": "preventive",
        "assessment_id": None,
    }}}


class SaveConversationRequest(BaseModel):
    """Request model for saving conversation endpoint."""

    consultation_id: str = Field(..., description="Consultation identifier")
    messages: list[dict[str, Any]] = Field(..., min_length=1, description="List of messages to save")

    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate each message has required fields."""
        for msg in v:
            if "role" not in msg:
                raise ValueError("Each message must have a 'role' field")
            if "content" not in msg:
                raise ValueError("Each message must have a 'content' field")
            if msg["role"] not in ["user", "assistant", "system"]:
                raise ValueError("Message role must be 'user', 'assistant', or 'system'")
        return v

    model_config = {"json_schema_extra": {"example": {
        "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好！我是您的健康助手"},
        ],
    }}}


class SkillCreateRequest(BaseModel):
    """Request model for skill creation endpoint."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique skill name")
    display_name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: str | None = Field(None, description="Skill description")
    skill_type: str = Field(..., description="Type of skill")
    category: str | None = Field(None, description="Category of skill")
    intent_keywords: list[str] | None = Field(None, description="Keywords for intent matching")
    config: dict[str, Any] | None = Field(None, description="Additional configuration")
    model_config: dict[str, Any] | None = Field(None, description="LLM model configuration")
    prompts: dict[str, str] | None = Field(None, description="Prompt templates")

    @field_validator('skill_type')
    @classmethod
    def validate_skill_type(cls, v: str) -> str:
        """Validate skill type."""
        valid_types = ["generic", "disease_specific", "prescription", "mcp_tool"]
        if v not in valid_types:
            raise ValueError(f"skill_type must be one of {valid_types}")
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate category."""
        if v is None:
            return v
        valid_categories = [
            "health_assessment",
            "risk_prediction",
            "health_promotion",
            "prescription_generation",
            "triage_guidance",
            "medication_check",
            "service_recommendation",
        ]
        if v not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}")
        return v

    model_config = {"json_schema_extra": {"example": {
        "name": "hypertension_assessment",
        "display_name": "高血压评估",
        "description": "高血压风险评估和健康建议",
        "skill_type": "disease_specific",
        "category": "health_assessment",
        "intent_keywords": ["高血压", "血压", "头晕"],
    }}}


class SkillUpdateRequest(BaseModel):
    """Request model for skill update endpoint."""

    display_name: str | None = Field(None, description="New display name")
    description: str | None = Field(None, description="New description")
    intent_keywords: list[str] | None = Field(None, description="New intent keywords")
    config: dict[str, Any] | None = Field(None, description="New configuration")

    model_config = {"json_schema_extra": {"example": {
        "display_name": "高血压评估（更新版）",
        "description": "更新的高血压风险评估和健康建议",
        "intent_keywords": ["高血压", "血压", "头晕", "头痛"],
    }}}


class SkillPromptUpdateRequest(BaseModel):
    """Request model for skill prompt update endpoint."""

    prompt_type: str = Field(..., description="Type of prompt")
    content: str = Field(..., min_length=1, description="Prompt content")

    model_config = {"json_schema_extra": {"example": {
        "prompt_type": "system",
        "content": "你是一位专业的健康管理助手...",
    }}}


class SkillModelConfigUpdateRequest(BaseModel):
    """Request model for skill model config update endpoint."""

    provider: str | None = Field(None, description="Model provider")
    model_name: str | None = Field(None, description="Model name")
    temperature: float | None = Field(None, ge=0, le=2, description="Temperature for generation")
    max_tokens: int | None = Field(None, gt=0, le=100000, description="Max tokens to generate")
    top_p: float | None = Field(None, ge=0, le=1, description="Top-p sampling parameter")
    extra_config: dict[str, Any] | None = Field(None, description="Additional model config")

    model_config = {"json_schema_extra": {"example": {
        "provider": "internal",
        "model_name": "glm-5",
        "temperature": 0.7,
        "max_tokens": 2000,
        "top_p": 0.9,
    }}}


class CloseConsultationRequest(BaseModel):
    """Request model for closing consultation endpoint."""

    consultation_id: str = Field(..., description="Consultation identifier")

    model_config = {"json_schema_extra": {"example": {
        "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
    }}}


class StreamingChatRequest(BaseModel):
    """Request model for streaming chat endpoint."""

    session_id: str | None = Field(None, description="Session ID (creates new session if not provided)")
    patient_id: str = Field(..., description="Patient identifier")
    message: str = Field(..., min_length=1, description="User message content")
    questionnaire_answers: dict[str, Any] | None = Field(None, description="Questionnaire answers {question_id: value} submitted from frontend")

    model_config = {"json_schema_extra": {"example": {
        "session_id": None,
        "patient_id": "patient_001",
        "message": "继续评估",
        "questionnaire_answers": {"gender-select": "male", "q_age_picker": 45, "height-input": 170, "weight-input": 75},
    }}}


# Allowed skill names for the standard assessment API
ASSESSMENT_SKILLS = [
    "cvd-risk-assessment",
    "hypertension-risk-assessment",
    "hyperglycemia-risk-assessment",
    "hyperlipidemia-risk-assessment",
    "hyperuricemia-risk-assessment",
    "obesity-risk-assessment",
    "population-classification",
]

# Package shorthands that expand to multiple skills
SKILL_PACKAGES = {
    "package@assessment": ASSESSMENT_SKILLS,
}


def _normalize_skills(v: str | list[str]) -> list[str]:
    """Normalize skill input to a flat list of individual skill names.

    Accepts:
      - Single string:  "cvd-risk-assessment"
      - List of strings: ["cvd-risk-assessment", "hypertension-risk-assessment"]
      - Package shorthand: "package@assessment" → all ASSESSMENT_SKILLS
      - Mixed: ["package@assessment", "cvd-risk-assessment"]
    """
    if isinstance(v, str):
        v = [v]
    expanded: list[str] = []
    for item in v:
        pkg = SKILL_PACKAGES.get(item)
        if pkg:
            expanded.extend(pkg)
        else:
            expanded.append(item)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for s in expanded:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


class AssessmentRequest(BaseModel):
    """Request model for standard assessment API (third-party integration)."""

    party_id: str = Field(..., description="Patient / customer identifier")
    skill: str | list[str] = Field(..., description="Skill(s) to execute. Accepts a single skill name, an array, or a package shorthand like 'package@assessment'.")
    patient_data: dict[str, Any] | None = Field(None, description="Patient basic info (age, gender). Auto-fetched from Ping An API if omitted.")
    vital_signs: dict[str, Any] | None = Field(None, description="Vital signs data. Auto-fetched from Ping An API if omitted.")
    medical_history: dict[str, Any] | None = Field(None, description="Medical history. Auto-fetched from Ping An API if omitted.")
    questionnaire_answers: dict[str, Any] | None = Field(None, description="Questionnaire answers {question_id: value} submitted from frontend")
    session_id: str | None = Field(None, description="会话ID（首次不传，后续传返回值中的 session_id）")
    re_assessment: bool = Field(False, description="是否重新评估。为 true 时清空上次会话数据，返回全量问卷题目")

    @field_validator("skill", mode="before")
    @classmethod
    def validate_and_normalize_skill(cls, v: str | list[str]) -> list[str]:
        skills = _normalize_skills(v)
        for s in skills:
            if s not in ASSESSMENT_SKILLS:
                raise ValueError(f"Unknown skill: {s}. Available: {ASSESSMENT_SKILLS}")
        return skills

    model_config = {"json_schema_extra": {"examples": [
        {
            "party_id": "123",
            "skill": "cvd-risk-assessment",
            "patient_data": {"age": 26, "gender": "男"},
            "vital_signs": {"systolic_bp": 150, "diastolic_bp": 95},
            "medical_history": {"disease_labels": ["高血压"]},
        },
        {
            "party_id": "123",
            "skill": ["cvd-risk-assessment", "hypertension-risk-assessment"],
        },
        {
            "party_id": "123",
            "skill": "package@assessment",
        },
    ]}}
