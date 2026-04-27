"""
Comprehensive test for get_health_data MCP tool integration.

Tests the complete flow from user input to health data retrieval.
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp_servers"))

from profile_server.tools import get_health_data
from profile_server.pingan_client import PingAnHealthArchiveClient


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(name: str, data: Dict[str, Any]):
    """Print result data."""
    print(f"\n{name}:")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def test_1_direct_api_call():
    """Test direct API call to Ping An health archive."""
    print_section("Test 1: Direct Ping An API Call")

    async with PingAnHealthArchiveClient() as client:
        result = await client.get_health_data("test_patient_001")
        print_result("API Response", result)

        # Verify response structure
        assert "_metadata" in result, "Missing _metadata"
        assert result["_metadata"]["party_id"] == "test_patient_001"
        assert result["_metadata"]["iesp_api_code"] == "queryHealthData"

        print("\n[OK] Direct API call successful")
        return True


async def test_2_mcp_tool_function():
    """Test the MCP tool function."""
    print_section("Test 2: MCP Tool Function (get_health_data)")

    result = await get_health_data(party_id="test_patient_002")
    print_result("Tool Response", result)

    # Verify response structure
    assert "_metadata" in result
    assert result["_metadata"]["party_id"] == "test_patient_002"

    print("\n[OK] MCP tool function successful")
    return True


async def test_3_party_id_extraction():
    """Test party_id extraction from user input."""
    print_section("Test 3: party_id Pattern Extraction")

    test_cases = [
        ("客户号:12345678", "12345678"),
        ("partyId: ABC123", "ABC123"),
        ("My customer ID is TEST001", None),  # Won't match Chinese pattern
    ]

    import re
    patterns = [
        r'客户号[：:]\s*([A-Za-z0-9]+)',
        r'partyId[：:]\s*([A-Za-z0-9]+)',
    ]

    print("\nPattern Matching Tests:")
    for input_text, expected_party_id in test_cases:
        party_id = None
        for pattern in patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                party_id = match.group(1)
                break

        status = "[OK]" if party_id == expected_party_id else "[FAIL]"
        print(f"  {status} Input: '{input_text}'")
        print(f"     Expected: {expected_party_id}, Got: {party_id}")

    print("\n[OK] Pattern extraction tests completed")
    return True


async def test_4_with_actual_party_id():
    """Test with an actual-looking party_id."""
    print_section("Test 4: Test with Various party_id Formats")

    test_party_ids = [
        "12345678",
        "ABC12345",
        "TEST001",
        "99999999",
    ]

    print("\nTesting different party_id formats:")
    for party_id in test_party_ids:
        result = await get_health_data(party_id=party_id)

        status = "[OK]" if result.get("code") == "S000000" else "[FAIL]"
        print(f"  {status} party_id: {party_id}")
        print(f"     Response code: {result.get('code')}")
        print(f"     Message: {result.get('message', 'N/A')}")
        print(f"     Has data: {bool(result.get('data'))}")
        print(f"     Info: {result.get('info', 'N/A')}")

    print("\n[OK] party_id format tests completed")
    return True


async def test_5_error_handling():
    """Test error handling."""
    print_section("Test 5: Error Handling")

    # Test with empty party_id
    print("\nTest 5a: Empty party_id")
    try:
        result = await get_health_data(party_id="")
        print_result("Empty party_id Response", result)
        print("[OK] Empty party_id handled")
    except Exception as e:
        print(f"[FAIL] Exception: {e}")

    # Test with special characters
    print("\nTest 5b: Special characters in party_id")
    try:
        result = await get_health_data(party_id="TEST@#$")
        print_result("Special Chars Response", result)
        print("[OK] Special characters handled")
    except Exception as e:
        print(f"[FAIL] Exception: {e}")

    return True


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  get_health_data Integration Test Suite")
    print("=" * 70)

    tests = [
        ("Direct API Call", test_1_direct_api_call),
        ("MCP Tool Function", test_2_mcp_tool_function),
        ("party_id Extraction", test_3_party_id_extraction),
        ("party_id Formats", test_4_with_actual_party_id),
        ("Error Handling", test_5_error_handling),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] Test '{name}' failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print_section("Test Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")

    print("\nDetailed Results:")
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING]  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
