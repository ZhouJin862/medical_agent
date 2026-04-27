"""
DSPy Framework - Declarative Skills for Health Assessment.

Provides:
- Signatures for different skill types
- Skill Registry for dynamic loading
- Skill Factory for creating skill instances
- Base Skill class for inheritance
"""

from .signatures.base import BaseSignature, InputField, OutputField
from .signatures.four_highs import (
    HealthAssessmentSignature,
    RiskPredictionSignature,
    HypertensionAssessmentSignature,
    DiabetesAssessmentSignature,
    DyslipidemiaAssessmentSignature,
    GoutAssessmentSignature,
    ObesityAssessmentSignature,
)
from .signatures.prescription import (
    DietPrescriptionSignature,
    ExercisePrescriptionSignature,
    SleepPrescriptionSignature,
    MedicationPrescriptionSignature,
)
from .skill_registry import SkillRegistry
from .skill_factory import SkillFactory
from .base_skill import BaseSkill

__all__ = [
    # Signatures
    "BaseSignature",
    "InputField",
    "OutputField",
    "HealthAssessmentSignature",
    "RiskPredictionSignature",
    "HypertensionAssessmentSignature",
    "DiabetesAssessmentSignature",
    "DyslipidemiaAssessmentSignature",
    "GoutAssessmentSignature",
    "ObesityAssessmentSignature",
    "DietPrescriptionSignature",
    "ExercisePrescriptionSignature",
    "SleepPrescriptionSignature",
    "MedicationPrescriptionSignature",
    # Core
    "SkillRegistry",
    "SkillFactory",
    "BaseSkill",
]
