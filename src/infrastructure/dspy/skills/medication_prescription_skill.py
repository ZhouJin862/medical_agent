"""
Medication Prescription Skill - Medication prescription recommendations.

This skill generates medication prescription recommendations based on
health assessment and medication check results.
"""

from ..base_skill import BaseSkill, SkillConfig
from ..signatures.prescription import MedicationPrescriptionSignature
from ...llm import ModelProvider


class MedicationPrescriptionSkill(BaseSkill):
    """
    Medication prescription skill.

    Generates medication recommendations based on health status
    and medication check results.
    """

    def __init__(self, llm=None):
        """Initialize the medication prescription skill."""
        config = SkillConfig(
            name="medication_prescription",
            description="用药处方 - 生成用药建议和处方推荐",
            signature_class=MedicationPrescriptionSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["用药", "药品", "处方", "药物治疗"],
        )
        super().__init__(config, llm)
