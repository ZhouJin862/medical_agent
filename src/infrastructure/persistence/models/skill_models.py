"""
Skill ORM models.

Includes models for Skills, Skill Prompts, Skill Model Configs,
Disease Types, Knowledge Bases, and Vital Signs Standards.
"""
from enum import Enum
from typing import Any

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Integer,
    Index,
)
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import BaseModel


class SkillType(str, Enum):
    """Type of skill."""

    GENERIC = "generic"
    DISEASE_SPECIFIC = "disease_specific"
    PRESCRIPTION = "prescription"
    MCP_TOOL = "mcp_tool"


class SkillCategory(str, Enum):
    """Category of skill."""

    HEALTH_ASSESSMENT = "health_assessment"
    RISK_PREDICTION = "risk_prediction"
    HEALTH_PROMOTION = "health_promotion"
    PRESCRIPTION_GENERATION = "prescription_generation"
    TRIAGE_GUIDANCE = "triage_guidance"
    MEDICATION_CHECK = "medication_check"
    SERVICE_RECOMMENDATION = "service_recommendation"


class ModelProvider(str, Enum):
    """LLM model provider."""

    INTERNAL = "internal"  # GLM-5
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"


class SkillModel(BaseModel):
    """
    Skill aggregate root ORM model.

    Represents a configurable AI skill that can be dynamically loaded.
    """

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    type: Mapped[SkillType] = mapped_column(
        SQLEnum(SkillType),
        nullable=False,
        index=True,
    )
    category: Mapped[SkillCategory | None] = mapped_column(
        SQLEnum(SkillCategory),
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        default="1.0.0",
        nullable=False,
    )
    intent_keywords: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    __table_args__ = (
        Index("idx_skill_type_enabled", "type", "enabled"),
    )


class SkillPromptModel(BaseModel):
    """
    Skill Prompt ORM model.

    Stores prompt templates for different stages of skill execution.
    """

    __tablename__ = "skill_prompts"

    skill_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        default="1.0.0",
        nullable=False,
    )
    variables: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    __table_args__ = (
        Index("idx_skill_prompt_skill_type", "skill_id", "prompt_type"),
    )


class SkillModelConfigModel(BaseModel):
    """
    Skill Model Config ORM model.

    Stores LLM model configuration for each skill.
    """

    __tablename__ = "skill_model_configs"

    skill_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    model_provider: Mapped[ModelProvider] = mapped_column(
        SQLEnum(ModelProvider),
        default=ModelProvider.INTERNAL,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    temperature: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    max_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    top_p: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )


class DiseaseCategory(str, Enum):
    """Category of disease type."""

    FOUR_HIGHS = "four_highs"  # High blood pressure, glucose, lipids, uric acid
    OBESITY = "obesity"


class DiseaseTypeModel(BaseModel):
    """
    Disease Type ORM model.

    Stores disease type classifications for four-highs and obesity.
    """

    __tablename__ = "disease_types"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    name_en: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    category: Mapped[DiseaseCategory] = mapped_column(
        SQLEnum(DiseaseCategory),
        nullable=False,
    )
    icd_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("idx_disease_type_code", "code"),
    )


class KnowledgeType(str, Enum):
    """Type of knowledge base content."""

    GUIDELINE = "guideline"
    RISK_RULE = "risk_rule"
    REFERENCE = "reference"
    DRUG_GUIDE = "drug_guide"
    CARE_STANDARD = "care_standard"


class KnowledgeBaseModel(BaseModel):
    """
    Knowledge Base ORM model.

    Stores medical knowledge and guidelines for skill execution.
    """

    __tablename__ = "knowledge_bases"

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    disease_code: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("disease_types.code"),
        nullable=True,
        index=True,
    )
    knowledge_type: Mapped[KnowledgeType] = mapped_column(
        SQLEnum(KnowledgeType),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        default="1.0.0",
        nullable=False,
    )
    effective_date: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    __table_args__ = (
        Index("idx_knowledge_disease_type", "disease_code", "knowledge_type"),
    )


class RiskLevel(str, Enum):
    """Risk level classification."""

    NORMAL = "normal"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"


class VitalSignsStandardModel(BaseModel):
    """
    Vital Signs Standard ORM model.

    Stores reference ranges for vital signs indicators.
    Used for risk assessment and classification.
    """

    __tablename__ = "vital_signs_standards"

    indicator_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    indicator_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    disease_code: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("disease_types.code"),
        nullable=True,
        index=True,
    )
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Normal range
    normal_min: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    normal_max: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Low risk range (borderline)
    risk_low_min: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    risk_low_max: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Medium risk range
    risk_medium_min: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    risk_medium_max: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # High risk range
    risk_high_min: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    risk_high_max: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Gender specific (optional)
    gender: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # Age range (optional)
    age_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    age_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("idx_vital_signs_indicator", "indicator_code"),
        Index("idx_vital_signs_disease", "disease_code"),
    )
