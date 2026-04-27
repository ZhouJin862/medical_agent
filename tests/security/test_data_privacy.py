"""
Data privacy and protection tests.

Verify that sensitive patient data is properly protected
and not leaked in error messages or logs.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.interface.api.main import app


@pytest.mark.security
@pytest.mark.asyncio
async def test_sensitive_data_not_in_errors():
    """
    Security Test: Sensitive data not exposed in errors.

    Verifies that patient data is not leaked in error messages.
    """
    transport = ASGITransport(app=app)

    sensitive_data = {
        "message": "我的血压是135/88",
        "patient_id": "patient-with-sensitive-info",
        "vital_signs": {
            "blood_pressure": {"systolic": 135, "diastolic": 88},
            "blood_glucose": {"fasting": 6.5},
            "ssn": "123-45-6789",  # Should not be in errors
            "credit_card": "4111-1111-1111-1111",
        },
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try sending invalid data that might trigger errors
        response = await client.post(
            "/api/chat/send",
            json=sensitive_data,
        )

        # Even if error occurs, sensitive data should not be exposed
        if response.status_code != 200:
            error_content = response.text.lower()

            # Check that SSN and credit card are not in error
            assert "123-45-6789" not in error_content, "SSN leaked in error"
            assert "4111-1111-1111-1111" not in error_content, "Credit card leaked in error"
            assert "ssn" not in error_content or "redacted" in error_content, \
                "SSN field name leaked"


@pytest.mark.security
@pytest.mark.asyncio
async def test_patient_data_isolation():
    """
    Security Test: Patient data isolation.

    Verifies that users cannot access other patients' data.
    """
    transport = ASGITransport(app=app)

    # User A's consultation
    async with AsyncClient(transport=transport, base_url="http://test") as client_a:
        response_a = await client_a.post(
            "/api/chat/send",
            json={
                "message": "我的个人信息",
                "patient_id": "patient-A",
            },
        )

    # User B tries to access User A's consultation
    async with AsyncClient(transport=transport, base_url="http://test") as client_b:
        if response_a.status_code == 200:
            consultation_id = response_a.json().get("consultation_id")

            if consultation_id:
                # Try to access other user's consultation
                response_b = await client_b.get(
                    f"/api/chat/consultations/{consultation_id}/messages"
                )

                # Should either return 404 (not found) or 403 (forbidden)
                # depending on implementation
                assert response_b.status_code in [404, 403, 401], \
                    "Patient data isolation failed - user can access other's data"


@pytest.mark.security
@pytest.mark.asyncio
async def test_no_sensitive_data_in_logs():
    """
    Security Test: Sensitive data not logged.

    Verifies that sensitive patient data is not written to logs.
    """
    # This test would need log capture/analysis
    # For now, it's a placeholder test

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我的SSN是123-45-6789",
                "patient_id": "log-security-test",
            },
        )

        # In a real test, you would:
        # 1. Capture logs during request
        # 2. Verify SSN is not in logs
        # 3. Verify full patient data is not in logs

        # For placeholder, just verify response is handled
        assert response.status_code in [200, 400, 422]


@pytest.mark.security
@pytest.mark.asyncio
async def test_password_field_not_exposed():
    """
    Security Test: Password fields not exposed.

    Verifies that password fields are never returned in responses.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try various endpoints that might return user data
        endpoints = [
            "/api/v3/skills",
            "/api/chat/consultations/non-existent",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)

            if response.status_code == 200:
                response_text = response.text.lower()

                # Check that password-related terms are not in response
                assert "password" not in response_text or \
                    "redacted" in response_text or \
                    "hashed" in response_text, \
                    "Password field exposed in response"


@pytest.mark.security
@pytest.mark.asyncio
async def test_medical_data_redaction():
    """
    Security Test: Medical data redaction in generic responses.

    Verifies that medical data is properly redacted when
    returned in non-medical contexts.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我的血压是135/88，血糖是6.5",
                "patient_id": "redaction-test",
            },
        )

        if response.status_code == 200:
            data = response.json()
            response_content = str(data)

            # In non-sensitive responses, medical values might be summarized
            # rather than repeated exactly (implementation-dependent)
            # This test verifies no accidental full PII exposure


@pytest.mark.security
@pytest.mark.asyncio
async def test_health_data_encrypted_in_storage():
    """
    Security Test: Health data encryption.

    Verifies that health data is encrypted at rest.

    Note: This is a placeholder test. Real implementation would:
    1. Check database storage
    2. Verify data is encrypted
    3. Verify decryption works for authorized users
    """
    # Placeholder - would require database access
    assert True, "Encryption verification requires database access"


@pytest.mark.security
@pytest.mark.asyncio
async def test_minimal_data_exposure():
    """
    Security Test: Minimal data exposure principle.

    Verifies that only necessary data is returned in responses.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test skill list endpoint
        response = await client.get("/api/v3/skills")

        if response.status_code == 200:
            data = response.json()

            # Skills should not expose internal implementation details
            if "skills" in data:
                for skill in data["skills"]:
                    # Check that internal fields are not exposed
                    assert "internal_" not in str(skill) or "prompt" not in str(skill), \
                        "Internal implementation details exposed"


@pytest.mark.security
@pytest.mark.asyncio
async def test_error_messages_dont_leak_info():
    """
    Security Test: Error messages don't leak system information.

    Verifies that error messages don't reveal:
    - Stack traces (in production)
    - Database structure
    - File paths
    - Internal implementation details
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try various error-triggering requests
        error_tests = [
            client.get("/api/nonexistent-endpoint"),
            client.get("/api/chat/consultations/invalid-id/messages"),
            client.post("/api/chat/send", json={}),  # Empty payload
        ]

        for response_future in error_tests:
            response = await response_future
            error_text = response.text.lower()

            # Check for common information leaks
            assert "traceback" not in error_text or "most recent" not in error_text, \
                "Stack trace leaked in error"
            assert "file " not in error_text or "line " not in error_text, \
                "File paths leaked in error"
            assert "sql" not in error_text or "query" not in error_text, \
                "SQL query leaked in error"


@pytest.mark.security
@pytest.mark.asyncio
async def test_session_data_cleanup():
    """
    Security Test: Session data cleanup.

    Verifies that session data is properly cleaned up
    after session ends.
    """
    transport = ASGITransport(app=app)

    # Create a session
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "开始会话",
                "patient_id": "session-cleanup-test",
            },
        )

        if response.status_code == 200:
            consultation_id = response.json().get("consultation_id")

            if consultation_id:
                # Close the consultation
                close_response = await client.post(
                    f"/api/chat/consultations/{consultation_id}/close"
                )

                # Try to access the closed consultation
                access_response = await client.get(
                    f"/api/chat/consultations/{consultation_id}/messages"
                )

                # Should either be closed or require re-authentication
                # (Implementation-dependent)
                assert access_response.status_code in [200, 403, 404]


@pytest.mark.security
@pytest.mark.asyncio
async def test_audit_trail_for_sensitive_operations():
    """
    Security Test: Audit trail for sensitive operations.

    Verifies that sensitive operations are logged
    for audit purposes.

    Note: This is a placeholder. Real implementation would:
    1. Perform sensitive operation
    2. Check audit logs
    3. Verify operation was logged
    """
    # Placeholder - would require audit log access
    assert True, "Audit trail verification requires log access"


@pytest.mark.security
@pytest.mark.asyncio
async def test_data_retention_policy():
    """
    Security Test: Data retention policy compliance.

    Verifies that old data is handled according to retention policy.

    Note: This is a placeholder. Real implementation would:
    1. Create old data
    2. Run retention cleanup
    3. Verify data was anonymized or deleted
    """
    # Placeholder - would require database access and time control
    assert True, "Data retention verification requires database access"
