"""
Prescription Skills - Health prescription generation.

Skills for generating:
- Diet prescriptions
- Exercise prescriptions
- Sleep prescriptions
"""

from ..base_skill import BaseSkill, SkillConfig
from ..signatures.prescription import (
    DietPrescriptionSignature,
    ExercisePrescriptionSignature,
    SleepPrescriptionSignature,
)
from ...llm import ModelProvider


class DietPrescriptionSkill(BaseSkill):
    """
    Diet prescription skill.

    Generates personalized dietary recommendations.
    """

    def __init__(self, llm=None):
        """Initialize the diet prescription skill."""
        config = SkillConfig(
            name="diet_prescription",
            description="饮食处方 - 生成个性化饮食建议",
            signature_class=DietPrescriptionSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["饮食", "吃饭", "营养", "膳食", "diet"],
        )
        super().__init__(config, llm)


class ExercisePrescriptionSkill(BaseSkill):
    """
    Exercise prescription skill.

    Generates personalized exercise recommendations.
    """

    def __init__(self, llm=None):
        """Initialize the exercise prescription skill."""
        config = SkillConfig(
            name="exercise_prescription",
            description="运动处方 - 生成个性化运动建议",
            signature_class=ExercisePrescriptionSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["运动", "锻炼", "健身", "活动", "exercise"],
        )
        super().__init__(config, llm)


class SleepPrescriptionSkill(BaseSkill):
    """
    Sleep prescription skill.

    Generates sleep improvement recommendations.
    """

    def __init__(self, llm=None):
        """Initialize the sleep prescription skill."""
        config = SkillConfig(
            name="sleep_prescription",
            description="睡眠处方 - 生成睡眠改善建议",
            signature_class=SleepPrescriptionSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["睡眠", "休息", "失眠", "sleep"],
        )
        super().__init__(config, llm)
