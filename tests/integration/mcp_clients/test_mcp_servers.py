"""
Integration tests for MCP servers.

These tests verify that MCP servers respond correctly to tool calls.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_servers.profile_server.main import server as profile_server
from mcp_servers.triage_server.main import server as triage_server
from mcp_servers.medication_server.main import server as medication_server
from mcp_servers.service_server.main import server as service_server


@pytest.mark.asyncio
class TestProfileServer:
    """Test profile_server MCP server."""

    async def test_list_tools(self):
        """Test listing available tools."""
        from mcp_servers.profile_server.tools import TOOLS

        tool_names = [tool["name"] for tool in TOOLS]
        expected_tools = [
            "get_patient_profile",
            "get_vital_signs",
            "get_medical_records",
            "get_lab_results"
        ]

        assert set(tool_names) == set(expected_tools)

    async def test_tool_schemas(self):
        """Test that tool schemas are valid."""
        from mcp_servers.profile_server.tools import TOOLS

        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]
            assert "required" in tool["inputSchema"]

    async def test_get_patient_profile_tool(self):
        """Test get_patient_profile tool handler."""
        from mcp_servers.profile_server.tools import get_patient_profile

        with patch(
            'mcp_servers.profile_server.tools.HealthArchiveHTTPClient'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get_patient_profile = AsyncMock(
                return_value={"patient_id": "P001", "name": "Test"}
            )
            mock_client_class.return_value = mock_client

            result = await get_patient_profile("P001")

            assert result["patient_id"] == "P001"
            assert result["name"] == "Test"


@pytest.mark.asyncio
class TestTriageServer:
    """Test triage_server MCP server."""

    async def test_list_tools(self):
        """Test listing available tools."""
        from mcp_servers.triage_server.tools import TOOLS

        tool_names = [tool["name"] for tool in TOOLS]
        expected_tools = [
            "get_hospitals",
            "get_departments",
            "get_doctors",
            "get_triage_advice"
        ]

        assert set(tool_names) == set(expected_tools)

    async def test_get_hospitals_tool(self):
        """Test get_hospitals tool handler."""
        from mcp_servers.triage_server.tools import get_hospitals

        with patch(
            'mcp_servers.triage_server.tools.TriageGuidanceHTTPClient'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get_hospitals = AsyncMock(
                return_value={"hospitals": [{"name": "Test Hospital"}]}
            )
            mock_client_class.return_value = mock_client

            result = await get_hospitals("P001", severity="moderate")

            assert "hospitals" in result
            assert len(result["hospitals"]) > 0


@pytest.mark.asyncio
class TestMedicationServer:
    """Test medication_server MCP server."""

    async def test_list_tools(self):
        """Test listing available tools."""
        from mcp_servers.medication_server.tools import TOOLS

        tool_names = [tool["name"] for tool in TOOLS]
        expected_tools = [
            "check_medication",
            "recommend_drugs",
            "check_drug_interactions",
            "check_contraindications"
        ]

        assert set(tool_names) == set(expected_tools)

    async def test_check_medication_tool(self):
        """Test check_medication tool handler."""
        from mcp_servers.medication_server.tools import check_medication

        with patch(
            'mcp_servers.medication_server.tools.MedicationCheckingHTTPClient'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.check_medication = AsyncMock(
                return_value={"safe": True, "warnings": []}
            )
            mock_client_class.return_value = mock_client

            result = await check_medication("P001", "Aspirin")

            assert "safe" in result


@pytest.mark.asyncio
class TestServiceServer:
    """Test service_server MCP server."""

    async def test_list_tools(self):
        """Test listing available tools."""
        from mcp_servers.service_server.tools import TOOLS

        tool_names = [tool["name"] for tool in TOOLS]
        expected_tools = [
            "recommend_insurance",
            "recommend_health_services",
            "recommend_checkup_packages",
            "recommend_rehabilitation"
        ]

        assert set(tool_names) == set(expected_tools)

    async def test_recommend_insurance_tool(self):
        """Test recommend_insurance tool handler."""
        from mcp_servers.service_server.tools import recommend_insurance

        with patch(
            'mcp_servers.service_server.tools.ServiceRecommendationHTTPClient'
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.recommend_insurance = AsyncMock(
                return_value={"recommendations": []}
            )
            mock_client_class.return_value = mock_client

            result = await recommend_insurance("P001")

            assert "recommendations" in result


@pytest.mark.asyncio
class TestServerHealthChecks:
    """Test server health check endpoints."""

    async def test_profile_server_health_check(self):
        """Test profile_server health check."""
        from mcp_servers.profile_server.main import health_check

        result = health_check()

        assert result["status"] == "healthy"
        assert result["server"] == "profile-server"

    async def test_triage_server_health_check(self):
        """Test triage_server health check."""
        from mcp_servers.triage_server.main import health_check

        result = health_check()

        assert result["status"] == "healthy"
        assert result["server"] == "triage-server"

    async def test_medication_server_health_check(self):
        """Test medication_server health check."""
        from mcp_servers.medication_server.main import health_check

        result = health_check()

        assert result["status"] == "healthy"
        assert result["server"] == "medication-server"

    async def test_service_server_health_check(self):
        """Test service_server health check."""
        from mcp_servers.service_server.main import health_check

        result = health_check()

        assert result["status"] == "healthy"
        assert result["server"] == "service-server"


@pytest.mark.asyncio
class TestMCPServerStartup:
    """Test MCP server startup functionality."""

    async def test_server_initialization_options(self):
        """Test that servers can be initialized with proper options."""
        from mcp.server.models import InitializationOptions

        # All servers should have similar initialization structure
        init_options = InitializationOptions(
            server_name="test-server",
            server_version="1.0.0",
            capabilities={}
        )

        assert init_options.server_name == "test-server"
        assert init_options.server_version == "1.0.0"
