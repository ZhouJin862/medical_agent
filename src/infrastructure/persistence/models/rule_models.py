"""
Rule models for configurable business logic.

Allows health assessment, risk prediction, and health plan rules
to be configured dynamically instead of hardcoded.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import String, Text, Float, Integer, JSON, Boolean
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import BaseModel


class RuleType:
    """Rule type enumeration."""
    THRESHOLD = "threshold"  # Value threshold rules (e.g., BP > 140/90)
    RANGE = "range"  # Value range rules (e.g., BMI between 18.5 and 24)
    SCORE = "score"  # Score-based rules (e.g., risk score calculation)
    CONDITION = "condition"  # Complex conditional rules
    REFERENCE = "reference"  # Reference value lookup


class RuleCategory:
    """Rule category enumeration."""
    VITAL_SIGN = "vital_sign"  # Blood pressure, glucose, etc.
    RISK_ASSESSMENT = "risk_assessment"  # Risk scoring rules
    DIAGNOSIS = "diagnosis"  # Disease diagnosis rules
    PRESCRIPTION = "prescription"  # Health plan prescription rules
    REFERENCE_VALUE = "reference_value"  # Normal value references


class RuleTargetType:
    """Target type for what the rule evaluates."""
    VITAL_SIGN = "vital_sign"  # Evaluates vital sign values
    QUESTIONNAIRE = "questionnaire"  # Evaluates questionnaire answers
    COMBINED = "combined"  # Combines multiple inputs


class RuleModel(BaseModel):
    """
    Business rule model.

    Stores configurable rules for health assessment, risk prediction,
    and health plan generation.
    """

    __tablename__ = "rules"

    # Basic information
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rule classification
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, default=RuleType.THRESHOLD)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, default=RuleTargetType.VITAL_SIGN)

    # Rule definition (JSON configuration)
    rule_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Rule metadata
    disease_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True,
        help_text="Associated disease code (for disease-specific rules)"
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, help_text="Evaluation priority (higher first)")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Version control for rule changes
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    change_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = super().to_dict()
        result["rule_type"] = self.rule_type
        result["category"] = self.category
        result["target_type"] = self.target_type
        return result


class RuleExecutionHistoryModel(BaseModel):
    """
    Rule execution history for audit and debugging.

    Tracks when rules were evaluated and their results.
    """

    __tablename__ = "rule_execution_history"

    rule_id: Mapped[str] = mapped_column(CHAR(36), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Input data
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Execution result
    result: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Execution metadata
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    consultation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    skill_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return super().to_dict()


class VitalSignStandardModel(BaseModel):
    """
    Vital sign reference standards.

    Stores normal ranges and threshold values for vital signs
    (e.g., blood pressure, blood glucose, BMI, etc.).
    """

    __tablename__ = "vital_sign_standards"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Vital sign type
    vital_sign_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        help_text="blood_pressure, blood_glucose, bmi, lipid_profile, uric_acid"
    )

    # Normal range
    normal_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    normal_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Thresholds for different risk levels
    low_risk_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low_risk_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    medium_risk_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    medium_risk_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    high_risk_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_risk_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    very_high_risk_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    very_high_risk_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Unit information
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gender_specific: Mapped[bool] = mapped_column(Boolean, default=False)

    # Age-specific adjustments (JSON)
    age_adjustments: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return super().to_dict()

    def get_risk_level(self, value: float, gender: str = "male", age: int = None) -> str:
        """
        Determine risk level based on value.

        Args:
            value: The vital sign value
            gender: Patient gender (for gender-specific standards)
            age: Patient age (for age-specific adjustments)

        Returns:
            Risk level: normal, low, medium, high, very_high
        """
        # Apply age adjustments if configured
        adjusted_value = self._apply_age_adjustments(value, age)

        if self.normal_min is not None and adjusted_value < self.normal_min:
            return "low"
        if self.normal_max is not None and adjusted_value > self.normal_max:
            return self._check_high_risk(adjusted_value)
        return "normal"

    def _apply_age_adjustments(self, value: float, age: Optional[int]) -> float:
        """Apply age-specific adjustments to thresholds."""
        if not age or not self.age_adjustments:
            return value

        # Simple age adjustment logic
        for adjustment in self.age_adjustments.get("adjustments", []):
            age_min = adjustment.get("age_min", 0)
            age_max = adjustment.get("age_max", 150)
            if age_min <= age <= age_max:
                multiplier = adjustment.get("multiplier", 1.0)
                return value * multiplier
        return value

    def _check_high_risk(self, value: float) -> str:
        """Check high risk level based on value ranges."""
        if self.very_high_risk_min is not None and value >= self.very_high_risk_min:
            return "very_high"
        if self.high_risk_min is not None and value >= self.high_risk_min:
            return "high"
        if self.medium_risk_min is not None and value >= self.medium_risk_min:
            return "medium"
        if self.low_risk_min is not None and value >= self.low_risk_min:
            return "low"
        return "normal"


class RiskScoreRuleModel(BaseModel):
    """
    Risk scoring rules.

    Defines how to calculate risk scores from various inputs.
    """

    __tablename__ = "risk_score_rules"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Disease association
    disease_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Scoring configuration
    scoring_config: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    """
    Example configuration:
    {
        "factors": [
            {"name": "blood_pressure", "weight": 0.3, "rule_reference": "bp_high"},
            {"name": "blood_glucose", "weight": 0.2, "rule_reference": "glucose_high"},
            {"name": "bmi", "weight": 0.25, "rule_reference": "bmi_high"},
            {"name": "age", "weight": 0.15, "rule_reference": "age_factor"},
            {"name": "family_history", "weight": 0.1, "rule_reference": "family_history"}
        ],
        "thresholds": {
            "low": 0.2,
            "medium": 0.4,
            "high": 0.6,
            "very_high": 0.8
        }
    }
    """

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")

    def calculate_score(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate risk score from input data.

        Args:
            input_data: Dictionary containing factor values

        Returns:
            Dictionary with score and risk level
        """
        factors = self.scoring_config.get("factors", [])
        thresholds = self.scoring_config.get("thresholds", {})

        total_score = 0.0
        factor_details = []

        for factor in factors:
            name = factor.get("name")
            weight = factor.get("weight", 0)
            value = input_data.get(name, 0)
            rule_ref = factor.get("rule_reference")

            # Calculate factor score (0-1)
            factor_score = self._normalize_factor(value, factor)
            weighted_score = factor_score * weight
            total_score += weighted_score

            factor_details.append({
                "name": name,
                "value": value,
                "weight": weight,
                "score": factor_score,
                "weighted_score": weighted_score
            })

        # Determine risk level from score
        risk_level = self._get_risk_level(total_score, thresholds)

        return {
            "score": round(total_score, 3),
            "risk_level": risk_level,
            "factor_details": factor_details
        }

    def _normalize_factor(self, value: Any, factor: Dict) -> float:
        """Normalize a factor value to 0-1 range."""
        factor_type = factor.get("type", "range")

        if factor_type == "range":
            min_val = factor.get("min", 0)
            max_val = factor.get("max", 1)
            normalized = (value - min_val) / (max_val - min_val)
            return max(0, min(1, normalized))
        elif factor_type == "binary":
            return 1.0 if value else 0.0
        elif factor_type == "categorical":
            categories = factor.get("categories", {})
            return categories.get(str(value), 0.5)
        else:
            return 0.5

    def _get_risk_level(self, score: float, thresholds: Dict[str, float]) -> str:
        """Get risk level from score."""
        if score >= thresholds.get("very_high", 0.8):
            return "very_high"
        elif score >= thresholds.get("high", 0.6):
            return "high"
        elif score >= thresholds.get("medium", 0.4):
            return "medium"
        elif score >= thresholds.get("low", 0.2):
            return "low"
        return "normal"
