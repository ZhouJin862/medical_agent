# End-to-End (E2E) Tests

Complete end-to-end test suite for the Medical Agent system.

## Overview

E2E tests verify complete user journeys through the entire system, from initial query through assessment, recommendations, and follow-up planning.

## Test Scenarios

### 1. Complete Hypertension Consultation (`test_complete_hypertension_consultation`)
- User asks about hypertension assessment
- System retrieves patient data
- System performs blood pressure assessment
- System provides cardiovascular risk evaluation
- System gives lifestyle recommendations

### 2. Diabetes Risk Assessment (`test_complete_diabetes_risk_assessment`)
- User asks about diabetes risk
- System retrieves blood glucose data
- System performs diabetes risk evaluation
- System provides prevention recommendations

### 3. Comprehensive Health Check (`test_comprehensive_health_check_flow`)
- User requests comprehensive health assessment
- System evaluates all four-highs risks
- System provides integrated health report
- System gives prioritized recommendations

### 4. Treatment Recommendation (`test_treatment_recommendation_flow`)
- User asks for treatment recommendations
- System provides lifestyle modifications
- System suggests follow-up schedule
- System offers medication consultation if needed

### 5. Medication Interaction Check (`test_medication_interaction_check_flow`)
- User asks about medication interactions
- System checks for drug interactions
- System provides safety recommendations

### 6. Follow-up and Monitoring Plan (`test_follow_up_and_monitoring_plan_flow`)
- User completes initial assessment
- System generates follow-up schedule
- System sets monitoring alerts
- System provides reminder templates

### 7. Multi-turn Conversation (`test_multi_turn_conversation_flow`)
- User asks initial question
- System asks for clarification
- User provides more details
- System provides comprehensive answer

### 8. Health Plan Generation (`test_health_plan_generation_flow`)
- User requests personalized health plan
- System generates comprehensive plan
- Plan includes diet, exercise, medication sections
- Plan is stored and retrievable

### 9. Error Recovery (`test_error_recovery_flow`)
- System encounters an error during processing
- System gracefully handles the error
- User receives helpful error message
- System logs the error for debugging

### 10. Session Persistence (`test_session_persistence_across_interactions`)
- User starts a consultation session
- User sends multiple related messages
- System maintains context across messages
- Session history is preserved

### 11. Skill Routing (`test_skill_routing_to_correct_assessment`)
- User asks about specific disease (hypertension, diabetes, etc.)
- System routes to appropriate skill
- System returns domain-specific assessment
- Assessment matches the domain expertise

## Running Tests

### Run all E2E tests:
```bash
pytest -m e2e tests/e2e/
```

### Run specific test file:
```bash
pytest tests/e2e/test_complete_consultation_flow.py
```

### Run with coverage:
```bash
pytest -m e2e --cov=src --cov-report=html tests/e2e/
```

### Run with verbose output:
```bash
pytest -m e2e -vv tests/e2e/
```

### Run using the provided script:
```bash
python scripts/run_e2e_tests.py
```

With coverage:
```bash
python scripts/run_e2e_tests.py --coverage
```

Specific test file:
```bash
python scripts/run_e2e_tests.py --file tests/e2e/test_complete_consultation_flow.py
```

## Test Fixtures

The E2E tests use the following fixtures from `conftest.py`:

- `mock_external_services`: Mock MCP clients (profile, triage, medication, service)
- `e2e_test_client`: HTTP client using ASGITransport
- `sample_e2e_scenarios`: Predefined test scenarios
- `patient_profiles`: Sample patient data
- `conversation_turns`: Multi-turn conversation data
- `assert_e2e_response`: Response validation helper
- `e2e_test_logger`: Test execution logger

## Test Data

Test data includes:

- Patient profiles for various conditions:
  - Healthy adult
  - Hypertension grade 1
  - Diabetes pre-diabetes
  - Metabolic syndrome

- Vital signs ranges:
  - Blood pressure (systolic/diastolic)
  - Blood glucose (fasting, HbA1c)
  - Lipid profile (TC, LDL-C, HDL-C, triglycerides)
  - Uric acid
  - BMI

- Multi-turn conversation scenarios

## Expected Behavior

Each E2E test verifies:

1. **Response Structure**: Valid JSON with required fields
2. **Intent Classification**: Correct intent recognition
3. **Content Quality**: Response contains expected keywords
4. **Error Handling**: Graceful error recovery
5. **Session Management**: Context persistence across turns
6. **Skill Routing**: Correct domain-specific routing

## Test Isolation

E2E tests use mocked external services to ensure:
- No dependency on running MCP servers
- Consistent test data
- Fast execution
- Predictable results

## Adding New Tests

To add a new E2E test:

1. Create test function with `@pytest.mark.e2e` decorator
2. Use `e2e_test_client` fixture for HTTP requests
3. Use `mock_external_services` for external service mocking
4. Verify response structure and content
5. Add documentation to this README

Example:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_new_feature_flow(e2e_test_client):
    """Test new feature end-to-end."""
    response = await e2e_test_client.post(
        "/api/chat/send",
        json={
            "message": "Test query",
            "patient_id": "test-patient",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # Verify response...
```

## Continuous Integration

E2E tests should run in CI/CD pipeline with:
- Separate stage for E2E tests (after unit/integration tests)
- Longer timeout (30s per test)
- Mocked external services
- Coverage reporting

## Troubleshooting

### Test timeout:
- Increase timeout in fixture if needed
- Check for blocking I/O operations
- Verify mock responses are correct

### Unexpected responses:
- Check LLM mock configuration
- Verify skill routing logic
- Review agent state transitions

### Session not persisting:
- Verify consultation_id is passed
- Check session manager implementation
- Review context retrieval logic
