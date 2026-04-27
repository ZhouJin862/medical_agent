"""
MCP Tool Skills - Skills that call MCP servers.

These skills integrate with external Java services through MCP:
- Triage guidance
- Medication checking
- Service recommendations
"""

from ..base_skill import BaseSkill, SkillConfig
from ...llm import ModelProvider
from ..signatures.base import BaseSignature, InputField, OutputField, FieldType


class TriageGuidanceSkill(BaseSkill):
    """
    Triage guidance skill.

    Uses MCP to get hospital, department, and doctor recommendations.
    """

    def __init__(self, llm=None):
        """Initialize the triage guidance skill."""

        class TriageGuidanceSignature(BaseSignature):
            system_prompt = """你是分诊导医助手，负责为患者推荐合适的就医选择。

根据患者的健康状况，提供：
1. 就医紧急程度建议
2. 推荐医院
3. 推荐科室
4. 推荐医生（如有）
"""

            input_fields = [
                InputField(
                    name="health_status",
                    description="健康状况评估结果",
                    field_type=FieldType.JSON,
                    required=True,
                ),
                InputField(
                    name="patient_location",
                    description="患者位置（用于计算距离）",
                    field_type=FieldType.JSON,
                    required=False,
                ),
                InputField(
                    name="preferred_hospitals",
                    description="偏好医院列表",
                    field_type=FieldType.ARRAY,
                    required=False,
                ),
            ]

            output_fields = [
                OutputField(
                    name="triage_recommendation",
                    description="分诊推荐结果",
                    field_type=FieldType.JSON,
                ),
            ]

            prompt_template = """请提供分诊导医建议：

健康状况：
{health_status}

{% if patient_location %}
患者位置：
{patient_location}
{% endif %}

{% if preferred_hospitals %}
偏好医院：
{preferred_hospitals}
{% endif %}

请提供详细的分诊建议。"""

        config = SkillConfig(
            name="triage_guidance",
            description="分诊导医 - 推荐医院、科室、医生",
            signature_class=TriageGuidanceSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["就医", "挂号", "医院", "科室", "医生", "分诊"],
            knowledge_base_ids=["triage_knowledge"],
        )
        super().__init__(config, llm)

    async def execute(self, **kwargs):
        """
        Execute with MCP integration.

        Args:
            **kwargs: Input parameters

        Returns:
            SkillResult with MCP data
        """
        from ...mcp import MCPClientFactory

        # Call MCP for triage data
        try:
            triage_client = MCPClientFactory.get_client("triage_server")

            # Get hospitals
            hospitals = await triage_client.call_tool(
                "get_hospitals",
                kwargs.get("patient_location", {})
            )

            # Get departments based on health status
            health_status = kwargs.get("health_status", {})
            departments = await triage_client.call_tool(
                "get_departments",
                {"conditions": health_status.get("conditions", [])}
            )

            # Get doctors if preferred hospitals specified
            doctors = []
            if kwargs.get("preferred_hospitals"):
                doctors = await triage_client.call_tool(
                    "get_doctors",
                    {
                        "hospital_ids": kwargs["preferred_hospitals"],
                        "specialty": health_status.get("recommended_specialty")
                    }
                )

            # Enhance result with MCP data
            mcp_data = {
                "hospitals": hospitals,
                "departments": departments,
                "doctors": doctors,
            }

            # Add to kwargs for base execution
            kwargs["mcp_data"] = mcp_data

        except Exception as e:
            # Fall back to base execution without MCP data
            pass

        return await super().execute(**kwargs)


class MedicationCheckSkill(BaseSkill):
    """
    Medication checking skill.

    Uses MCP to validate medications and check for interactions.
    """

    def __init__(self, llm=None):
        """Initialize the medication checking skill."""

        class MedicationCheckSignature(BaseSignature):
            system_prompt = """你是合理用药助手，负责提供用药建议和检查。

请检查：
1. 当前用药是否合理
2. 是否存在药物相互作用
3. 是否存在禁忌症
4. 给出用药建议
"""

            input_fields = [
                InputField(
                    name="current_medications",
                    description="当前用药列表",
                    field_type=FieldType.ARRAY,
                    required=True,
                ),
                InputField(
                    name="health_status",
                    description="健康状况",
                    field_type=FieldType.JSON,
                    required=False,
                ),
                InputField(
                    name="allergies",
                    description="药物过敏史",
                    field_type=FieldType.JSON,
                    required=False,
                ),
            ]

            output_fields = [
                OutputField(
                    name="medication_recommendation",
                    description="用药建议结果",
                    field_type=FieldType.JSON,
                ),
            ]

            prompt_template = """请进行合理用药检查：

当前用药：
{current_medications}

{% if health_status %}
健康状况：
{health_status}
{% endif %}

{% if allergies %}
过敏史：
{allergies}
{% endif %}

请提供用药建议和注意事项。"""

        config = SkillConfig(
            name="medication_check",
            description="合理用药 - 检查用药合理性、相互作用、禁忌",
            signature_class=MedicationCheckSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["用药", "药物", "药品", "medication"],
            knowledge_base_ids=["medication_knowledge"],
        )
        super().__init__(config, llm)

    async def execute(self, **kwargs):
        """Execute with MCP integration."""
        from ...mcp import MCPClientFactory

        # Call MCP for medication checking
        try:
            medication_client = MCPClientFactory.get_client("medication_server")

            # Check medication interactions
            check_result = await medication_client.call_tool(
                "check_medication",
                {
                    "medications": kwargs.get("current_medications", []),
                    "allergies": kwargs.get("allergies", {}),
                }
            )

            # Get drug recommendations
            recommendations = await medication_client.call_tool(
                "recommend_drugs",
                {
                    "health_status": kwargs.get("health_status", {}),
                }
            )

            # Enhance result with MCP data
            kwargs["mcp_check_result"] = check_result
            kwargs["mcp_recommendations"] = recommendations

        except Exception as e:
            # Fall back to base execution
            pass

        return await super().execute(**kwargs)


class ServiceRecommendSkill(BaseSkill):
    """
    Service recommendation skill.

    Uses MCP to recommend insurance products and health services.
    """

    def __init__(self, llm=None):
        """Initialize the service recommendation skill."""

        class ServiceRecommendSignature(BaseSignature):
            system_prompt = """你是健康服务推荐助手，负责推荐合适的保险产品和健康服务。

根据患者的健康状况和需求，推荐：
1. 适合的保险产品
2. 健康管理服务
3. 康养服务
"""

            input_fields = [
                InputField(
                    name="health_status",
                    description="健康状况",
                    field_type=FieldType.JSON,
                    required=True,
                ),
                InputField(
                    name="user_preferences",
                    description="用户偏好",
                    field_type=FieldType.JSON,
                    required=False,
                ),
            ]

            output_fields = [
                OutputField(
                    name="service_recommendation",
                    description="服务推荐结果",
                    field_type=FieldType.JSON,
                ),
            ]

            prompt_template = """请推荐健康服务和保险产品：

健康状况：
{health_status}

{% if user_preferences %}
用户偏好：
{user_preferences}
{% endif %}

请提供个性化的服务和产品推荐。"""

        config = SkillConfig(
            name="service_recommend",
            description="服务推荐 - 推荐保险产品和健康服务",
            signature_class=ServiceRecommendSignature,
            model_provider=ModelProvider.ANTHROPIC,
            enabled=True,
            intent_keywords=["保险", "服务", "推荐", "产品"],
            knowledge_base_ids=["service_knowledge"],
        )
        super().__init__(config, llm)

    async def execute(self, **kwargs):
        """Execute with MCP integration."""
        from ...mcp import MCPClientFactory

        # Call MCP for service recommendations
        try:
            service_client = MCPClientFactory.get_client("service_server")

            # Get insurance recommendations
            insurance = await service_client.call_tool(
                "recommend_insurance",
                {
                    "health_status": kwargs.get("health_status", {}),
                }
            )

            # Get health service recommendations
            services = await service_client.call_tool(
                "recommend_health_services",
                {
                    "health_status": kwargs.get("health_status", {}),
                    "preferences": kwargs.get("user_preferences", {}),
                }
            )

            # Enhance result with MCP data
            kwargs["mcp_insurance"] = insurance
            kwargs["mcp_services"] = services

        except Exception as e:
            # Fall back to base execution
            pass

        return await super().execute(**kwargs)
