"""
MedicationRecommendation Value Object - Medication recommendations.

Encapsulates:
- Current medication assessment
- Suggested alternatives
- Warnings and interactions
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class MedicationStatus(Enum):
    """Status of medication assessment."""

    APPROPRIATE = "appropriate"  # 用药合理
    CAUTION = "caution"  # 需谨慎使用
    CONTRAINDICATED = "contraindicated"  # 禁忌
    ALTERNATIVE_RECOMMENDED = "alternative_recommended"  # 建议替代


@dataclass
class CurrentMedication:
    """
    Current medication being taken.

    Attributes:
        medication_id: Medication identifier
        name: Medication name
        dosage: Current dosage
        frequency: How often taken
        status: Assessment status
        warnings: Any warnings
    """

    medication_id: str
    name: str
    dosage: str
    frequency: str
    status: MedicationStatus
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "medication_id": self.medication_id,
            "name": self.name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "status": self.status.value,
            "warnings": self.warnings,
        }


@dataclass
class MedicationRecommendation:
    """
    Medication recommendation.

    Attributes:
        medication_id: Medication identifier
        name: Medication name
        recommended_dosage: Recommended dosage
        recommended_frequency: Recommended frequency
        reason: Reason for recommendation
        contraindications: Any contraindications
    """

    medication_id: str
    name: str
    recommended_dosage: str
    recommended_frequency: str
    reason: str
    contraindications: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "medication_id": self.medication_id,
            "name": self.name,
            "recommended_dosage": self.recommended_dosage,
            "recommended_frequency": self.recommended_frequency,
            "reason": self.reason,
            "contraindications": self.contraindications,
        }


@dataclass
class MedicationRecommendationResult:
    """
    Complete medication recommendation result.

    Attributes:
        current_medications: Assessment of current medications
        recommended_medications: Suggested medications
        interactions: Drug interaction warnings
        general_advice: General medication advice
    """

    current_medications: List[CurrentMedication] = field(default_factory=list)
    recommended_medications: List[MedicationRecommendation] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    general_advice: List[str] = field(default_factory=list)

    def has_contraindications(self) -> bool:
        """Check if any contraindications exist."""
        return any(
            med.status == MedicationStatus.CONTRAINDICATED
            for med in self.current_medications
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_medications": [m.to_dict() for m in self.current_medications],
            "recommended_medications": [
                m.to_dict() for m in self.recommended_medications
            ],
            "interactions": self.interactions,
            "general_advice": self.general_advice,
        }
