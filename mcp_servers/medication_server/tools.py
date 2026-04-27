"""
MCP tools for medication_server.

Defines MCP tools for medication checking and drug recommendation.
"""
import logging
from typing import Any, Dict, List, Optional
import os

from .http_client import MedicationCheckingHTTPClient

logger = logging.getLogger(__name__)

# Get service URL from environment or use default
MEDICATION_SERVICE_URL = os.getenv("MEDICATION_SERVICE_URL", "http://localhost:8082")
MEDICATION_SERVICE_API_KEY = os.getenv("MEDICATION_SERVICE_API_KEY")


async def check_medication(
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
        current_medications: List of current medications

    Returns:
        Medication check results including:
        - indication_match: Whether indication matches
        - dosage_appropriate: Whether dosage is appropriate
        - interactions: Drug interactions found
        - contraindications: Contraindications
        - recommendations: Safety recommendations
    """
    logger.info(f"Checking medication: {medication} for patient: {patient_id}")

    async with MedicationCheckingHTTPClient(
        base_url=MEDICATION_SERVICE_URL,
        api_key=MEDICATION_SERVICE_API_KEY
    ) as client:
        result = await client.check_medication(
            patient_id, medication, dosage, frequency, current_medications
        )
        logger.info(f"Medication check completed for: {medication}")
        return result


async def recommend_drugs(
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
        renal_function: Renal function status
        hepatic_function: Hepatic function status
        allergies: List of known drug allergies

    Returns:
        Drug recommendations including:
        - first_line_recommendations: First-line options
        - alternative_recommendations: Alternative options
        - contraindicated_drugs: Drugs to avoid
        - special_considerations: Special considerations
    """
    logger.info(f"Recommending drugs for condition: {condition}, patient: {patient_id}")

    async with MedicationCheckingHTTPClient(
        base_url=MEDICATION_SERVICE_URL,
        api_key=MEDICATION_SERVICE_API_KEY
    ) as client:
        result = await client.recommend_drugs(
            patient_id, condition, severity, patient_age,
            renal_function, hepatic_function, allergies
        )
        logger.info(f"Drug recommendations completed for: {condition}")
        return result


async def check_drug_interactions(
    medications: List[str]
) -> Dict[str, Any]:
    """
    Check for drug-drug interactions.

    Args:
        medications: List of medications to check

    Returns:
        Drug interaction results including:
        - interactions: List of interactions
        - severity_levels: Severity of each interaction
        - management_recommendations: How to manage interactions
    """
    logger.info(f"Checking drug interactions for {len(medications)} medications")

    async with MedicationCheckingHTTPClient(
        base_url=MEDICATION_SERVICE_URL,
        api_key=MEDICATION_SERVICE_API_KEY
    ) as client:
        result = await client.check_drug_interactions(medications)
        logger.info("Drug interaction check completed")
        return result


async def check_contraindications(
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
        Contraindication check results including:
        - absolute_contraindications: Absolute contraindications
        - relative_contraindications: Relative contraindications
        - precautions: Precautionary notes
    """
    logger.info(f"Checking contraindications for: {medication}")

    async with MedicationCheckingHTTPClient(
        base_url=MEDICATION_SERVICE_URL,
        api_key=MEDICATION_SERVICE_API_KEY
    ) as client:
        result = await client.check_contraindications(patient_id, medication, conditions)
        logger.info(f"Contraindication check completed for: {medication}")
        return result


# Tool definitions for MCP server
TOOLS = [
    {
        "name": "check_medication",
        "description": "Check medication for safety including indication match, dosage appropriateness, interactions, and contraindications",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "medication": {
                    "type": "string",
                    "description": "Medication name to check"
                },
                "dosage": {
                    "type": "string",
                    "description": "Dosage information (e.g., '10mg')"
                },
                "frequency": {
                    "type": "string",
                    "description": "Dosing frequency (e.g., 'twice daily')"
                },
                "current_medications": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of current medications for interaction check"
                }
            },
            "required": ["patient_id", "medication"]
        }
    },
    {
        "name": "recommend_drugs",
        "description": "Recommend appropriate drugs based on patient condition, age, and organ function",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "condition": {
                    "type": "string",
                    "description": "Medical condition to treat"
                },
                "severity": {
                    "type": "string",
                    "enum": ["mild", "moderate", "severe"],
                    "description": "Condition severity"
                },
                "patient_age": {
                    "type": "integer",
                    "description": "Patient age in years"
                },
                "renal_function": {
                    "type": "string",
                    "enum": ["normal", "mild_impairment", "moderate_impairment", "severe_impairment"],
                    "description": "Renal function status"
                },
                "hepatic_function": {
                    "type": "string",
                    "description": "Hepatic function status"
                },
                "allergies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of known drug allergies"
                }
            },
            "required": ["patient_id", "condition"]
        }
    },
    {
        "name": "check_drug_interactions",
        "description": "Check for drug-drug interactions between multiple medications",
        "inputSchema": {
            "type": "object",
            "properties": {
                "medications": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of medications to check"
                }
            },
            "required": ["medications"]
        }
    },
    {
        "name": "check_contraindications",
        "description": "Check for medication contraindications based on patient conditions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "medication": {
                    "type": "string",
                    "description": "Medication to check"
                },
                "conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of patient conditions"
                }
            },
            "required": ["patient_id", "medication"]
        }
    }
]

# Tool handlers mapping
TOOL_HANDLERS = {
    "check_medication": check_medication,
    "recommend_drugs": recommend_drugs,
    "check_drug_interactions": check_drug_interactions,
    "check_contraindications": check_contraindications,
}
