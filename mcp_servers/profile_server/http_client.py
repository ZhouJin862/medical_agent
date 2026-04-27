"""
HTTP client for calling health archive Java service.

Provides HTTP client functionality to communicate with the
external health archive system for patient data.
"""
import asyncio
import logging
from typing import Any, Dict, Optional
import json

import httpx

logger = logging.getLogger(__name__)


class HealthArchiveHTTPClient:
    """
    HTTP client for health archive system.

    Communicates with the Java health archive service to retrieve
    patient profile data, vital signs, and medical records.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL of the health archive service
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

    async def get_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient basic profile from health archive system.

        Args:
            patient_id: Patient identifier

        Returns:
            Patient profile data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self._client.get(f"/api/patients/{patient_id}/profile")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get patient profile: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def get_vital_signs(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient vital signs from health archive system.

        Args:
            patient_id: Patient identifier

        Returns:
            Vital signs data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self._client.get(f"/api/patients/{patient_id}/vital-signs")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get vital signs: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def get_medical_records(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient medical records from health archive system.

        Args:
            patient_id: Patient identifier

        Returns:
            Medical records data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self._client.get(f"/api/patients/{patient_id}/medical-records")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get medical records: {e}")
            return {"error": str(e), "patient_id": patient_id}

    async def get_lab_results(self, patient_id: str, test_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get patient lab results from health archive system.

        Args:
            patient_id: Patient identifier
            test_type: Optional test type filter

        Returns:
            Lab results data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            params = {}
            if test_type:
                params["test_type"] = test_type
            response = await self._client.get(
                f"/api/patients/{patient_id}/lab-results",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get lab results: {e}")
            return {"error": str(e), "patient_id": patient_id}
