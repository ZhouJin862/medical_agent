"""
HTTP client for calling service recommendation Java service.

Provides HTTP client functionality to communicate with the
external service recommendation system.
"""
import asyncio
import logging
from typing import Any, Dict, Optional, List
import json

import httpx

logger = logging.getLogger(__name__)


class ServiceRecommendationHTTPClient:
    """
    HTTP client for service recommendation system.

    Communicates with the Java service recommendation system to provide
    insurance products, health services, and rehabilitation services.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL of the service recommendation service
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def recommend_insurance(
        self,
        patient_id: str,
        diagnosis: Optional[str] = None,
        risk_factors: Optional[List[str]] = None,
        age: Optional[int] = None,
        budget_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Recommend insurance products.

        Args:
            patient_id: Patient identifier
            diagnosis: Patient diagnosis
            risk_factors: Risk factors
            age: Patient age
            budget_level: Budget preference

        Returns:
            Insurance recommendations
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {
                "patient_id": patient_id,
                "budget_level": budget_level
            }
            if diagnosis:
                body["diagnosis"] = diagnosis
            if risk_factors:
                body["risk_factors"] = risk_factors
            if age:
                body["age"] = age

            response = await self._client.post(
                f"/api/services/insurance",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to recommend insurance: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def recommend_health_services(
        self,
        patient_id: str,
        condition: Optional[str] = None,
        health_goals: Optional[List[str]] = None,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recommend health services.

        Args:
            patient_id: Patient identifier
            condition: Medical condition
            health_goals: Health goals
            service_type: Service type filter

        Returns:
            Health service recommendations
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {"patient_id": patient_id}
            if condition:
                body["condition"] = condition
            if health_goals:
                body["health_goals"] = health_goals
            if service_type:
                body["service_type"] = service_type

            response = await self._client.post(
                f"/api/services/health",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to recommend health services: {e}")
            return {"error": str(e), "patient_id": patient_id}

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
            age_group: Age group
            risk_factors: Risk factors

        Returns:
            Checkup package recommendations
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {"patient_id": patient_id}
            if age_group:
                body["age_group"] = age_group
            if risk_factors:
                body["risk_factors"] = risk_factors

            response = await self._client.post(
                f"/api/services/checkup",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to recommend checkup packages: {e}")
            return {"error": str(e), "patient_id": patient_id}

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
            condition: Medical condition
            recovery_stage: Recovery stage

        Returns:
            Rehabilitation recommendations
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {
                "patient_id": patient_id,
                "condition": condition,
                "recovery_stage": recovery_stage
            }

            response = await self._client.post(
                f"/api/services/rehabilitation",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to recommend rehabilitation: {e}")
            return {"error": str(e), "patient_id": patient_id}
