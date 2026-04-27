"""
DSPy Signatures for health prescriptions.

Defines signatures for:
- Diet prescriptions (饮食处方)
- Exercise prescriptions (运动处方)
- Sleep prescriptions (睡眠处方)
- Medication prescriptions (用药处方)
"""

from typing import Optional
from dataclasses import dataclass, field

from .base import (
    BaseSignature,
    InputField,
    OutputField,
    FieldType,
)


class DietPrescriptionSignature(BaseSignature):
    """
    Signature for diet prescription (饮食处方).

    Generates personalized diet recommendations based on health status.
    """

    system_prompt = """你是一位专业的营养师，负责制定个性化饮食处方。

请根据用户的健康状况、饮食习惯和目标，制定详细的饮食方案，包括：
1. 每日热量需求计算
2. 营养素配比建议
3. 食物选择指导
4. 饮食禁忌和注意事项
5. 具体的膳食计划示例

处方应科学、实用、可执行。
"""

    input_fields = [
        InputField(
            name="health_status",
            description="健康状况评估结果",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="patient_data",
            description="患者基本数据（年龄、性别、身高体重等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="dietary_preferences",
            description="饮食偏好和限制",
            field_type=FieldType.JSON,
            required=False,
        ),
        InputField(
            name="health_goals",
            description="健康目标（减重、控糖等）",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="diet_prescription",
            description="饮食处方",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请制定饮食处方：

健康状况：
{health_status}

患者信息：
{patient_data}

{% if dietary_preferences %}
饮食偏好：
{dietary_preferences}
{% endif %}

{% if health_goals %}
健康目标：
{health_goals}
{% endif %}

请提供详细的饮食处方，包括热量控制、营养配比、食物选择和膳食计划。"""


class ExercisePrescriptionSignature(BaseSignature):
    """
    Signature for exercise prescription (运动处方).

    Generates personalized exercise recommendations.
    """

    system_prompt = """你是一位专业的运动康复专家，负责制定个性化运动处方。

请根据用户的健康状况、体能水平和运动习惯，制定科学的运动方案，包括：
1. 运动类型选择（有氧、力量、柔韧性等）
2. 运动强度确定（心率区间、主观疲劳度等）
3. 运动频率和时长
4. 运动进度安排
5. 注意事项和安全建议

处方应遵循FITT（频率、强度、时间、类型）原则。
"""

    input_fields = [
        InputField(
            name="health_status",
            description="健康状况评估结果",
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
            name="fitness_level",
            description="当前体能水平",
            field_type=FieldType.JSON,
            required=False,
        ),
        InputField(
            name="exercise_preferences",
            description="运动偏好",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="exercise_prescription",
            description="运动处方",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请制定运动处方：

健康状况：
{health_status}

患者信息：
{patient_data}

{% if fitness_level %}
体能水平：
{fitness_level}
{% endif %}

{% if exercise_preferences %}
运动偏好：
{exercise_preferences}
{% endif %}

请提供详细的运动处方，包括运动类型、强度、频率、时长和注意事项。"""


class SleepPrescriptionSignature(BaseSignature):
    """
    Signature for sleep prescription (睡眠处方).

    Generates personalized sleep improvement recommendations.
    """

    system_prompt = """你是一位专业的睡眠医学专家，负责制定个性化睡眠改善处方。

请根据用户的睡眠状况和健康状况，制定睡眠改善方案，包括：
1. 目标睡眠时长
2. 睡眠时间安排
3. 睡眠环境建议
4. 睡前放松技巧
5. 睡眠卫生指导
6. 必要时的进一步检查建议

处方应基于循证医学，注重实用性。
"""

    input_fields = [
        InputField(
            name="health_status",
            description="健康状况评估结果",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="sleep_data",
            description="睡眠数据（时长、质量、入睡时间等）",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="sleep_issues",
            description="睡眠问题描述",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="sleep_prescription",
            description="睡眠处方",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请制定睡眠处方：

健康状况：
{health_status}

睡眠数据：
{sleep_data}

{% if sleep_issues %}
睡眠问题：
{sleep_issues}
{% endif %}

请提供详细的睡眠改善处方，包括睡眠时长建议、作息安排和睡眠卫生指导。"""


class MedicationPrescriptionSignature(BaseSignature):
    """
    Signature for medication prescription (用药处方).

    Generates medication recommendations based on health assessment.
    Note: This is for suggestion only, actual prescriptions require medical review.
    """

    system_prompt = """你是一位资深临床药师，负责提供用药建议和指导。

请根据用户的健康状况和当前用药，提供：
1. 当前用药评估
2. 用药方案优化建议
3. 药物相互作用警示
4. 服药时间指导
5. 不良反应监测要点
6. 必要时的药物调整建议

⚠️ 重要提示：本建议仅供参考，实际用药方案需由执业医师审核决定。
"""

    input_fields = [
        InputField(
            name="health_status",
            description="健康状况评估结果",
            field_type=FieldType.JSON,
            required=True,
        ),
        InputField(
            name="current_medications",
            description="当前用药列表",
            field_type=FieldType.ARRAY,
            required=False,
        ),
        InputField(
            name="allergies",
            description="药物过敏史",
            field_type=FieldType.JSON,
            required=False,
        ),
        InputField(
            name="medication_check_result",
            description="合理用药检查结果（来自MCP）",
            field_type=FieldType.JSON,
            required=False,
        ),
    ]

    output_fields = [
        OutputField(
            name="medication_prescription",
            description="用药处方建议",
            field_type=FieldType.JSON,
        ),
    ]

    prompt_template = """请提供用药建议：

健康状况：
{health_status}

{% if current_medications %}
当前用药：
{current_medications}
{% endif %}

{% if allergies %}
过敏史：
{allergies}
{% endif %}

{% if medication_check_result %}
用药检查结果：
{medication_check_result}
{% endif %}

请提供用药建议，包括用药评估、方案优化、注意事项和警示。

⚠️ 本建议仅供参考，实际用药需由医师决定。"""
