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

    # External API codes
    API_CODE_HUMAN_QUERY = "humanQuery"
    API_CODE_ADD_HUMAN_INFO = "addHumanInfo"
    API_CODE_INSIGHT_SAVE = "insightSave"

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

    async def _call_iesp_api(
        self,
        api_code: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call an IESP API endpoint with OAuth2 authentication.

        Args:
            api_code: The iespApiCode to use (e.g. humanQuery, addHumanInfo, insightSave).
            body: JSON request body.

        Returns:
            Parsed API response dict.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        request_id = str(int(time.time() * 1000))

        try:
            access_token = await self._get_access_token()

            params = {
                "iespAccessId": self.IESP_ACCESS_ID,
                "iespApiCode": api_code,
                "access_token": access_token,
                "request_id": request_id,
            }

            logger.info(f"Calling IESP API: api_code={api_code}, request_id={request_id}")

            response = await self._client.post(
                self.DATA_URL,
                params=params,
                json=body,
            )
            response.raise_for_status()

            api_response = response.json()
            logger.info(f"IESP API response: api_code={api_code}, ret={api_response.get('ret')}, code={api_response.get('code')}")

            return api_response

        except httpx.HTTPError as e:
            logger.error(f"IESP API call failed: api_code={api_code}, error={e}")
            return {"ret": "-1", "code": "-1", "msg": str(e)}

    async def query_human_info(self, party_id: str) -> Optional[Dict[str, Any]]:
        """Query health digital human info via humanQuery API.

        Args:
            party_id: User/patient identifier.

        Returns:
            The ``data`` field from the API response on success, or None on failure.
        """
        resp = await self._call_iesp_api(self.API_CODE_HUMAN_QUERY, {"partyId": party_id})

        if resp.get("ret") == "0" and resp.get("code") == "0":
            data = resp.get("data")
            if data:
                logger.info(f"humanQuery success for party_id={party_id}")
                return data
            else:
                logger.info(f"humanQuery returned empty data for party_id={party_id}")
                return None
        else:
            logger.warning(f"humanQuery failed: ret={resp.get('ret')}, msg={resp.get('msg')}")
            return None

    async def add_human_info(self, payload: Dict[str, Any]) -> bool:
        """Push patient health data via addHumanInfo API.

        Args:
            payload: Full request body matching addHumanInfo schema.

        Returns:
            True if the API returned success, False otherwise.
        """
        resp = await self._call_iesp_api(self.API_CODE_ADD_HUMAN_INFO, payload)

        if resp.get("ret") == "0" and resp.get("code") == "0":
            logger.info(f"addHumanInfo success")
            return True
        else:
            logger.warning(f"addHumanInfo failed: ret={resp.get('ret')}, msg={resp.get('msg')}")
            return False

    async def save_insight(self, payload: Dict[str, Any]) -> bool:
        """Push assessment insight via insightSave API.

        Args:
            payload: Full request body matching insightSave schema.

        Returns:
            True if the API returned success, False otherwise.
        """
        resp = await self._call_iesp_api(self.API_CODE_INSIGHT_SAVE, payload)

        if resp.get("ret") == "0" and resp.get("code") == "0":
            logger.info(f"insightSave success")
            return True
        else:
            logger.warning(f"insightSave failed: ret={resp.get('ret')}, msg={resp.get('msg')}")
            return False
