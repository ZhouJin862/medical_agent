"""
MCP tools for triage_server.

Defines MCP tools for triage guidance including hospital,
department, and doctor recommendations.
"""
import logging
from typing import Any, Dict, List, Optional
import os

from .http_client import TriageGuidanceHTTPClient

logger = logging.getLogger(__name__)

# Get service URL from environment or use default
TRIAGE_SERVICE_URL = os.getenv("TRIAGE_SERVICE_URL", "http://localhost:8081")
TRIAGE_SERVICE_API_KEY = os.getenv("TRIAGE_SERVICE_API_KEY")


async def get_hospitals(
    patient_id: str,
    severity: str = "moderate",
    location: Optional[str] = None,
    radius_km: int = 50
) -> Dict[str, Any]:
    """
    Get hospital recommendations based on patient condition and location.

    Args:
        patient_id: Patient identifier
        severity: Severity level (mild, moderate, severe, emergency)
        location: Patient location (city/district)
        radius_km: Search radius in kilometers

    Returns:
        Dictionary containing hospital recommendations:
        - hospitals: List of hospital options with details
        - distance_km: Distance from patient
        - emergency_available: Emergency services availability
    """
    logger.info(f"Getting hospitals for patient: {patient_id}, severity: {severity}")

    async with TriageGuidanceHTTPClient(
        base_url=TRIAGE_SERVICE_URL,
        api_key=TRIAGE_SERVICE_API_KEY
    ) as client:
        result = await client.get_hospitals(patient_id, severity, location, radius_km)
        logger.info(f"Retrieved hospitals for patient: {patient_id}")
        return result


async def get_departments(
    patient_id: str,
    symptoms: Optional[List[str]] = None,
    diagnosis: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get department recommendations based on symptoms or diagnosis.

    Args:
        patient_id: Patient identifier
        symptoms: List of patient symptoms
        diagnosis: Patient diagnosis

    Returns:
        Dictionary containing department recommendations:
        - departments: List of recommended departments
        - priority: Recommendation priority
        - reason: Reason for recommendation
    """
    logger.info(f"Getting departments for patient: {patient_id}")

    async with TriageGuidanceHTTPClient(
        base_url=TRIAGE_SERVICE_URL,
        api_key=TRIAGE_SERVICE_API_KEY
    ) as client:
        result = await client.get_departments(patient_id, symptoms, diagnosis)
        logger.info(f"Retrieved departments for patient: {patient_id}")
        return result


async def get_doctors(
    patient_id: str,
    department: str,
    specialty: Optional[str] = None,
    need_expert: bool = False
) -> Dict[str, Any]:
    """
    Get doctor recommendations for a specific department.

    Args:
        patient_id: Patient identifier
        department: Target department name
        specialty: Doctor specialty (optional)
        need_expert: Whether to recommend experts only

    Returns:
        Dictionary containing doctor recommendations:
        - doctors: List of recommended doctors
        - name: Doctor name
        - title: Professional title
        - expertise_areas: Areas of expertise
    """
    logger.info(f"Getting doctors for patient: {patient_id}, department: {department}")

    async with TriageGuidanceHTTPClient(
        base_url=TRIAGE_SERVICE_URL,
        api_key=TRIAGE_SERVICE_API_KEY
    ) as client:
        result = await client.get_doctors(patient_id, department, specialty, need_expert)
        logger.info(f"Retrieved doctors for patient: {patient_id}")
        return result


async def get_triage_advice(
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
        Dictionary containing triage advice:
        - urgency_level: Urgency level (routine, urgent, emergency)
        - recommended_timing: Recommended timing for visit
        - recommended_department: Suggested department
        - self_care_instructions: Self-care instructions if applicable
        - warning_signs: Warning signs requiring immediate attention
    """
    logger.info(f"Getting triage advice for patient: {patient_id}")

    async with TriageGuidanceHTTPClient(
        base_url=TRIAGE_SERVICE_URL,
        api_key=TRIAGE_SERVICE_API_KEY
    ) as client:
        result = await client.get_triage_advice(patient_id, symptoms, urgency_assessment)
        logger.info(f"Retrieved triage advice for patient: {patient_id}")
        return result


# Tool definitions for MCP server
TOOLS = [
    {
        "name": "get_hospitals",
        "description": "Get hospital recommendations based on patient condition severity and location",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "severity": {
                    "type": "string",
                    "enum": ["mild", "moderate", "severe", "emergency"],
                    "description": "Severity level of patient condition"
                },
                "location": {
                    "type": "string",
                    "description": "Patient location (city/district)"
                },
                "radius_km": {
                    "type": "integer",
                    "description": "Search radius in kilometers"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_departments",
        "description": "Get department recommendations based on patient symptoms or diagnosis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "symptoms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of patient symptoms"
                },
                "diagnosis": {
                    "type": "string",
                    "description": "Patient diagnosis"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_doctors",
        "description": "Get doctor recommendations for a specific department",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "department": {
                    "type": "string",
                    "description": "Target department name"
                },
                "specialty": {
                    "type": "string",
                    "description": "Doctor specialty"
                },
                "need_expert": {
                    "type": "boolean",
                    "description": "Whether to recommend experts only"
                }
            },
            "required": ["patient_id", "department"]
        }
    },
    {
        "name": "get_triage_advice",
        "description": "Get triage advice including urgency level and recommended actions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "symptoms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of current symptoms"
                },
                "urgency_assessment": {
                    "type": "string",
                    "description": "Optional urgency assessment"
                }
            },
            "required": ["patient_id", "symptoms"]
        }
    }
]

# Tool handlers mapping
TOOL_HANDLERS = {
    "get_hospitals": get_hospitals,
    "get_departments": get_departments,
    "get_doctors": get_doctors,
    "get_triage_advice": get_triage_advice,
}
