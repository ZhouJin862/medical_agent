# Ping An Health Archive API Integration

## Overview

This document describes the integration with the Ping An health archive API for retrieving patient health data via MCP (Model Context Protocol) tools.

## API Details

### 1. OAuth2 Token API

**Endpoint:** `https://test-api.pingan.com.cn:20443/oauth/oauth2/access_token`

**Method:** GET

**Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| client_id | P_MHIS-YEDI-FRONT | Client identifier |
| grant_type | client_credentials | OAuth2 grant type |
| client_secret | 9x86SUzf | Client secret |

**Response:**
```json
{
  "access_token": "string",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### 2. Health Data Query API

**Endpoint:** `https://test-api.pingan.com.cn:20443/open/appsvr/health/ehis/iesp/purveyor/postWithJson.do`

**Method:** POST

**Query Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| iespAccessId | 1abc | IESP access identifier |
| iespApiCode | queryHealthData | API code for health data query |
| access_token | {token} | OAuth2 access token from token API |
| request_id | {timestamp} | Unique request identifier (current timestamp) |

**Request Body:**
```json
{
  "partyId": "customer_id_here"
}
```

**Response:**
```json
{
  "basic_info": {
    "name": "Patient Name",
    "gender": "M/F",
    "age": 30,
    "id_card": "...",
    "phone": "..."
  },
  "health_indicators": {
    "blood_pressure": "...",
    "blood_glucose": "...",
    "bmi": "..."
  },
  "medical_records": {
    "diagnoses": [...],
    "medications": [...]
  },
  "_metadata": {
    "party_id": "...",
    "request_id": "...",
    "iesp_api_code": "queryHealthData"
  }
}
```

## MCP Tool

### Tool Name: `get_health_data`

**Description:** Get comprehensive patient health data from Ping An health archive system using OAuth2 authentication.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| party_id | string | Yes | Customer/Patient identifier from Ping An system (客户号/partyId) |

**Usage Example:**
```python
result = await get_health_data(party_id="12345678")
```

## Implementation Details

### File Structure
```
mcp_servers/profile_server/
├── pingan_client.py    # Ping An API HTTP client
├── tools.py             # MCP tool definitions (includes get_health_data)
├── main.py              # MCP server entry point
└── http_client.py       # Original health archive client
```

### Key Components

1. **PingAnHealthArchiveClient** (`pingan_client.py`)
   - Handles OAuth2 token management with caching
   - Makes authenticated requests to Ping An API
   - Includes SSL verification disabled for test environment

2. **get_health_data** (`tools.py`)
   - MCP tool function exposed to the agent
   - Uses PingAnHealthArchiveClient to fetch data
   - Returns formatted health data with metadata

3. **Token Management**
   - Tokens are cached until expiry
   - Tokens are refreshed 1 minute before expiry
   - Concurrent requests share the same token

## Configuration

### Environment Variables (Optional)

The following environment variables can be set for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| HEALTH_ARCHIVE_URL | http://localhost:8080 | Original health archive URL |
| HEALTH_ARCHIVE_API_KEY | None | API key for original system |

### Ping An API Configuration

Ping An API credentials are hardcoded in `pingan_client.py` for the test environment:

```python
CLIENT_ID = "P_MHIS-YEDI-FRONT"
CLIENT_SECRET = "9x86SUzf"
IESP_ACCESS_ID = "1abc"
IESP_API_CODE = "queryHealthData"
```

For production, these should be moved to environment variables or secure configuration.

## Error Handling

The client handles errors gracefully:

1. **Token Failure:** Returns error with party_id and metadata
2. **Network Error:** Catches httpx.HTTPError and logs details
3. **Invalid Response:** Returns error structure with context

All errors include the party_id and request metadata for debugging.

## Testing

### Manual Testing

```python
import asyncio
from mcp_servers.profile_server.pingan_client import PingAnHealthArchiveClient

async def test():
    async with PingAnHealthArchiveClient() as client:
        result = await client.get_health_data("12345678")
        print(result)

asyncio.run(test())
```

### MCP Server Testing

Start the profile server:
```bash
python -m mcp_servers.profile_server.main
```

Test the tool via MCP protocol:
```json
{
  "name": "get_health_data",
  "arguments": {
    "party_id": "12345678"
  }
}
```

## Security Notes

1. **SSL Verification:** Currently disabled for test environment (`verify=False`)
2. **Credentials:** Client secret is hardcoded - should be moved to secure storage
3. **Token Caching:** Tokens are stored in memory only
4. **Logging:** Sensitive data should not be logged in production

## Future Enhancements

1. Move credentials to environment variables or secret manager
2. Enable SSL verification for production
3. Add token persistence across restarts
4. Implement retry logic for transient failures
5. Add request/response logging for debugging
6. Support for additional Ping An API endpoints
