"""
Medical Guideline ORM models.

Includes GuidelineModel for storing clinical practice guidelines
for disease prevention and treatment.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import String, Text, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import BaseModel


class GuidelineCategory:
    """Guideline category enumeration."""
    PREVENTION = "prevention"
    TREATMENT = "treatment"
    DIAGNOSIS = "diagnosis"
    MONITORING = "monitoring"
    LIFESTYLE = "lifestyle"
    COMPREHENSIVE = "comprehensive"


class GuidelineModel(BaseModel):
    """
    Medical practice guideline model.

    Stores comprehensive clinical practice guidelines for disease
    prevention, diagnosis, treatment, and monitoring.
    """

    __tablename__ = "guidelines"

    # Basic information
    guideline_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guideline_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Disease classification
    disease_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    disease_name: Mapped[str] = mapped_column(String(100), nullable=False)
    guideline_category: Mapped[str] = mapped_column(String(50), nullable=False, default=GuidelineCategory.COMPREHENSIVE)

    # Guideline content (JSON configuration)
    guideline_content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    """
    Example structure:
    {
        "prevention": {
            "primary_prevention": [...],
            "secondary_prevention": [...],
            "tertiary_prevention": [...]
        },
        "treatment": {
            "pharmacological": [...],
            "non_pharmacological": [...],
            "emergency": [...]
        },
        "diagnosis": {
            "diagnostic_criteria": [...],
            "differential_diagnosis": [...],
            "required_tests": [...]
        },
        "monitoring": {
            "routine_monitoring": [...],
            "frequency": "...",
            "alert_thresholds": [...]
        },
        "lifestyle": {
            "diet": [...],
            "exercise": [...],
            "sleep": [...],
            "smoking_alcohol": [...]
        },
        "risk_thresholds": {
            "low": {...},
            "medium": {...},
            "high": {...},
            "very_high": {...}
        }
    }
    """

    # Evidence and sources
    evidence_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sources: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    publication_year: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Metadata
    guideline_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    publisher: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Target population
    target_population: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    """
    Example:
    {
        "age_range": {"min": 18, "max": 75},
        "gender": ["male", "female"],
        "risk_factors": [...],
        "comorbidities": [...]
    }
    """

    __table_args__ = (
        Index("idx_guideline_disease_code", "disease_code"),
        Index("idx_guideline_category", "guideline_category"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return super().to_dict()

    def get_prevention_recommendations(self) -> List[Dict[str, Any]]:
        """Get prevention recommendations."""
        return self.guideline_content.get("prevention", {})

    def get_treatment_guidelines(self) -> Dict[str, Any]:
        """Get treatment guidelines."""
        return self.guideline_content.get("treatment", {})

    def get_lifestyle_recommendations(self) -> Dict[str, Any]:
        """Get lifestyle recommendations."""
        return self.guideline_content.get("lifestyle", {})

    def get_monitoring_requirements(self) -> Dict[str, Any]:
        """Get monitoring requirements."""
        return self.guideline_content.get("monitoring", {})

    def get_risk_thresholds(self) -> Dict[str, Any]:
        """Get risk thresholds."""
        return self.guideline_content.get("risk_thresholds", {})
