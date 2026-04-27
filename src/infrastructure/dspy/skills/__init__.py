"""
DSPy Skills - Concrete skill implementations.

This module contains:
- General health assessment skills
- Disease-specific skills (四高一重)
- Prescription skills
- MCP Tool skills
"""

from .general_skills import (
    HealthAssessmentSkill,
    RiskPredictionSkill,
    HealthProfileSkill,
)
from .disease_skills import (
    HypertensionSkill,
    DiabetesSkill,
    DyslipidemiaSkill,
    GoutSkill,
    ObesitySkill,
    MetabolicSyndromeSkill,
)
from .prescription_skills import (
    DietPrescriptionSkill,
    ExercisePrescriptionSkill,
    SleepPrescriptionSkill,
)
from .medication_prescription_skill import MedicationPrescriptionSkill
from .mcp_tool_skills import (
    TriageGuidanceSkill,
    MedicationCheckSkill,
    ServiceRecommendSkill,
)

__all__ = [
    # General Skills
    "HealthAssessmentSkill",
    "RiskPredictionSkill",
    "HealthProfileSkill",
    # Disease Skills
    "HypertensionSkill",
    "DiabetesSkill",
    "DyslipidemiaSkill",
    "GoutSkill",
    "ObesitySkill",
    "MetabolicSyndromeSkill",
    # Prescription Skills
    "DietPrescriptionSkill",
    "ExercisePrescriptionSkill",
    "SleepPrescriptionSkill",
    "MedicationPrescriptionSkill",
    # MCP Tool Skills
    "TriageGuidanceSkill",
    "MedicationCheckSkill",
    "ServiceRecommendSkill",
]
