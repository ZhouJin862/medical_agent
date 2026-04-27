"""
General Health Assessment Skills.

General-purpose skills for health assessment and risk prediction.
"""

from ..base_skill import BaseSkill, SkillConfig
from ..signatures.four_highs import (
    HealthAssessmentSignature,
    RiskPredictionSignature,
)
from ...llm import ModelProvider


class HealthAssessmentSkill(BaseSkill):
    """
    General health assessment skill.

    Evaluates overall health status based on vital signs and patient data.
    """

    def __init__(self, llm=None):
        """Initialize the health assessment skill."""
        config = SkillConfig(
            name="health_assessment",
            description="通用健康评估 - 评估整体健康状况",
            signature_class=HealthAssessmentSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["评估", "健康", "检查", "状况", "analysis"],
        )
        super().__init__(config, llm)


class RiskPredictionSkill(BaseSkill):
    """
    Risk prediction skill.

    Predicts health risks based on current vital signs and history.
    """

    def __init__(self, llm=None):
        """Initialize the risk prediction skill."""
        config = SkillConfig(
            name="risk_prediction",
            description="风险预测 - 预测疾病风险和健康趋势",
            signature_class=RiskPredictionSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["风险", "预测", "概率", "可能性", "risk"],
        )
        super().__init__(config, llm)


class HealthProfileSkill(BaseSkill):
    """
    Health profile skill.

    Creates a comprehensive health profile from patient data.
    """

    def __init__(self, llm=None):
        """Initialize the health profile skill."""
        from ..signatures.base import BaseSignature, InputField, OutputField, FieldType

        # Create a custom signature for health profile
        class HealthProfileSignature(BaseSignature):
            system_prompt = """你是一位健康管理专家，负责生成患者的健康画像。

健康画像应包含：
1. 整体健康状况评级
2. 各项指标分析
3. 健康风险识别
4. 改善建议
5. 长期健康趋势预测
"""

            input_fields = [
                InputField(
                    name="patient_data",
                    description="患者基本数据",
                    field_type=FieldType.JSON,
                    required=True,
                ),
                InputField(
                    name="vital_signs",
                    description="生命体征数据",
                    field_type=FieldType.JSON,
                    required=True,
                ),
                InputField(
                    name="medical_history",
                    description="病史信息",
                    field_type=FieldType.JSON,
                    required=False,
                ),
            ]

            output_fields = [
                OutputField(
                    name="health_profile",
                    description="健康画像",
                    field_type=FieldType.JSON,
                ),
            ]

            prompt_template = """请为患者生成健康画像：

患者信息：
{patient_data}

生命体征：
{vital_signs}

{% if medical_history %}
病史：
{medical_history}
{% endif %}

请生成完整的健康画像报告。"""

        config = SkillConfig(
            name="health_profile",
            description="健康画像 - 生成综合健康画像",
            signature_class=HealthProfileSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["画像", "profile", "综合", "分析"],
        )
        super().__init__(config, llm)
