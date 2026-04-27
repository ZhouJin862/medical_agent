"""
DSPy Signatures for 四高一重 (Four Highs One Weight) health assessments.

Defines signatures for:
- General health assessment
- Risk prediction
- Specific disease assessments (hypertension, diabetes, dyslipidemia, gout, obesity)
"""

from typing import Optional, Any
from dataclasses import dataclass, field

from .base import (
    BaseSignature,
    InputField,
    OutputField,
    FieldType,
)


class HealthAssessmentSignature(BaseSignature):
    """
    Signature for general health assessment.

    Evaluates overall health status based on vital signs and patient data.
    """

    system_prompt = """你是一位专业的健康管理师，负责评估用户的整体健康状况。

请根据提供的用户体征数据和健康信息，进行全面、客观的健康评估。
评估结果应包含：
1. 整体健康状况评级
2. 各项指标的分析
3. 异常指标说明
4. 健康建议

可用工具：
- get_health_data: 使用party_id（客户号）从平安健康档案系统获取患者健康数据

注意：如果用户提供了客户号(partyId/客户号)，应该优先使用get_health_data工具获取完整的健康档案数据。
"""

    input_fields = [
        InputField(
            name="patient_data",
            description="患者基本数据（年龄、性别、身高等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="party_id",
            description="平安健康档案系统的客户号(客户号/partyId)，如果有提供可用于获取完整健康数据",
            field_type=FieldType.STRING,
            required=False,
        ),
        InputField(
            name="vital_signs",
            description="生命体征数据（血压、血糖、血脂、尿酸、BMI等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="medical_history",
            description="既往病史和家族史",
            field_type=FieldType.JSON,
            required=False,
        ),
        InputField(
            name="user_query",
            description="用户的健康咨询问题",
            field_type=FieldType.STRING,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="health_status",
            description="整体健康状况评估结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请根据以下信息进行健康评估：

患者信息：
{patient_data}

{% if party_id %}
客户号(partyId): {party_id}
已使用get_health_data工具从平安健康档案获取完整数据
{% endif %}

生命体征：
{vital_signs}

{% if medical_history %}
病史信息：
{medical_history}
{% endif %}

{% if user_query %}
用户咨询：
{user_query}
{% endif %}

请提供详细的健康评估报告。"""


class RiskPredictionSignature(BaseSignature):
    """
    Signature for risk prediction.

    Predicts risks for various health outcomes based on current health data.
    """

    system_prompt = """你是一位专业的风险评估专家，负责预测用户的健康风险。

基于用户当前的体征数据和病史，预测：
1. 患病风险率（各种疾病的发生概率）
2. 疾病恶化风险率
3. 并发症风险
4. 失能风险
5. 预期医疗成本

预测应基于医学指南和循证医学证据。

可用工具：
- get_health_data: 使用party_id（客户号）从平安健康档案系统获取患者完整健康数据，用于更准确的风险预测

注意：如果用户提供了客户号(partyId/客户号)，应该优先使用get_health_data工具获取完整的历史数据。
"""

    input_fields = [
        InputField(
            name="patient_data",
            description="患者基本数据",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="party_id",
            description="平安健康档案系统的客户号(客户号/partyId)，可用于获取完整历史数据进行风险预测",
            field_type=FieldType.STRING,
            required=False,
        ),
        InputField(
            name="vital_signs",
            description="生命体征数据",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="medical_history",
            description="既往病史",
            field_type=FieldType.JSON,
            required=False,
        ),
        InputField(
            name="target_diseases",
            description="需要预测风险的疾病列表",
            field_type=FieldType.ARRAY,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="risk_predictions",
            description="各类风险的预测结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请进行健康风险预测：

患者信息：
{patient_data}

{% if party_id %}
客户号(partyId): {party_id}
已使用get_health_data工具从平安健康档案获取完整历史数据
{% endif %}

生命体征：
{vital_signs}

{% if medical_history %}
病史：
{medical_history}
{% endif %}

{% if target_diseases %}
重点预测疾病：
{target_diseases}
{% endif %}

请提供详细的风险预测报告，包括各项风险的概率和建议。"""


class HypertensionAssessmentSignature(BaseSignature):
    """Signature for hypertension (高血压) assessment."""

    system_prompt = """你是一位心血管疾病专家，专门负责高血压的评估和管理。

请根据患者的血压数据和相关指标，评估：
1. 高血压分级（正常、正常高值、1级、2级、3级）
2. 心血管风险分层
3. 靶器官损害评估
4. 降压目标建议

参考《中国高血压防治指南》。
"""

    input_fields = [
        InputField(
            name="blood_pressure",
            description="血压数据（收缩压、舒张压）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="patient_data",
            description="患者基本数据（年龄、性别等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="risk_factors",
            description="危险因素（吸烟、肥胖、家族史等）",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="hypertension_assessment",
            description="高血压评估结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请进行高血压评估：

血压数据：
{blood_pressure}

患者信息：
{patient_data}

{% if risk_factors %}
危险因素：
{risk_factors}
{% endif %}

请提供高血压分级、风险评估和管理建议。"""


class DiabetesAssessmentSignature(BaseSignature):
    """Signature for diabetes (糖尿病) assessment."""

    system_prompt = """你是一位内分泌科专家，专门负责糖尿病的评估和管理。

请根据患者的血糖数据和相关指标，评估：
1. 糖尿病类型判断
2. 血糖控制状态评估
3. 并发症风险筛查
4. 降糖目标建议

参考《中国2型糖尿病防治指南》。
"""

    input_fields = [
        InputField(
            name="blood_glucose",
            description="血糖数据（空腹血糖、餐后血糖、糖化血红蛋白等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="patient_data",
            description="患者基本数据",
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
            name="diabetes_assessment",
            description="糖尿病评估结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请进行糖尿病评估：

血糖数据：
{blood_glucose}

患者信息：
{patient_data}

{% if medical_history %}
病史：
{medical_history}
{% endif %}

请提供糖尿病评估、风险评估和管理建议。"""


class DyslipidemiaAssessmentSignature(BaseSignature):
    """Signature for dyslipidemia (血脂异常) assessment."""

    system_prompt = """你是一位心血管代谢专家，专门负责血脂异常的评估和管理。

请根据患者的血脂数据，评估：
1. 血脂异常分型
2. 动脉粥样硬化性心血管病（ASCVD）风险
3. 降脂目标建议
4. 生活方式干预建议

参考《中国成人血脂异常防治指南》。
"""

    input_fields = [
        InputField(
            name="lipid_profile",
            description="血脂数据（总胆固醇、甘油三酯、LDL-C、HDL-C等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="patient_data",
            description="患者基本数据",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="risk_factors",
            description="其他危险因素",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="dyslipidemia_assessment",
            description="血脂评估结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请进行血脂评估：

血脂数据：
{lipid_profile}

患者信息：
{patient_data}

{% if risk_factors %}
危险因素：
{risk_factors}
{% endif %}

请提供血脂评估、风险评估和管理建议。"""


class GoutAssessmentSignature(BaseSignature):
    """Signature for gout/hyperuricemia (痛风/高尿酸血症) assessment."""

    system_prompt = """你是一位风湿免疫科专家，专门负责痛风和高尿酸血症的评估和管理。

请根据患者的尿酸数据和相关症状，评估：
1. 高尿酸血症分级
2. 痛风发作风险评估
3. 尿酸性肾病风险
4. 降尿酸目标建议

参考《中国高尿酸血症与痛风诊疗指南》。
"""

    input_fields = [
        InputField(
            name="uric_acid",
            description="尿酸数据",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="patient_data",
            description="患者基本数据",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="symptoms",
            description="症状信息（关节疼痛等）",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="gout_assessment",
            description="痛风/高尿酸评估结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请进行痛风/高尿酸血症评估：

尿酸数据：
{uric_acid}

患者信息：
{patient_data}

{% if symptoms %}
症状：
{symptoms}
{% endif %}

请提供高尿酸血症评估、痛风风险和管理建议。"""


class ObesityAssessmentSignature(BaseSignature):
    """Signature for obesity (肥胖) assessment."""

    system_prompt = """你是一位内分泌代谢科专家，专门负责肥胖的评估和管理。

请根据患者的体重数据，评估：
1. 肥胖程度分级（BMI分类）
2. 体脂分布评估（腰围、腰臀比）
3. 肥胖相关并发症风险
4. 体重管理目标建议

参考《中国成人肥胖症防治专家共识》。
"""

    input_fields = [
        InputField(
            name="anthropometrics",
            description="人体测量数据（BMI、腰围、体脂率等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="patient_data",
            description="患者基本数据",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="comorbidities",
            description="合并症信息",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="obesity_assessment",
            description="肥胖评估结果",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请进行肥胖评估：

人体测量数据：
{anthropometrics}

患者信息：
{patient_data}

{% if comorbidities %}
合并症：
{comorbidities}
{% endif %}

请提供肥胖评估、风险分层和管理建议。"""
