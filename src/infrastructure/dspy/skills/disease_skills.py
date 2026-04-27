"""
Disease-Specific Skills for 四高一重 (Four Highs One Weight).

Skills for:
- Hypertension (高血压)
- Diabetes (糖尿病)
- Dyslipidemia (血脂异常)
- Gout/Hyperuricemia (痛风/高尿酸血症)
- Obesity (肥胖)
- Metabolic Syndrome (代谢综合征)
"""

from ..base_skill import BaseSkill, SkillConfig
from ..signatures.four_highs import (
    HypertensionAssessmentSignature,
    DiabetesAssessmentSignature,
    DyslipidemiaAssessmentSignature,
    GoutAssessmentSignature,
    ObesityAssessmentSignature,
)
from ...llm import ModelProvider
from ..signatures.base import BaseSignature, InputField, OutputField, FieldType


class HypertensionSkill(BaseSkill):
    """
    Hypertension assessment skill.

    Evaluates blood pressure data and cardiovascular risk.
    """

    def __init__(self, llm=None):
        """Initialize the hypertension assessment skill."""
        config = SkillConfig(
            name="hypertension_assessment",
            description="高血压评估 - 评估血压状况和心血管风险",
            signature_class=HypertensionAssessmentSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["血压", "高血压", "收缩压", "舒张压", "hypertension"],
        )
        super().__init__(config, llm)


class DiabetesSkill(BaseSkill):
    """
    Diabetes assessment skill.

    Evaluates blood glucose data and diabetes risk.
    """

    def __init__(self, llm=None):
        """Initialize the diabetes assessment skill."""
        config = SkillConfig(
            name="diabetes_assessment",
            description="糖尿病评估 - 评估血糖状况和糖尿病风险",
            signature_class=DiabetesAssessmentSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["血糖", "糖尿病", "糖化血红蛋白", "空腹血糖", "diabetes"],
        )
        super().__init__(config, llm)


class DyslipidemiaSkill(BaseSkill):
    """
    Dyslipidemia assessment skill.

    Evaluates blood lipid data and cardiovascular risk.
    """

    def __init__(self, llm=None):
        """Initialize the dyslipidemia assessment skill."""
        config = SkillConfig(
            name="dyslipidemia_assessment",
            description="血脂评估 - 评估血脂状况和心血管风险",
            signature_class=DyslipidemiaAssessmentSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["血脂", "胆固醇", "甘油三酯", "低密度脂蛋白", "血脂异常"],
        )
        super().__init__(config, llm)


class GoutSkill(BaseSkill):
    """
    Gout/Hyperuricemia assessment skill.

    Evaluates uric acid data and gout risk.
    """

    def __init__(self, llm=None):
        """Initialize the gout assessment skill."""
        config = SkillConfig(
            name="gout_assessment",
            description="痛风/高尿酸血症评估 - 评估尿酸状况和痛风风险",
            signature_class=GoutAssessmentSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["尿酸", "痛风", "高尿酸", "关节疼痛", "gout"],
        )
        super().__init__(config, llm)


class ObesitySkill(BaseSkill):
    """
    Obesity assessment skill.

    Evaluates BMI and body composition data.
    """

    def __init__(self, llm=None):
        """Initialize the obesity assessment skill."""
        config = SkillConfig(
            name="obesity_assessment",
            description="肥胖评估 - 评估体重状况和肥胖相关风险",
            signature_class=ObesityAssessmentSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["体重", "BMI", "肥胖", "体脂", "腰围", "obesity"],
        )
        super().__init__(config, llm)


class MetabolicSyndromeSkill(BaseSkill):
    """
    Metabolic syndrome assessment skill.

    Evaluates multiple risk factors for metabolic syndrome.
    """

    def __init__(self, llm=None):
        """Initialize the metabolic syndrome assessment skill."""

        # Create custom signature for metabolic syndrome
        class MetabolicSyndromeSignature(BaseSignature):
            system_prompt = """你是一位内分泌代谢科专家，专门负责代谢综合征的评估。

代谢综合征诊断标准（满足以下3项或以上）：
1. 腹型肥胖：男性腰围≥90cm，女性腰围≥85cm
2. 高甘油三酯：TG ≥ 1.7 mmol/L
3. 低HDL-C：男性 < 1.0 mmol/L，女性 < 1.3 mmol/L
4. 高血压：SBP ≥ 130 或 DBP ≥ 85 mmHg
5. 高血糖：FPG ≥ 6.1 mmol/L 或已确诊糖尿病

请根据患者数据评估：
1. 是否符合代谢综合征诊断
2. 符合几项诊断标准
3. 心血管疾病风险评估
4. 生活方式干预建议
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
                    name="blood_pressure",
                    description="血压数据",
                    field_type=FieldType.JSON,
                    required=True,
                ),
                InputField(
                    name="lipid_profile",
                    description="血脂数据",
                    field_type=FieldType.JSON,
                    required=True,
                ),
                InputField(
                    name="blood_glucose",
                    description="血糖数据",
                    field_type=FieldType.JSON,
                    required=True,
                ),
            ]

            output_fields = [
                OutputField(
                    name="metabolic_syndrome_assessment",
                    description="代谢综合征评估结果",
                    field_type=FieldType.JSON,
                ),
            ]

            prompt_template = """请进行代谢综合征评估：

患者信息：
{patient_data}

血压：
{blood_pressure}

血脂：
{lipid_profile}

血糖：
{blood_glucose}

其他体征：
{vital_signs}

请评估是否患有代谢综合征及相关风险。"""

        config = SkillConfig(
            name="metabolic_syndrome_assessment",
            description="代谢综合征评估 - 评估代谢综合征及相关风险",
            signature_class=MetabolicSyndromeSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["代谢", "代谢综合征", "综合征", "综合风险"],
        )
        super().__init__(config, llm)
