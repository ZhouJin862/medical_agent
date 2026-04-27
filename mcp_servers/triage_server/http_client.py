"""
HTTP client for calling triage guidance Java service.

Provides HTTP client functionality to communicate with the
external triage guidance system.
"""
import asyncio
import logging
from typing import Any, Dict, Optional, List
import json

import httpx

logger = logging.getLogger(__name__)


class TriageGuidanceHTTPClient:
    """
    HTTP client for triage guidance system.

    Communicates with the Java triage guidance service to retrieve
    hospital recommendations, department recommendations, and doctor recommendations.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL of the triage guidance service
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

    async def get_hospitals(
        self,
        patient_id: str,
        severity: str = "moderate",
        location: Optional[str] = None,
        radius_km: int = 50
    ) -> Dict[str, Any]:
        """
        Get hospital recommendations from triage system.

        Args:
            patient_id: Patient identifier
            severity: Severity level
            location: Patient location
            radius_km: Search radius

        Returns:
            Hospital recommendations data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            params = {
                "severity": severity,
                "radius_km": radius_km
            }
            if location:
                params["location"] = location

            response = await self._client.get(
                f"/api/triage/hospitals/{patient_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get hospitals: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def get_departments(
        self,
        patient_id: str,
        symptoms: Optional[List[str]] = None,
        diagnosis: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get department recommendations from triage system.

        Args:
            patient_id: Patient identifier
            symptoms: List of symptoms
            diagnosis: Patient diagnosis

        Returns:
            Department recommendations data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {}
            if symptoms:
                body["symptoms"] = symptoms
            if diagnosis:
                body["diagnosis"] = diagnosis

            response = await self._client.post(
                f"/api/triage/departments/{patient_id}",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get departments: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def get_doctors(
        self,
        patient_id: str,
        department: str,
        specialty: Optional[str] = None,
        need_expert: bool = False
    ) -> Dict[str, Any]:
        """
        Get doctor recommendations from triage system.

        Args:
            patient_id: Patient identifier
            department: Target department
            specialty: Doctor specialty
            need_expert: Whether to recommend experts

        Returns:
            Doctor recommendations data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            params = {
                "department": department,
                "need_expert": need_expert
            }
            if specialty:
                params["specialty"] = specialty

            response = await self._client.get(
                f"/api/triage/doctors/{patient_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get doctors: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def get_triage_advice(
        self,
        patient_id: str,
        symptoms: List[str],
        urgency_assessment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get triage advice from triage system.

        Args:
            patient_id: Patient identifier
            symptoms: List of symptoms
            urgency_assessment: Urgency assessment

        Returns:
            Triage advice data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {
                "symptoms": symptoms
            }
            if urgency_assessment:
                body["urgency_assessment"] = urgency_assessment

            response = await self._client.post(
                f"/api/triage/advice/{patient_id}",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get triage advice: {e}")
            return {"error": str(e), "patient_id": patient_id}
