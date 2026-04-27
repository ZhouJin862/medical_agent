"""
Input validation and sanitization tests.

Verify that user inputs are properly validated and sanitized
to prevent injection attacks and other security vulnerabilities.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.interface.api.main import app


@pytest.mark.security
@pytest.mark.asyncio
async def test_sql_injection_prevention():
    """
    Security Test: SQL injection prevention.

    Verifies that SQL injection attempts are properly handled
    and don't result in database errors or data leaks.
    """
    transport = ASGITransport(app=app)

    sql_injection_payloads = [
        "'; DROP TABLE consultations; --",
        "' OR '1'='1",
        "admin'--",
        "1' UNION SELECT * FROM users--",
        "'; INSERT INTO users VALUES ('hacker', 'password'); --",
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in sql_injection_payloads:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": payload,
                    "patient_id": "security-test-001",
                },
            )

            # Should return valid response (not database error)
            assert response.status_code in [200, 400, 422], \
                f"Unexpected response to SQL injection payload: {payload}"

            # Should not reveal database structure
            if response.status_code == 200:
                data = response.json()
                # Response should not contain error messages about SQL
                response_text = str(data).lower()
                assert "sql" not in response_text or "error" not in response_text, \
                    "SQL error information leaked"


@pytest.mark.security
@pytest.mark.asyncio
async def test_xss_prevention():
    """
    Security Test: XSS prevention.

    Verifies that XSS payloads are properly sanitized
    and don't execute scripts in responses.
    """
    transport = ASGITransport(app=app)

    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(XSS)'>",
        "<body onload=alert('XSS')>",
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in xss_payloads:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": payload,
                    "patient_id": "security-test-002",
                },
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 422]

            if response.status_code == 200:
                data = response.json()
                response_content = str(data).lower()

                # Script tags should be escaped or removed
                # (not executed, and if echoed back, should be safe)
                assert "<script>" not in response_content or \
                    ("<" in response_content and "&lt;" in response_content), \
                    "Unescaped script tag in response"


@pytest.mark.security
@pytest.mark.asyncio
async def test_path_traversal_prevention():
    """
    Security Test: Path traversal prevention.

    Verifies that path traversal attempts are blocked.
    """
    transport = ASGITransport(app=app)

    path_traversal_payloads = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%2fpasswd",
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in path_traversal_payloads:
            # Try path traversal in patient_id
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": "Test message",
                    "patient_id": payload,
                },
            )

            # Should reject invalid patient_id format
            assert response.status_code in [400, 422, 404], \
                f"Path traversal payload not rejected: {payload}"

            # Should not return file contents
            if response.content:
                content = response.content.decode()
                assert "root:" not in content, "File contents leaked via path traversal"


@pytest.mark.security
@pytest.mark.asyncio
async def test_command_injection_prevention():
    """
    Security Test: Command injection prevention.

    Verifies that command injection attempts are blocked.
    """
    transport = ASGITransport(app=app)

    command_injection_payloads = [
        "; cat /etc/passwd",
        "| ls -la",
        "&& whoami",
        "`whoami`",
        "$(whoami)",
        "; rm -rf /",
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in command_injection_payloads:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": payload,
                    "patient_id": "security-test-003",
                },
            )

            # Should handle without executing commands
            assert response.status_code in [200, 400, 422]

            # Response should not contain command output
            if response.status_code == 200:
                data = response.json()
                response_text = str(data)
                # Should not contain typical command outputs
                assert "uid=" not in response_text and "gid=" not in response_text, \
                    "Command output leaked in response"


@pytest.mark.security
@pytest.mark.asyncio
async def test_ldap_injection_prevention():
    """
    Security Test: LDAP injection prevention.

    Verifies that LDAP injection attempts are blocked.
    """
    transport = ASGITransport(app=app)

    ldap_injection_payloads = [
        "*)(uid=*",
        "*)(|(objectClass=*",
        "*))%00",
        "*)(&(password=*",
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in ldap_injection_payloads:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": payload,
                    "patient_id": "security-test-004",
                },
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 422]

            # Should not leak LDAP information
            if response.status_code == 200:
                data = response.json()
                response_text = str(data).lower()
                assert "dn:" not in response_text, "LDAP data leaked"


@pytest.mark.security
@pytest.mark.asyncio
async def test_html_entity_encoding():
    """
    Security Test: HTML entity encoding in outputs.

    Verifies that special characters are properly encoded
    in HTML responses.
    """
    transport = ASGITransport(app=app)

    special_chars = [
        "<>&\"'",
        "<script>",
        "<img>",
        "<iframe>",
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for chars in special_chars:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": f"Test with special chars: {chars}",
                    "patient_id": "security-test-005",
                },
            )

            if response.status_code == 200:
                data = response.json()
                response_content = str(data)

                # Check that special characters are handled safely
                # They should either be encoded or the response should be JSON
                # (which handles encoding automatically)
                for char in ['<', '>', '&', '"', "'"]:
                    # In JSON, these are escaped automatically
                    # This test verifies JSON is being used properly
                    if char in response_content:
                        # If present, should be properly escaped
                        assert "\\" in response_content or char in chars, \
                            f"Unescaped character in response: {char}"


@pytest.mark.security
@pytest.mark.asyncio
async def test_input_length_limits():
    """
    Security Test: Input length limits.

    Verifies that excessively long inputs are rejected.
    """
    transport = ASGITransport(app=app)

    # Very long message (10,000 characters)
    long_message = "A" * 10000

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": long_message,
                "patient_id": "security-test-006",
            },
        )

        # Should reject overly long input
        # (Specific limit depends on your requirements)
        assert response.status_code in [400, 422, 413], \
            "Overly long input was not rejected"


@pytest.mark.security
@pytest.mark.asyncio
async def test_json_payload_limits():
    """
    Security Test: JSON payload size limits.

    Verifies that overly large JSON payloads are rejected.
    """
    transport = ASGITransport(app=app)

    # Create a very large JSON payload
    large_payload = {
        "message": "Test",
        "patient_id": "security-test-007",
        "vital_signs": {
            "blood_pressure": {"systolic": 120, "diastolic": 80},
            "large_data": "X" * 100000,  # Large value
        },
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json=large_payload,
        )

        # Should reject overly large payload
        assert response.status_code in [400, 422, 413], \
            "Overly large JSON payload was not rejected"


@pytest.mark.security
@pytest.mark.asyncio
async def test_unexpected_content_type():
    """
    Security Test: Unexpected content type handling.

    Verifies that requests with unexpected content types
    are handled securely.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try sending text instead of JSON
        response = await client.post(
            "/api/chat/send",
            content="not a json",
            headers={"Content-Type": "text/plain"},
        )

        # Should reject with appropriate error
        assert response.status_code in [400, 415, 422], \
            "Unexpected content type was not rejected"


@pytest.mark.security
@pytest.mark.asyncio
async def test_malformed_json():
    """
    Security Test: Malformed JSON handling.

    Verifies that malformed JSON is rejected gracefully.
    """
    transport = ASGITransport(app=app)

    malformed_json_payloads = [
        '{"message": "test",}',  # Trailing comma
        '{"message": "test"',   # Missing closing brace
        '{message: "test"}',     # Unquoted key
        '{"message": test}',     # Unquoted value
        '{"message": "test"',    # Incomplete
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in malformed_json_payloads:
            response = await client.post(
                "/api/chat/send",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

            # Should reject malformed JSON
            assert response.status_code in [400, 422], \
                f"Malformed JSON was not rejected: {payload}"


@pytest.mark.security
@pytest.mark.asyncio
async def test_unicode_normalization_issues():
    """
    Security Test: Unicode normalization attacks.

    Verifies that Unicode normalization attacks are prevented.
    """
    transport = ASGITransport(app=app)

    # Various Unicode representations that could be used for attacks
    unicode_payloads = [
        "\u003Cscript\u003Ealert('XSS')\u003C/script\u003E",  # Unicode encoded tags
        "\u002F\u002A\u002A",  # Encoded comment
        "admin\u0000",  # Null byte
        "\ufffd" * 100,  # Replacement character spam
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for payload in unicode_payloads:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": payload,
                    "patient_id": "security-test-008",
                },
            )

            # Should handle without security issues
            assert response.status_code in [200, 400, 422]

            # Should not have processing errors
            # that might indicate vulnerability
            if response.status_code == 200:
                data = response.json()
                assert data is not None
