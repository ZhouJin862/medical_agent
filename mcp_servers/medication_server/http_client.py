"""
HTTP client for calling medication checking Java service.

Provides HTTP client functionality to communicate with the
external medication checking system.
"""
import asyncio
import logging
from typing import Any, Dict, Optional, List
import json

import httpx

logger = logging.getLogger(__name__)


class MedicationCheckingHTTPClient:
    """
    HTTP client for medication checking system.

    Communicates with the Java medication checking service to verify
    medication safety, check interactions, and provide drug recommendations.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8082",
        timeout: int = 30,
        api_key: Optional[str] = None
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL of the medication checking service
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
            medication: Medication name
            dosage: Dosage information
            frequency: Dosing frequency
            current_medications: Current medications for interaction check

        Returns:
            Medication check results
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {
                "patient_id": patient_id,
                "medication": medication
            }
            if dosage:
                body["dosage"] = dosage
            if frequency:
                body["frequency"] = frequency
            if current_medications:
                body["current_medications"] = current_medications

            response = await self._client.post(
                f"/api/medication/check",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to check medication: {e}")
            return {"error": str(e), "medication": medication}

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
            condition: Medical condition
            severity: Condition severity
            patient_age: Patient age
            renal_function: Renal function status
            hepatic_function: Hepatic function status
            allergies: Known allergies

        Returns:
            Drug recommendations
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {
                "patient_id": patient_id,
                "condition": condition,
                "severity": severity
            }
            if patient_age:
                body["patient_age"] = patient_age
            if renal_function:
                body["renal_function"] = renal_function
            if hepatic_function:
                body["hepatic_function"] = hepatic_function
            if allergies:
                body["allergies"] = allergies

            response = await self._client.post(
                f"/api/medication/recommend",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to recommend drugs: {e}")
            return {"error": str(e), "condition": condition}

    async def check_drug_interactions(
        self,
        medications: List[str]
    ) -> Dict[str, Any]:
        """
        Check for drug-drug interactions.

        Args:
            medications: List of medications to check

        Returns:
            Drug interaction results
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            response = await self._client.post(
                f"/api/medication/interactions",
                json={"medications": medications}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to check drug interactions: {e}")
            return {"error": str(e)}

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
            conditions: Patient conditions

        Returns:
            Contraindication check results
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            body = {
                "patient_id": patient_id,
                "medication": medication
            }
            if conditions:
                body["conditions"] = conditions

            response = await self._client.post(
                f"/api/medication/contraindications",
                json=body
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to check contraindications: {e}")
            return {"error": str(e), "medication": medication}
