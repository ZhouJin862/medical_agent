"""
Integration tests for MCP Tool Skills.

Tests for:
- TriageGuidanceSkill (分诊导医)
- MedicationCheckSkill (合理用药)
- ServiceRecommendSkill (服务推荐)

These tests verify the integration with MCP servers and the
skill execution with MCP data enhancement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.dspy.skills.mcp_tool_skills import (
    TriageGuidanceSkill,
    MedicationCheckSkill,
    ServiceRecommendSkill,
)
from src.infrastructure.dspy.base_skill import SkillResult


# ===== Fixtures =====


@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    llm = MagicMock()
    llm.supports_structured_output.return_value = True
    llm.generate_structured = AsyncMock()
    llm.generate = AsyncMock()
    return llm


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    response = MagicMock()
    response.content = '{"recommendation": "test recommendation"}'
    response.model = "claude-3-5-sonnet"
    response.tokens_used = 100
    return response


@pytest.fixture
def sample_health_status():
    """Sample health status data."""
    return {
        "conditions": ["hypertension", "diabetes"],
        "symptoms": ["headache", "dizziness"],
        "severity": "moderate",
    }


@pytest.fixture
def sample_patient_location():
    """Sample patient location data."""
    return {
        "city": "Beijing",
        "district": "Chaoyang",
        "coordinates": {"lat": 39.9, "lng": 116.4},
    }


@pytest.fixture
def sample_current_medications():
    """Sample current medications."""
    return [
        {"name": "Amlodipine", "dosage": "5mg", "frequency": "once daily"},
        {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
    ]


@pytest.fixture
def sample_user_preferences():
    """Sample user preferences for services."""
    return {
        "budget": "medium",
        "insurance_interest": True,
        "service_interest": ["health_management"],
    }


# ===== TriageGuidanceSkill Tests =====


@pytest.mark.asyncio
class TestTriageGuidanceSkill:
    """Tests for TriageGuidanceSkill."""

    def test_initialization(self):
        """Test skill initialization."""
        skill = TriageGuidanceSkill()

        assert skill.config.name == "triage_guidance"
        assert skill.config.enabled is True
        assert "就医" in skill.config.intent_keywords
        assert "医院" in skill.config.intent_keywords

    @pytest.mark.asyncio
    async def test_execute_with_mcp_data(
        self, mock_llm, mock_llm_response, sample_health_status, sample_patient_location
    ):
        """Test execution with MCP integration."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = TriageGuidanceSkill(llm=mock_llm)

        # Mock MCP client
        mock_hospitals = {
            "hospitals": [
                {"name": "北京协和医院", "level": "tertiary", "distance_km": 5.2}
            ]
        }
        mock_departments = {
            "departments": [
                {"name": "心血管内科", "priority": "high"}
            ]
        }

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_triage_client = AsyncMock()
            mock_triage_client.call_tool = AsyncMock(
                side_effect=[mock_hospitals, mock_departments]
            )
            mock_factory.get_client.return_value = mock_triage_client

            result = await skill.execute(
                health_status=sample_health_status,
                patient_location=sample_patient_location,
            )

        assert result.success is True
        mock_triage_client.call_tool.assert_called()

    @pytest.mark.asyncio
    async def test_execute_without_mcp_fallback(
        self, mock_llm, mock_llm_response, sample_health_status
    ):
        """Test execution falls back gracefully when MCP fails."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = TriageGuidanceSkill(llm=mock_llm)

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_factory.get_client.side_effect = Exception("MCP unavailable")

            result = await skill.execute(health_status=sample_health_status)

        # Should still succeed using base execution
        assert result.success is True

    @pytest.mark.asyncio
    async def test_can_handle_intent_keywords(self):
        """Test can_handle with intent keywords."""
        skill = TriageGuidanceSkill()

        assert skill.can_handle("我想去医院挂号")
        assert skill.can_handle("推荐哪个科室")
        assert skill.can_handle("找个心血管医生")
        assert not skill.can_handle("饮食建议")

    async def test_can_handle_at_syntax(self):
        """Test can_handle with @skill_name syntax."""
        skill = TriageGuidanceSkill()

        assert skill.can_handle("@triage_guidance 请帮助分诊")
        assert not skill.can_handle("@diet_prescription 帮助")


# ===== MedicationCheckSkill Tests =====


class TestMedicationCheckSkill:
    """Tests for MedicationCheckSkill."""

    def test_initialization(self):
        """Test skill initialization."""
        skill = MedicationCheckSkill()

        assert skill.config.name == "medication_check"
        assert skill.config.enabled is True
        assert "用药" in skill.config.intent_keywords
        assert "药物" in skill.config.intent_keywords

    @pytest.mark.asyncio
    async def test_execute_with_mcp_data(
        self, mock_llm, mock_llm_response, sample_current_medications, sample_health_status
    ):
        """Test execution with MCP integration."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = MedicationCheckSkill(llm=mock_llm)

        # Mock MCP client
        mock_check_result = {
            "interactions": [],
            "warnings": [],
            "contraindications": [],
        }
        mock_recommendations = {
            "first_line": ["Amlodipine"],
            "alternatives": [],
        }

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_medication_client = AsyncMock()
            mock_medication_client.call_tool = AsyncMock(
                side_effect=[mock_check_result, mock_recommendations]
            )
            mock_factory.get_client.return_value = mock_medication_client

            result = await skill.execute(
                current_medications=sample_current_medications,
                health_status=sample_health_status,
            )

        assert result.success is True
        assert mock_medication_client.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_allergies(
        self, mock_llm, mock_llm_response, sample_current_medications
    ):
        """Test execution with allergy information."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = MedicationCheckSkill(llm=mock_llm)

        allergies = {"drug_allergies": ["Penicillin"], "food_allergies": ["Peanuts"]}

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(
                return_value={"interactions": [], "warnings": []}
            )
            mock_factory.get_client.return_value = mock_client

            result = await skill.execute(
                current_medications=sample_current_medications,
                allergies=allergies,
            )

        assert result.success is True
        # Verify allergies were passed to MCP
        call_args = mock_client.call_tool.call_args_list[0]
        assert "allergies" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_can_handle_intent_keywords(self):
        """Test can_handle with intent keywords."""
        skill = MedicationCheckSkill()

        assert skill.can_handle("检查这个药是否合理")
        assert skill.can_handle("药物相互作用")
        assert skill.can_handle("用药注意事项")
        assert not skill.can_handle("运动建议")


# ===== ServiceRecommendSkill Tests =====


@pytest.mark.asyncio
class TestServiceRecommendSkill:
    """Tests for ServiceRecommendSkill."""

    def test_initialization(self):
        """Test skill initialization."""
        skill = ServiceRecommendSkill()

        assert skill.config.name == "service_recommend"
        assert skill.config.enabled is True
        assert "保险" in skill.config.intent_keywords
        assert "服务" in skill.config.intent_keywords

    @pytest.mark.asyncio
    async def test_execute_with_mcp_data(
        self,
        mock_llm,
        mock_llm_response,
        sample_health_status,
        sample_user_preferences,
    ):
        """Test execution with MCP integration."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = ServiceRecommendSkill(llm=mock_llm)

        # Mock MCP client
        mock_insurance = {
            "products": [
                {"name": "慢性病关爱保", "premium": "3000 CNY/year"}
            ]
        }
        mock_services = {
            "services": [
                {"name": "高血压管理计划", "price": "2000 CNY"}
            ]
        }

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_service_client = AsyncMock()
            mock_service_client.call_tool = AsyncMock(
                side_effect=[mock_insurance, mock_services]
            )
            mock_factory.get_client.return_value = mock_service_client

            result = await skill.execute(
                health_status=sample_health_status,
                user_preferences=sample_user_preferences,
            )

        assert result.success is True
        assert mock_service_client.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_minimal_params(
        self, mock_llm, mock_llm_response, sample_health_status
    ):
        """Test execution with minimal required parameters."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = ServiceRecommendSkill(llm=mock_llm)

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(
                return_value={"products": [], "services": []}
            )
            mock_factory.get_client.return_value = mock_client

            result = await skill.execute(health_status=sample_health_status)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_can_handle_intent_keywords(self):
        """Test can_handle with intent keywords."""
        skill = ServiceRecommendSkill()

        assert skill.can_handle("推荐保险产品")
        assert skill.can_handle("健康服务有哪些")
        assert skill.can_handle("我想买保险")
        assert not skill.can_handle("分诊建议")


# ===== Integration Tests =====


@pytest.mark.asyncio
class TestMCPToolSkillsIntegration:
    """Integration tests for MCP Tool Skills working together."""

    @pytest.mark.asyncio
    async def test_all_skills_share_base_class(self):
        """Test all MCP tool skills inherit from BaseSkill."""
        from src.infrastructure.dspy.base_skill import BaseSkill

        triage_skill = TriageGuidanceSkill()
        medication_skill = MedicationCheckSkill()
        service_skill = ServiceRecommendSkill()

        assert isinstance(triage_skill, BaseSkill)
        assert isinstance(medication_skill, BaseSkill)
        assert isinstance(service_skill, BaseSkill)

    @pytest.mark.asyncio
    async def test_all_skills_enabled_by_default(self):
        """Test all skills are enabled by default."""
        triage_skill = TriageGuidanceSkill()
        medication_skill = MedicationCheckSkill()
        service_skill = ServiceRecommendSkill()

        assert triage_skill.config.enabled is True
        assert medication_skill.config.enabled is True
        assert service_skill.config.enabled is True

    @pytest.mark.asyncio
    async def test_get_skill_info(self):
        """Test get_skill_info returns correct information."""
        triage_skill = TriageGuidanceSkill()
        info = triage_skill.get_info()

        assert info["name"] == "triage_guidance"
        assert info["enabled"] is True
        assert "health_status" in [f["name"] for f in info["input_fields"]]

    @pytest.mark.asyncio
    async def test_disabled_skill_returns_false_for_can_handle(self):
        """Test disabled skill returns False for can_handle."""
        skill = TriageGuidanceSkill()
        skill.config.enabled = False

        assert not skill.can_handle("医院挂号")

    @pytest.mark.asyncio
    async def test_disabled_skill_fails_execution(self, mock_llm, sample_health_status):
        """Test executing a disabled skill fails."""
        skill = TriageGuidanceSkill(llm=mock_llm)
        skill.config.enabled = False

        result = await skill.execute(health_status=sample_health_status)

        assert result.success is False
        assert "disabled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_skill_with_custom_llm(self, mock_llm):
        """Test skill initialization with custom LLM."""
        skill = TriageGuidanceSkill(llm=mock_llm)

        assert skill._llm == mock_llm


# ===== Error Handling Tests =====


@pytest.mark.asyncio
class TestMCPToolSkillsErrorHandling:
    """Tests for error handling in MCP Tool Skills."""

    @pytest.mark.asyncio
    async def test_triage_handles_mcp_timeout(
        self, mock_llm, mock_llm_response, sample_health_status
    ):
        """Test triage skill handles MCP timeout gracefully."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = TriageGuidanceSkill(llm=mock_llm)

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(side_effect=TimeoutError("Timeout"))
            mock_factory.get_client.return_value = mock_client

            # Should fall back to base execution
            result = await skill.execute(health_status=sample_health_status)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_medication_handles_mcp_error(
        self, mock_llm, mock_llm_response, sample_current_medications
    ):
        """Test medication skill handles MCP errors gracefully."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = MedicationCheckSkill(llm=mock_llm)

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_factory.get_client.side_effect = Exception("Server unavailable")

            result = await skill.execute(current_medications=sample_current_medications)

        # Should still succeed
        assert result.success is True

    @pytest.mark.asyncio
    async def test_service_handles_partial_mcp_data(
        self, mock_llm, mock_llm_response, sample_health_status
    ):
        """Test service skill handles partial MCP data."""
        mock_llm.generate_structured.return_value = mock_llm_response

        skill = ServiceRecommendSkill(llm=mock_llm)

        with patch("src.infrastructure.mcp.MCPClientFactory") as mock_factory:
            mock_client = AsyncMock()
            # First call succeeds, second fails
            mock_client.call_tool = AsyncMock(
                side_effect=[
                    {"products": []},  # insurance succeeds
                    Exception("Service unavailable"),  # services fails
                ]
            )
            mock_factory.get_client.return_value = mock_client

            result = await skill.execute(health_status=sample_health_status)

        # Should still succeed with partial data
        assert result.success is True

    @pytest.mark.asyncio
    async def test_missing_required_field_fails(self, mock_llm):
        """Test execution fails with missing required field."""
        skill = TriageGuidanceSkill(llm=mock_llm)

        result = await skill.execute(
            patient_location={"city": "Beijing"}  # Missing health_status
        )

        assert result.success is False
        assert "Missing required input" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
