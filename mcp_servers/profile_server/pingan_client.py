"""
HTTP client for Ping An health archive API.

Provides HTTP client functionality to communicate with the
Ping An health archive system for patient health data.
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class PingAnHealthArchiveClient:
    """
    HTTP client for Ping An health archive system.

    Communicates with the Ping An health archive API to retrieve
    patient health data using OAuth2 authentication.
    """

    # API Configuration
    BASE_URL = "https://test-api.pingan.com.cn:20443"
    TOKEN_URL = f"{BASE_URL}/oauth/oauth2/access_token"
    DATA_URL = f"{BASE_URL}/open/appsvr/health/ehis/iesp/purveyor/postWithJson.do"

    # OAuth Credentials
    CLIENT_ID = "P_MHIS-YEDI-FRONT"
    CLIENT_SECRET = "9x86SUzf"
    IESP_ACCESS_ID = "1abc"
    IESP_API_CODE = "queryHealthData"

    def __init__(self, timeout: int = 30):
        """
        Initialize the Ping An API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=False  # Disable SSL verification for test environment
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def _get_access_token(self) -> str:
        """
        Get OAuth2 access token.

        Returns:
            Access token string

        Raises:
            RuntimeError: If token request fails
        """
        # Check if we have a valid cached token
        if self._access_token and self._token_expiry:
            if time.time() < self._token_expiry:
                return self._access_token

        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            params = {
                "client_id": self.CLIENT_ID,
                "grant_type": "client_credentials",
                "client_secret": self.CLIENT_SECRET
            }

            logger.info(f"Requesting access token from {self.TOKEN_URL}")
            response = await self._client.get(self.TOKEN_URL, params=params)
            response.raise_for_status()

            token_data = response.json()

            # Ping An API returns nested response: {ret, msg, data: {access_token, expires_in}}
            if token_data.get("ret") == "0" and "data" in token_data:
                data = token_data["data"]
                self._access_token = data.get("access_token")
                expires_in = int(data.get("expires_in", 3600))
            else:
                # Fallback to standard OAuth2 response format
                self._access_token = token_data.get("access_token")
                expires_in = int(token_data.get("expires_in", 3600))

            self._token_expiry = time.time() + expires_in - 60  # Refresh 1 minute early

            logger.info(f"Successfully obtained access token: {self._access_token[:10]}... (expires in {expires_in}s)")
            return self._access_token

        except httpx.HTTPError as e:
            logger.error(f"Failed to get access token: {e}")
            raise RuntimeError(f"Failed to obtain access token: {e}")

    async def get_health_data(self, party_id: str) -> Dict[str, Any]:
        """
        Get patient health data from Ping An health archive.

        Args:
            party_id: Patient/customer identifier (partyId)

        Returns:
            Health data dictionary containing patient information

        Raises:
            RuntimeError: If request fails
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        request_id = str(int(time.time() * 1000))

        try:
            # Get access token
            access_token = await self._get_access_token()

            # Prepare request
            params = {
                "iespAccessId": self.IESP_ACCESS_ID,
                "iespApiCode": self.IESP_API_CODE,
                "access_token": access_token,
                "request_id": request_id
            }

            body = {"partyId": party_id}

            logger.info(f"Querying health data for party_id: {party_id}")

            response = await self._client.post(
                self.DATA_URL,
                params=params,
                json=body
            )
            response.raise_for_status()

            api_response = response.json()
            logger.info(f"Received response for party_id: {party_id}, code={api_response.get('code')}")

            # Ping An API returns: {code, message, success, data}
            # Handle the actual response format
            if api_response.get("success") == True or api_response.get("code") == "S000000":
                # Success - extract the data field
                result = api_response.get("data", {})
                # The data field might be empty if no data found
                if result:
                    result["_api_response"] = {
                        "code": api_response.get("code"),
                        "message": api_response.get("message"),
                        "success": api_response.get("success")
                    }
                else:
                    # Empty data - party_id not found or no data available
                    result = {
                        "info": "No data found for this party_id",
                        "code": api_response.get("code"),
                        "message": api_response.get("message")
                    }
            else:
                # Error response
                result = {
                    "error": api_response.get("message", "Unknown error"),
                    "code": api_response.get("code"),
                    "data": api_response.get("data")
                }

            # Add our metadata
            result["_metadata"] = {
                "party_id": party_id,
                "request_id": request_id,
                "iesp_api_code": self.IESP_API_CODE
            }

            return result

        except httpx.HTTPError as e:
            logger.error(f"Failed to get health data for party_id {party_id}: {e}")
            return {
                "error": str(e),
                "party_id": party_id,
                "_metadata": {
                    "party_id": party_id,
                    "request_id": request_id,
                    "iesp_api_code": self.IESP_API_CODE
                }
            }
