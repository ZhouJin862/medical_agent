"""
Triage MCP Client.

Client for the triage_server which provides triage guidance including
hospital recommendations, department recommendations, and doctor recommendations.
"""
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path

from ..base_client import BaseMCPClient, MCPToolError

logger = logging.getLogger(__name__)


class TriageMCPClient(BaseMCPClient):
    """
    MCP client for triage guidance.

    Provides methods to get hospital recommendations, department
    recommendations, and doctor recommendations based on patient
    symptoms and location.
    """

    def __init__(self, server_name: str = "triage_server", transport: str = "stdio"):
        """
        Initialize the Triage MCP client.

        Args:
            server_name: Name of the MCP server
            transport: Transport type ("stdio" or "sse")
        """
        command = self.get_server_command()
        super().__init__(server_name=server_name, transport=transport, command=command)

    def get_server_command(self) -> str:
        """
        Get the command to start the triage MCP server.

        Returns:
            Command string to start the server
        """
        import sys
        server_path = Path(__file__).parent.parent.parent.parent.parent / "mcp_servers" / "triage_server" / "main.py"
        return f"{sys.executable} {server_path}"

    async def get_hospitals(
        self,
        patient_id: str,
        severity: str = "moderate",
        location: Optional[str] = None,
        radius_km: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get hospital recommendations based on patient condition and location.

        Args:
            patient_id: Patient identifier
            severity: Severity level (mild, moderate, severe, emergency)
            location: Patient location (city/district)
            radius_km: Search radius in kilometers

        Returns:
            List of hospital recommendations including:
            - hospital_id: Hospital identifier
            - name: Hospital name
            - level: Hospital level (tertiary, secondary, primary)
            - distance_km: Distance from patient
            - address: Hospital address
            - emergency_available: Whether emergency services available
            - recommended_departments: Suggested departments
            - estimated_travel_time: Estimated travel time

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "severity": severity,
                "radius_km": radius_km
            }
            if location:
                params["location"] = location

            result = await self.call_tool("get_hospitals", params)
            parsed = self._parse_tool_result(result)
            return parsed.get("hospitals", [])
        except Exception as e:
            logger.error(f"Failed to get hospitals for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get hospitals: {e}") from e

    async def get_departments(
        self,
        patient_id: str,
        symptoms: Optional[List[str]] = None,
        diagnosis: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get department recommendations based on symptoms or diagnosis.

        Args:
            patient_id: Patient identifier
            symptoms: List of patient symptoms
            diagnosis: Patient diagnosis

        Returns:
            List of department recommendations including:
            - department_id: Department identifier
            - name: Department name
            - priority: Recommendation priority (high, medium, low)
            - reason: Reason for recommendation
            - related_symptoms: Symptoms related to this department

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {"patient_id": patient_id}
            if symptoms:
                params["symptoms"] = symptoms
            if diagnosis:
                params["diagnosis"] = diagnosis

            result = await self.call_tool("get_departments", params)
            parsed = self._parse_tool_result(result)
            return parsed.get("departments", [])
        except Exception as e:
            logger.error(f"Failed to get departments for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get departments: {e}") from e

    async def get_doctors(
        self,
        patient_id: str,
        department: str,
        specialty: Optional[str] = None,
        need_expert: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get doctor recommendations for a specific department.

        Args:
            patient_id: Patient identifier
            department: Target department name
            specialty: Doctor specialty (optional)
            need_expert: Whether to recommend experts only

        Returns:
            List of doctor recommendations including:
            - doctor_id: Doctor identifier
            - name: Doctor name
            - title: Professional title (Chief, Associate, Attending)
            - department: Department name
            - specialty: Medical specialty
            - expertise_areas: Areas of expertise
            - schedule: Available schedule
            - consultation_fee: Consultation fee

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "department": department,
                "need_expert": need_expert
            }
            if specialty:
                params["specialty"] = specialty

            result = await self.call_tool("get_doctors", params)
            parsed = self._parse_tool_result(result)
            return parsed.get("doctors", [])
        except Exception as e:
            logger.error(f"Failed to get doctors for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get doctors: {e}") from e

    async def get_triage_advice(
        self,
        patient_id: str,
        symptoms: List[str],
        urgency_assessment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get triage advice including urgency and recommended actions.

        Args:
            patient_id: Patient identifier
            symptoms: List of current symptoms
            urgency_assessment: Optional urgency assessment

        Returns:
            Dictionary containing triage advice including:
            - urgency_level: Urgency level (routine, urgent, emergency)
            - recommended_timing: Recommended timing for visit
            - recommended_department: Suggested department
            - self_care_instructions: Self-care instructions if applicable
            - warning_signs: Warning signs requiring immediate attention

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "symptoms": symptoms
            }
            if urgency_assessment:
                params["urgency_assessment"] = urgency_assessment

            result = await self.call_tool("get_triage_advice", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to get triage advice for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get triage advice: {e}") from e

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
