"""
Test script for Ping An Health Archive API integration.

Tests the OAuth2 token retrieval and health data query functionality.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp_servers"))

from mcp_servers.profile_server.pingan_client import PingAnHealthArchiveClient


async def test_token_retrieval():
    """Test OAuth2 token retrieval."""
    print("\n=== Test 1: Token Retrieval ===")

    async with PingAnHealthArchiveClient() as client:
        try:
            token = await client._get_access_token()
            print(f"Status: SUCCESS")
            print(f"Token obtained: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
            print(f"Token expires at: {client._token_expiry}")
            return True
        except Exception as e:
            print(f"Status: FAILED")
            print(f"Error: {e}")
            return False


async def test_health_data_query(party_id: str = "test_patient_001"):
    """Test health data query."""
    print(f"\n=== Test 2: Health Data Query (party_id: {party_id}) ===")

    async with PingAnHealthArchiveClient() as client:
        try:
            result = await client.get_health_data(party_id)
            print(f"Status: Query completed")

            # Check for errors
            if "error" in result:
                print(f"Response contains error (expected for test party_id)")
                print(f"Error: {result.get('error')}")
                print(f"Metadata: {result.get('_metadata', {})}")
            else:
                print(f"Data keys: {list(result.keys())}")

                # Print sample data
                if "basic_info" in result:
                    print(f"Basic Info: {result['basic_info']}")
                if "health_indicators" in result:
                    print(f"Health Indicators keys: {list(result['health_indicators'].keys())}")

                if "_metadata" in result:
                    print(f"Metadata: {result['_metadata']}")

            return True
        except Exception as e:
            print(f"Status: FAILED")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_token_caching():
    """Test token caching functionality."""
    print("\n=== Test 3: Token Caching ===")

    async with PingAnHealthArchiveClient() as client:
        try:
            # First token request
            print("First token request...")
            token1 = await client._get_access_token()
            expiry1 = client._token_expiry

            print(f"Token 1: {token1[:20]}...")
            print(f"Expiry 1: {expiry1}")

            # Second token request (should use cached token)
            print("\nSecond token request (should use cache)...")
            token2 = await client._get_access_token()
            expiry2 = client._token_expiry

            print(f"Token 2: {token2[:20]}...")
            print(f"Expiry 2: {expiry2}")

            # Verify tokens are the same (cached)
            # Note: expiry may be recalculated but token should be the same
            if token1 == token2:
                print("Status: SUCCESS - Token caching works correctly (same token returned)")
                return True
            else:
                print("Status: FAILED - Tokens are different (caching not working)")
                print(f"  Token 1: {token1}")
                print(f"  Token 2: {token2}")
                return False

        except Exception as e:
            print(f"Status: FAILED")
            print(f"Error: {e}")
            return False


async def test_mcp_tool():
    """Test the MCP tool function."""
    print("\n=== Test 4: MCP Tool Function ===")

    from mcp_servers.profile_server.tools import get_health_data

    try:
        result = await get_health_data(party_id="test_patient_001")
        print(f"Status: MCP tool executed")
        print(f"Result keys: {list(result.keys())}")
        print(f"Metadata: {result.get('_metadata', {})}")
        return True
    except Exception as e:
        print(f"Status: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_client_config():
    """Print client configuration."""
    print("\n=== Client Configuration ===")
    print(f"BASE_URL: {PingAnHealthArchiveClient.BASE_URL}")
    print(f"TOKEN_URL: {PingAnHealthArchiveClient.TOKEN_URL}")
    print(f"DATA_URL: {PingAnHealthArchiveClient.DATA_URL}")
    print(f"CLIENT_ID: {PingAnHealthArchiveClient.CLIENT_ID}")
    print(f"CLIENT_SECRET: {'*' * len(PingAnHealthArchiveClient.CLIENT_SECRET)}")
    print(f"IESP_ACCESS_ID: {PingAnHealthArchiveClient.IESP_ACCESS_ID}")
    print(f"IESP_API_CODE: {PingAnHealthArchiveClient.IESP_API_CODE}")


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Ping An Health Archive API Integration Tests")
    print("=" * 60)

    print_client_config()

    results = []

    # Run tests
    results.append(await test_token_retrieval())
    results.append(await test_health_data_query("test_patient_001"))
    results.append(await test_token_caching())
    results.append(await test_mcp_tool())

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\nAll tests PASSED!")
        return 0
    else:
        print(f"\n{failed} test(s) FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
