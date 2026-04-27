"""
MCP tools for profile_server.

Defines MCP tools for accessing patient health profile data.
"""
import logging
from typing import Any, Dict
import os

from .http_client import HealthArchiveHTTPClient
from .pingan_client import PingAnHealthArchiveClient

logger = logging.getLogger(__name__)

# Get service URL from environment or use default
HEALTH_ARCHIVE_URL = os.getenv("HEALTH_ARCHIVE_URL", "http://localhost:8080")
HEALTH_ARCHIVE_API_KEY = os.getenv("HEALTH_ARCHIVE_API_KEY")


async def get_patient_profile(patient_id: str) -> Dict[str, Any]:
    """
    Get patient basic profile information.

    Args:
        patient_id: Patient identifier (e.g., "P001")

    Returns:
        Dictionary containing patient profile data:
        - patient_id: Patient identifier
        - name: Patient name
        - gender: Gender (male/female)
        - age: Age in years
        - birth_date: Date of birth
        - phone: Contact phone number
        - email: Email address (optional)
    """
    logger.info(f"Getting patient profile for: {patient_id}")

    async with HealthArchiveHTTPClient(
        base_url=HEALTH_ARCHIVE_URL,
        api_key=HEALTH_ARCHIVE_API_KEY
    ) as client:
        result = await client.get_patient_profile(patient_id)
        logger.info(f"Retrieved profile for patient: {patient_id}")
        return result


async def get_vital_signs(patient_id: str) -> Dict[str, Any]:
    """
    Get patient vital signs data.

    Args:
        patient_id: Patient identifier

    Returns:
        Dictionary containing vital signs data:
        - blood_pressure: Systolic/diastolic values
        - blood_glucose: Fasting and postprandial glucose
        - lipids: Total cholesterol, triglycerides, HDL, LDL
        - uric_acid: Serum uric acid level
        - bmi: Body mass index
        - waist_circumference: Waist measurement
        - measured_at: Timestamp of measurement
    """
    logger.info(f"Getting vital signs for patient: {patient_id}")

    async with HealthArchiveHTTPClient(
        base_url=HEALTH_ARCHIVE_URL,
        api_key=HEALTH_ARCHIVE_API_KEY
    ) as client:
        result = await client.get_vital_signs(patient_id)
        logger.info(f"Retrieved vital signs for patient: {patient_id}")
        return result


async def get_medical_records(patient_id: str) -> Dict[str, Any]:
    """
    Get patient medical records and history.

    Args:
        patient_id: Patient identifier

    Returns:
        Dictionary containing medical records:
        - diagnoses: List of diagnoses with ICD codes
        - surgeries: List of surgical procedures
        - allergies: List of known allergies
        - medications: Current medications
        - chronic_diseases: List of chronic conditions
        - family_history: Family medical history
    """
    logger.info(f"Getting medical records for patient: {patient_id}")

    async with HealthArchiveHTTPClient(
        base_url=HEALTH_ARCHIVE_URL,
        api_key=HEALTH_ARCHIVE_API_KEY
    ) as client:
        result = await client.get_medical_records(patient_id)
        logger.info(f"Retrieved medical records for patient: {patient_id}")
        return result


async def get_lab_results(patient_id: str, test_type: str = None) -> Dict[str, Any]:
    """
    Get patient laboratory test results.

    Args:
        patient_id: Patient identifier
        test_type: Optional specific test type filter

    Returns:
        Dictionary containing lab results:
        - blood_count: Complete blood count results
        - metabolic_panel: Metabolic panel results
        - lipid_panel: Lipid panel results
        - thyroid_function: Thyroid function tests
        - hba1c: Hemoglobin A1c
        - tested_at: Timestamp of test
    """
    logger.info(f"Getting lab results for patient: {patient_id}")

    async with HealthArchiveHTTPClient(
        base_url=HEALTH_ARCHIVE_URL,
        api_key=HEALTH_ARCHIVE_API_KEY
    ) as client:
        result = await client.get_lab_results(patient_id, test_type)
        logger.info(f"Retrieved lab results for patient: {patient_id}")
        return result


async def get_health_data(party_id: str) -> Dict[str, Any]:
    """
    Get patient health data from Ping An health archive.

    This function queries the Ping An health archive system using OAuth2
    authentication to retrieve comprehensive patient health information.

    Args:
        party_id: Customer/Patient identifier (客户号/partyId)

    Returns:
        Dictionary containing health data from Ping An system:
        - Basic information: Name, gender, age, etc.
        - Health indicators: Blood pressure, blood glucose, etc.
        - Medical records: Diagnoses, medications, etc.
        - Lab results: Various test results
        - _metadata: Request metadata including party_id and request_id

    API Details:
        Token URL: https://test-api.pingan.com.cn:20443/oauth/oauth2/access_token
        Data URL: https://test-api.pingan.com.cn:20443/open/appsvr/health/ehis/iesp/purveyor/postWithJson.do
        iespApiCode: queryHealthData
    """
    logger.info(f"Getting health data from Ping An for party_id: {party_id}")

    async with PingAnHealthArchiveClient() as client:
        result = await client.get_health_data(party_id)
        logger.info(f"Retrieved health data for party_id: {party_id}")
        return result


# Tool definitions for MCP server
TOOLS = [
    {
        "name": "get_patient_profile",
        "description": "Get patient basic profile information including name, gender, age, and contact details",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier (e.g., 'P001')"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_vital_signs",
        "description": "Get patient vital signs data including blood pressure, blood glucose, lipids, uric acid, and BMI",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_medical_records",
        "description": "Get patient medical records including diagnoses, surgeries, allergies, medications, and chronic diseases",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_lab_results",
        "description": "Get patient laboratory test results including blood count, metabolic panel, and lipid panel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "test_type": {
                    "type": "string",
                    "description": "Optional specific test type filter"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_health_data",
        "description": "Get comprehensive patient health data from Ping An health archive system using OAuth2 authentication. Queries basic info, vital signs, medical records, and lab results by customer ID (partyId/客户号)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "party_id": {
                    "type": "string",
                    "description": "Customer/Patient identifier from Ping An system (客户号/partyId)"
                }
            },
            "required": ["party_id"]
        }
    }
]

# Tool handlers mapping
TOOL_HANDLERS = {
    "get_patient_profile": get_patient_profile,
    "get_vital_signs": get_vital_signs,
    "get_medical_records": get_medical_records,
    "get_lab_results": get_lab_results,
    "get_health_data": get_health_data,
}
