"""
Service MCP Client.

Client for the service_server which provides service recommendations
including insurance products, health services, and rehabilitation services.
"""
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path

from ..base_client import BaseMCPClient, MCPToolError

logger = logging.getLogger(__name__)


class ServiceMCPClient(BaseMCPClient):
    """
    MCP client for service recommendations.

    Provides methods to get insurance product recommendations,
    health service recommendations, and rehabilitation services.
    """

    def __init__(self, server_name: str = "service_server", transport: str = "stdio"):
        """
        Initialize the Service MCP client.

        Args:
            server_name: Name of the MCP server
            transport: Transport type ("stdio" or "sse")
        """
        command = self.get_server_command()
        super().__init__(server_name=server_name, transport=transport, command=command)

    def get_server_command(self) -> str:
        """
        Get the command to start the service MCP server.

        Returns:
            Command string to start the server
        """
        import sys
        server_path = Path(__file__).parent.parent.parent.parent.parent / "mcp_servers" / "service_server" / "main.py"
        return f"{sys.executable} {server_path}"

    async def recommend_insurance(
        self,
        patient_id: str,
        diagnosis: Optional[str] = None,
        risk_factors: Optional[List[str]] = None,
        age: Optional[int] = None,
        budget_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Recommend insurance products based on patient profile.

        Args:
            patient_id: Patient identifier
            diagnosis: Patient diagnosis
            risk_factors: List of risk factors
            age: Patient age
            budget_level: Budget preference (low, medium, high)

        Returns:
            Dictionary containing insurance recommendations:
            - chronic_disease_insurance: Chronic disease insurance options
            - critical_illness_insurance: Critical illness insurance options
            - medical_insurance: General medical insurance options
            - coverage_details: Coverage information for each product
            - premium_estimates: Estimated premium costs
            - claim_conditions: Conditions for claims
            - purchase_links: Links to purchase

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "budget_level": budget_level
            }
            if diagnosis:
                params["diagnosis"] = diagnosis
            if risk_factors:
                params["risk_factors"] = risk_factors
            if age:
                params["age"] = age

            result = await self.call_tool("recommend_insurance", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to recommend insurance for {patient_id}: {e}")
            raise MCPToolError(f"Failed to recommend insurance: {e}") from e

    async def recommend_health_services(
        self,
        patient_id: str,
        condition: Optional[str] = None,
        health_goals: Optional[List[str]] = None,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend health services based on patient needs.

        Args:
            patient_id: Patient identifier
            condition: Medical condition
            health_goals: List of health goals
            service_type: Specific service type filter

        Returns:
            Dictionary containing health service recommendations:
            - disease_management_services: Disease management programs
            - health_promotion_services: Health promotion services
            - rehabilitation_services: Rehabilitation programs
            - preventive_services: Preventive care services
            - service_details: Details for each service
            - pricing: Service pricing information
            - booking_info: How to book the service

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {"patient_id": patient_id}
            if condition:
                params["condition"] = condition
            if health_goals:
                params["health_goals"] = health_goals
            if service_type:
                params["service_type"] = service_type

            result = await self.call_tool("recommend_health_services", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to recommend health services for {patient_id}: {e}")
            raise MCPToolError(f"Failed to recommend health services: {e}") from e

    async def recommend_checkup_packages(
        self,
        patient_id: str,
        age_group: Optional[str] = None,
        risk_factors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recommend health checkup packages.

        Args:
            patient_id: Patient identifier
            age_group: Age group (young, middle, senior)
            risk_factors: List of risk factors

        Returns:
            Dictionary containing checkup package recommendations:
            - basic_package: Basic health checkup
            - comprehensive_package: Comprehensive checkup
            - targeted_packages: Targeted checkups based on conditions
            - package_contents: What each package includes
            - recommended_frequency: How often to get checkups
            - pricing: Package prices

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {"patient_id": patient_id}
            if age_group:
                params["age_group"] = age_group
            if risk_factors:
                params["risk_factors"] = risk_factors

            result = await self.call_tool("recommend_checkup_packages", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to recommend checkup packages for {patient_id}: {e}")
            raise MCPToolError(f"Failed to recommend checkup packages: {e}") from e

    async def recommend_rehabilitation(
        self,
        patient_id: str,
        condition: str,
        recovery_stage: str = "stable"
    ) -> Dict[str, Any]:
        """
        Recommend rehabilitation services.

        Args:
            patient_id: Patient identifier
            condition: Medical condition requiring rehab
            recovery_stage: Stage of recovery (acute, subacute, stable)

        Returns:
            Dictionary containing rehabilitation recommendations:
            - cardiac_rehabilitation: Cardiac rehab programs if applicable
            - pulmonary_rehabilitation: Pulmonary rehab programs if applicable
            - physical_therapy: Physical therapy options
            - occupational_therapy: Occupational therapy options
            - exercise_programs: Recommended exercise programs
            - service_providers: List of service providers
            - expected_outcomes: Expected rehabilitation outcomes

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            result = await self.call_tool(
                "recommend_rehabilitation",
                {
                    "patient_id": patient_id,
                    "condition": condition,
                    "recovery_stage": recovery_stage
                }
            )
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to recommend rehabilitation for {patient_id}: {e}")
            raise MCPToolError(f"Failed to recommend rehabilitation: {e}") from e

    def _parse_tool_result(self, result: Any) -> Dict[str, Any]:
        """
        Parse tool result and extract content.

        Args:
            result: Raw result from MCP tool call

        Returns:
            Parsed dictionary with tool result data
        """
        if hasattr(result, 'content'):
            # Handle CallToolResult format
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    import json
                    try:
                        return json.loads(content_item.text)
                    except json.JSONDecodeError:
                        return {"raw": content_item.text}
        elif isinstance(result, dict):
            return result
        return {"raw": str(result)}
