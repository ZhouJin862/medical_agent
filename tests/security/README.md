# Security Tests

Security testing suite for the Medical Agent API to verify protection against common vulnerabilities and ensure data privacy.

## Overview

Security tests verify that the application properly handles:
- Input validation and sanitization
- Data privacy and protection
- Authentication and authorization
- Common attack vectors

## Running Tests

### Run all security tests:
```bash
pytest -m security tests/security/
```

### Run specific test category:
```bash
# Input validation tests
pytest tests/security/test_input_validation.py

# Data privacy tests
pytest tests/security/test_data_privacy.py

# Authentication tests
pytest tests/security/test_authentication.py
```

### Run with verbose output:
```bash
pytest -m security -vv tests/security/
```

## Test Categories

### 1. Input Validation (`test_input_validation.py`)

Tests that verify user inputs are properly validated and sanitized.

#### Tests Included:
- `test_sql_injection_prevention` - SQL injection attempts blocked
- `test_xss_prevention` - XSS payloads sanitized
- `test_path_traversal_prevention` - Path traversal blocked
- `test_command_injection_prevention` - Command injection blocked
- `test_ldap_injection_prevention` - LDAP injection blocked
- `test_html_entity_encoding` - Special characters encoded
- `test_input_length_limits` - Long inputs rejected
- `test_json_payload_limits` - Large payloads rejected
- `test_unexpected_content_type` - Wrong content types rejected
- `test_malformed_json` - Malformed JSON rejected
- `test_unicode_normalization_issues` - Unicode attacks prevented

### 2. Data Privacy (`test_data_privacy.py`)

Tests that verify sensitive patient data is properly protected.

#### Tests Included:
- `test_sensitive_data_not_in_errors` - No sensitive data in errors
- `test_patient_data_isolation` - Users can't access others' data
- `test_no_sensitive_data_in_logs` - Sensitive data not logged
- `test_password_field_not_exposed` - Passwords not in responses
- `test_medical_data_redaction` - Medical data properly redacted
- `test_health_data_encrypted_in_storage` - Data encrypted at rest
- `test_minimal_data_exposure` - Only necessary data returned
- `test_error_messages_dont_leak_info` - No stack traces in errors
- `test_session_data_cleanup` - Sessions properly cleaned up
- `test_audit_trail_for_sensitive_operations` - Audit trail maintained
- `test_data_retention_policy` - Old data handled per policy

### 3. Authentication (`test_authentication.py`)

Tests that verify authentication and authorization mechanisms.

#### Tests Included:
- `test_protected_endpoint_requires_auth` - Protected endpoints require auth
- `test_invalid_token_rejected` - Invalid tokens rejected
- `test_csrf_protection` - CSRF protection in place
- `test_rate_limiting` - Rate limiting prevents abuse
- `test_authorization_checks` - Authorization enforced
- `test_session_hijacking_protection` - Sessions protected
- `test_password_security` - Passwords handled securely
- `test_token_expiration` - Tokens expire appropriately
- `test_privilege_escalation_prevention` - Can't escalate privileges
- `test_http_method_security` - Unsafe methods protected
- `test_security_headers` - Security headers present

## Security Checklist

### Input Validation
- [x] SQL injection prevention
- [x] XSS prevention
- [x] Path traversal prevention
- [x] Command injection prevention
- [x] LDAP injection prevention
- [x] Input length limits
- [x] Content-type validation
- [x] Unicode handling

### Data Privacy
- [x] No sensitive data in errors
- [x] Patient data isolation
- [x] No sensitive data in logs
- [x] Passwords not exposed
- [x] Minimal data exposure
- [x] Error message sanitization

### Authentication & Authorization
- [ ] Protected endpoint authentication (when implemented)
- [ ] Token validation (when implemented)
- [ ] CSRF protection (when implemented)
- [ ] Rate limiting (when implemented)
- [ ] Authorization checks (when implemented)
- [ ] Session security

### Infrastructure
- [ ] HTTPS enforcement
- [ ] Security headers
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Audit logging

## Common Vulnerabilities Tested

### OWASP Top 10 Coverage

| Vulnerability | Tests | Status |
|--------------|-------|--------|
| A01: Broken Access Control | Authorization tests | ⚠️ Pending auth implementation |
| A02: Cryptographic Failures | Encryption tests | ⚠️ Pending implementation |
| A03: Injection | Input validation tests | ✅ Covered |
| A04: Insecure Design | Security architecture | ✅ Covered |
| A05: Security Misconfiguration | Headers, config | ✅ Covered |
| A06: Vulnerable Components | Dependency scanning | ❌ Not covered |
| A07: Auth Failures | Authentication tests | ⚠️ Pending auth implementation |
| A08: Data Integrity Failures | Input validation | ✅ Covered |
| A09: Logging Failures | Data privacy tests | ✅ Covered |
| A10: SSRF | External request tests | ⚠️ Needs more coverage |

## Security Best Practices

### 1. Defense in Depth
- Multiple layers of security
- Fail securely
- Validate at every layer

### 2. Principle of Least Privilege
- Minimal required access
- Time-limited permissions
- Audit all access

### 3. Data Minimization
- Collect only necessary data
- Return only necessary data
- Redact sensitive information

### 4. Secure Defaults
- Secure by default
- Explicit opt-in for risk
- No insecure shortcuts

## Adding Security Tests

To add a new security test:

1. **Identify the vulnerability type** (input validation, data privacy, auth)
2. **Create test function** with `@pytest.mark.security` decorator
3. **Test both success and failure cases**
4. **Verify no information leakage**
5. **Document the security concern**

Example:
```python
@pytest.mark.security
@pytest.mark.asyncio
async def test_new_security_concern():
    """
    Security Test: Description of security concern.

    Verifies that [specific security measure] is properly implemented.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt to exploit vulnerability
        response = await client.post("/api/endpoint", json={...})

        # Verify protection is in place
        assert response.status_code in [400, 401, 403, 404], \
            "Vulnerability not protected"

        # Verify no information leakage
        if response.status_code != 200:
            assert "sensitive" not in response.text.lower()
```

## Security Testing Tools

### Recommended Tools

1. **OWASP ZAP** - Web application security scanner
2. **Burp Suite** - Web application testing
3. **SQLMap** - SQL injection testing
4. **Bandit** - Python security linter
5. **Safety** - Dependency vulnerability scanner

### Running Bandit (Python Security Linter)
```bash
pip install bandit
bandit -r src/
```

### Running Safety (Dependency Scanner)
```bash
pip install safety
safety check
```

## Continuous Integration

Security tests should run in CI/CD pipeline:

1. **Every Pull Request** - Run security tests
2. **Nightly** - Full security scan
3. **Before Release** - Comprehensive security audit
4. **After Changes** - Security impact assessment

## Security Reporting

If you discover a security vulnerability:

1. **Do NOT** create a public issue
2. **DO** contact the security team privately
3. **Include** steps to reproduce
4. **Allow** time for fix before disclosure

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Security Headers](https://securityheaders.com/)
