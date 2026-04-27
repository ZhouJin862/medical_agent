"""
MCP tools for service_server.

Defines MCP tools for service recommendations including insurance,
health services, checkup packages, and rehabilitation.
"""
import logging
from typing import Any, Dict, List, Optional
import os

from .http_client import ServiceRecommendationHTTPClient

logger = logging.getLogger(__name__)

# Get service URL from environment or use default
SERVICE_RECOMMENDATION_URL = os.getenv("SERVICE_RECOMMENDATION_URL", "http://localhost:8083")
SERVICE_RECOMMENDATION_API_KEY = os.getenv("SERVICE_RECOMMENDATION_API_KEY")


async def recommend_insurance(
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
        Insurance recommendations including:
        - chronic_disease_insurance: Chronic disease options
        - critical_illness_insurance: Critical illness options
        - medical_insurance: General medical insurance
        - coverage_details: Coverage information
        - premium_estimates: Cost estimates
    """
    logger.info(f"Recommending insurance for patient: {patient_id}")

    async with ServiceRecommendationHTTPClient(
        base_url=SERVICE_RECOMMENDATION_URL,
        api_key=SERVICE_RECOMMENDATION_API_KEY
    ) as client:
        result = await client.recommend_insurance(
            patient_id, diagnosis, risk_factors, age, budget_level
        )
        logger.info(f"Insurance recommendations completed for patient: {patient_id}")
        return result


async def recommend_health_services(
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
        Health service recommendations including:
        - disease_management_services: Disease management programs
        - health_promotion_services: Health promotion services
        - rehabilitation_services: Rehabilitation programs
        - preventive_services: Preventive care services
        - service_details: Service details and pricing
    """
    logger.info(f"Recommending health services for patient: {patient_id}")

    async with ServiceRecommendationHTTPClient(
        base_url=SERVICE_RECOMMENDATION_URL,
        api_key=SERVICE_RECOMMENDATION_API_KEY
    ) as client:
        result = await client.recommend_health_services(
            patient_id, condition, health_goals, service_type
        )
        logger.info(f"Health service recommendations completed for patient: {patient_id}")
        return result


async def recommend_checkup_packages(
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
        Checkup package recommendations including:
        - basic_package: Basic health checkup
        - comprehensive_package: Comprehensive checkup
        - targeted_packages: Targeted checkups
        - package_contents: Package contents
        - recommended_frequency: How often to get checkups
    """
    logger.info(f"Recommending checkup packages for patient: {patient_id}")

    async with ServiceRecommendationHTTPClient(
        base_url=SERVICE_RECOMMENDATION_URL,
        api_key=SERVICE_RECOMMENDATION_API_KEY
    ) as client:
        result = await client.recommend_checkup_packages(patient_id, age_group, risk_factors)
        logger.info(f"Checkup package recommendations completed for patient: {patient_id}")
        return result


async def recommend_rehabilitation(
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
        Rehabilitation recommendations including:
        - cardiac_rehabilitation: Cardiac rehab programs
        - pulmonary_rehabilitation: Pulmonary rehab programs
        - physical_therapy: Physical therapy options
        - exercise_programs: Exercise programs
        - service_providers: Service providers
    """
    logger.info(f"Recommending rehabilitation for patient: {patient_id}, condition: {condition}")

    async with ServiceRecommendationHTTPClient(
        base_url=SERVICE_RECOMMENDATION_URL,
        api_key=SERVICE_RECOMMENDATION_API_KEY
    ) as client:
        result = await client.recommend_rehabilitation(patient_id, condition, recovery_stage)
        logger.info(f"Rehabilitation recommendations completed for patient: {patient_id}")
        return result


# Tool definitions for MCP server
TOOLS = [
    {
        "name": "recommend_insurance",
        "description": "Recommend insurance products based on patient diagnosis, risk factors, and budget",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "diagnosis": {
                    "type": "string",
                    "description": "Patient diagnosis"
                },
                "risk_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of risk factors"
                },
                "age": {
                    "type": "integer",
                    "description": "Patient age"
                },
                "budget_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Budget preference"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "recommend_health_services",
        "description": "Recommend health services based on patient condition and health goals",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "condition": {
                    "type": "string",
                    "description": "Medical condition"
                },
                "health_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of health goals"
                },
                "service_type": {
                    "type": "string",
                    "description": "Specific service type filter"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "recommend_checkup_packages",
        "description": "Recommend health checkup packages based on age and risk factors",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "age_group": {
                    "type": "string",
                    "enum": ["young", "middle", "senior"],
                    "description": "Age group"
                },
                "risk_factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of risk factors"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "recommend_rehabilitation",
        "description": "Recommend rehabilitation services based on condition and recovery stage",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier"
                },
                "condition": {
                    "type": "string",
                    "description": "Medical condition requiring rehab"
                },
                "recovery_stage": {
                    "type": "string",
                    "enum": ["acute", "subacute", "stable"],
                    "description": "Stage of recovery"
                }
            },
            "required": ["patient_id", "condition"]
        }
    }
]

# Tool handlers mapping
TOOL_HANDLERS = {
    "recommend_insurance": recommend_insurance,
    "recommend_health_services": recommend_health_services,
    "recommend_checkup_packages": recommend_checkup_packages,
    "recommend_rehabilitation": recommend_rehabilitation,
}
