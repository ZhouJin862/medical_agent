"""
Profile MCP Client.

Client for the profile_server which provides access to patient health records
including basic profile information, vital signs, and medical records.
"""
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from ..base_client import BaseMCPClient, MCPToolError

logger = logging.getLogger(__name__)


class ProfileMCPClient(BaseMCPClient):
    """
    MCP client for health profile data.

    Provides methods to retrieve patient profile information,
    vital signs data, and medical records from the health archive system.
    """

    def __init__(self, server_name: str = "profile_server", transport: str = "stdio"):
        """
        Initialize the Profile MCP client.

        Args:
            server_name: Name of the MCP server
            transport: Transport type ("stdio" or "sse")
        """
        command = self.get_server_command()
        super().__init__(server_name=server_name, transport=transport, command=command)

    def get_server_command(self) -> str:
        """
        Get the command to start the profile MCP server.

        Returns:
            Command string to start the server
        """
        import sys
        server_path = Path(__file__).parent.parent.parent.parent.parent / "mcp_servers" / "profile_server" / "main.py"
        return f"{sys.executable} {server_path}"

    async def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient basic profile information.

        Args:
            patient_id: Patient identifier

        Returns:
            Dictionary containing patient profile data including:
            - patient_id: Patient identifier
            - name: Patient name
            - gender: Gender (male/female)
            - age: Age in years
            - birth_date: Date of birth
            - phone: Contact phone number
            - email: Email address (optional)

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            result = await self.call_tool(
                "get_patient_profile",
                {"patient_id": patient_id}
            )
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to get patient profile for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get patient profile: {e}") from e

    async def get_vital_signs(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient vital signs data.

        Args:
            patient_id: Patient identifier

        Returns:
            Dictionary containing vital signs data including:
            - blood_pressure: Systolic/diastolic values
            - blood_glucose: Fasting and postprandial glucose
            - lipids: Total cholesterol, triglycerides, HDL, LDL
            - uric_acid: Serum uric acid level
            - bmi: Body mass index
            - waist_circumference: Waist measurement
            - measured_at: Timestamp of measurement

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            result = await self.call_tool(
                "get_vital_signs",
                {"patient_id": patient_id}
            )
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to get vital signs for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get vital signs: {e}") from e

    async def get_medical_records(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient medical records and history.

        Args:
            patient_id: Patient identifier

        Returns:
            Dictionary containing medical records including:
            - diagnoses: List of diagnoses with ICD codes
            - surgeries: List of surgical procedures
            - allergies: List of known allergies
            - medications: Current medications
            - chronic_diseases: List of chronic conditions
            - family_history: Family medical history

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            result = await self.call_tool(
                "get_medical_records",
                {"patient_id": patient_id}
            )
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to get medical records for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get medical records: {e}") from e

    async def get_lab_results(self, patient_id: str, test_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get patient laboratory test results.

        Args:
            patient_id: Patient identifier
            test_type: Optional specific test type filter

        Returns:
            Dictionary containing lab results including:
            - blood_count: Complete blood count results
            - metabolic_panel: Metabolic panel results
            - lipid_panel: Lipid panel results
            - thyroid_function: Thyroid function tests
            - hba1c: Hemoglobin A1c
            - tested_at: Timestamp of test

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {"patient_id": patient_id}
            if test_type:
                params["test_type"] = test_type

            result = await self.call_tool(
                "get_lab_results",
                params
            )
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to get lab results for {patient_id}: {e}")
            raise MCPToolError(f"Failed to get lab results: {e}") from e

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
