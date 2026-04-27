"""
Medication MCP Client.

Client for the medication_server which provides medication checking
and drug recommendation services.
"""
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path

from ..base_client import BaseMCPClient, MCPToolError

logger = logging.getLogger(__name__)


class MedicationMCPClient(BaseMCPClient):
    """
    MCP client for medication checking and recommendation.

    Provides methods to check medication safety, including
    indication verification, dosage validation, drug interaction
    checking, and contraindication screening.
    """

    def __init__(self, server_name: str = "medication_server", transport: str = "stdio"):
        """
        Initialize the Medication MCP client.

        Args:
            server_name: Name of the MCP server
            transport: Transport type ("stdio" or "sse")
        """
        command = self.get_server_command()
        super().__init__(server_name=server_name, transport=transport, command=command)

    def get_server_command(self) -> str:
        """
        Get the command to start the medication MCP server.

        Returns:
            Command string to start the server
        """
        import sys
        server_path = Path(__file__).parent.parent.parent.parent.parent / "mcp_servers" / "medication_server" / "main.py"
        return f"{sys.executable} {server_path}"

    async def check_medication(
        self,
        patient_id: str,
        medication: str,
        dosage: Optional[str] = None,
        frequency: Optional[str] = None,
        current_medications: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check medication for safety and appropriateness.

        Args:
            patient_id: Patient identifier
            medication: Medication name to check
            dosage: Dosage information (e.g., "10mg")
            frequency: Dosing frequency (e.g., "twice daily")
            current_medications: List of current medications for interaction check

        Returns:
            Dictionary containing medication check results:
            - medication_name: Name of checked medication
            - indication_match: Whether indication matches patient condition
            - dosage_appropriate: Whether dosage is appropriate
            - dosage_warnings: Any dosage-related warnings
            - interactions: List of drug interactions found
            - contraindications: List of contraindications
            - special_populations: Special population considerations
            - recommendations: Safety recommendations

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "medication": medication
            }
            if dosage:
                params["dosage"] = dosage
            if frequency:
                params["frequency"] = frequency
            if current_medications:
                params["current_medications"] = current_medications

            result = await self.call_tool("check_medication", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to check medication for {patient_id}: {e}")
            raise MCPToolError(f"Failed to check medication: {e}") from e

    async def recommend_drugs(
        self,
        patient_id: str,
        condition: str,
        severity: str = "moderate",
        patient_age: Optional[int] = None,
        renal_function: Optional[str] = None,
        hepatic_function: Optional[str] = None,
        allergies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recommend appropriate drugs based on patient condition.

        Args:
            patient_id: Patient identifier
            condition: Medical condition to treat
            severity: Condition severity (mild, moderate, severe)
            patient_age: Patient age in years
            renal_function: Renal function status (normal, mild_impairment, moderate_impairment, severe_impairment)
            hepatic_function: Hepatic function status
            allergies: List of known drug allergies

        Returns:
            Dictionary containing drug recommendations:
            - condition: Treated condition
            - first_line_recommendations: First-line treatment options
            - alternative_recommendations: Alternative treatment options
            - contraindicated_drugs: Drugs to avoid
            - special_considerations: Special considerations
            - monitoring_parameters: Parameters to monitor
            - lifestyle_recommendations: Recommended lifestyle changes

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "condition": condition,
                "severity": severity
            }
            if patient_age:
                params["patient_age"] = patient_age
            if renal_function:
                params["renal_function"] = renal_function
            if hepatic_function:
                params["hepatic_function"] = hepatic_function
            if allergies:
                params["allergies"] = allergies

            result = await self.call_tool("recommend_drugs", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to recommend drugs for {patient_id}: {e}")
            raise MCPToolError(f"Failed to recommend drugs: {e}") from e

    async def check_drug_interactions(
        self,
        medications: List[str]
    ) -> Dict[str, Any]:
        """
        Check for drug-drug interactions.

        Args:
            medications: List of medications to check

        Returns:
            Dictionary containing interaction check results:
            - medications: Checked medications
            - interactions: List of interactions found
            - severity_levels: Severity of each interaction
            - management_recommendations: How to manage each interaction

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            result = await self.call_tool(
                "check_drug_interactions",
                {"medications": medications}
            )
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to check drug interactions: {e}")
            raise MCPToolError(f"Failed to check drug interactions: {e}") from e

    async def check_contraindications(
        self,
        patient_id: str,
        medication: str,
        conditions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check for medication contraindications.

        Args:
            patient_id: Patient identifier
            medication: Medication to check
            conditions: List of patient conditions

        Returns:
            Dictionary containing contraindication check results:
            - medication: Checked medication
            - absolute_contraindications: Absolute contraindications
            - relative_contraindications: Relative contraindications
            - precautions: Precautionary notes
            - recommendations: Recommendations based on contraindications

        Raises:
            MCPToolError: If the tool call fails
        """
        try:
            params = {
                "patient_id": patient_id,
                "medication": medication
            }
            if conditions:
                params["conditions"] = conditions

            result = await self.call_tool("check_contraindications", params)
            return self._parse_tool_result(result)
        except Exception as e:
            logger.error(f"Failed to check contraindications for {patient_id}: {e}")
            raise MCPToolError(f"Failed to check contraindications: {e}") from e

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
