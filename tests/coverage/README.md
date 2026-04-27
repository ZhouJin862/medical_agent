# Test Coverage

Guidelines and tools for measuring and improving test coverage for the Medical Agent project.

## Overview

Test coverage measures how much of the codebase is exercised by automated tests. The target is **80% overall coverage** with higher targets for critical modules.

## Coverage Targets

| Layer | Target | Notes |
|-------|--------|-------|
| Domain Layer | 90% | Core business logic - highest priority |
| Application Layer | 85% | Application services and orchestration |
| Interface Layer | 80% | API endpoints and controllers |
| Infrastructure Layer | 75% | External integrations, database |

### Module-Level Targets

| Module | Target | Priority |
|--------|--------|----------|
| `domain/shared/` | 95% | Critical - value objects, enums |
| `domain/consultation/` | 90% | Critical - core aggregate |
| `domain/health_plan/` | 90% | Critical - core aggregate |
| `application/services/` | 85% | High - business logic |
| `interface/api/` | 80% | High - user-facing |
| `infrastructure/llm/` | 70% | Medium - external API |
| `infrastructure/database/` | 75% | Medium - data access |

## Running Coverage Tests

### Quick Coverage Check:
```bash
pytest --cov=src --cov-report=term-missing
```

### Full Coverage Report:
```bash
python scripts/check_coverage.py
```

### With HTML Report:
```bash
python scripts/check_coverage.py --html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Custom Threshold:
```bash
python scripts/check_coverage.py --fail-under 85
```

### Branch Coverage:
```bash
pytest --cov=src --cov-branch --cov-report=term-missing
```

### Specific Module Coverage:
```bash
pytest --cov=src/domain --cov-report=term-missing tests/unit/domain/
```

### Exclude Files from Coverage:
Add to `.coveragerc` or `pytest.ini`:
```ini
[coverage:run]
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */migrations/*
```

## Coverage Tools

### pytest-cov
Coverage plugin for pytest.

```bash
pip install pytest-cov
```

### coverage.py
Standalone coverage tool.

```bash
pip install coverage
coverage run -m pytest
coverage report
coverage html
```

## Interpreting Coverage Reports

### Terminal Output
```
Name                                         Stmts   Miss  Cover   Missing
------------------------------------------------------------------------
src/domain/shared/value_objects.py             45      3    93%   23-27
src/application/services/chat_service.py      120     25    79%   45-50, 78-92
src/interface/api/routes/chat.py               80     20    75%   34-40, 67
------------------------------------------------------------------------
TOTAL                                          245     48    80%
```

**Columns:**
- `Stmts`: Total statements
- `Miss`: Statements not executed
- `Cover`: Coverage percentage
- `Missing`: Line numbers not covered

### HTML Report
Interactive HTML report shows:
- File-by-file breakdown
- Color-coded coverage
- Line-by-line highlighting
- Missing lines highlighted in red

## Improving Coverage

### 1. Identify Gaps

**Use terminal output to find missing lines:**
```bash
pytest --cov=src --cov-report=term-missing
```

**Use HTML report for detailed analysis:**
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### 2. Prioritize

**High Priority:**
- Critical business logic (domain layer)
- Error handling paths
- Edge cases and boundary conditions
- Security-related code

**Medium Priority:**
- Application services
- API controllers
- Data access code

**Low Priority:**
- Simple getters/setters
- Trivial wrapper functions
- Third-party integrations (use mocks)

### 3. Write Tests

**For Missing Lines:**

```python
# Example: Testing error path
@pytest.mark.asyncio
async def test_chat_send_invalid_request():
    """Test chat send with invalid request."""
    response = await client.post(
        "/api/chat/send",
        json={"message": ""},  # Empty message
    )
    assert response.status_code == 400
```

**For Branch Coverage:**

```python
# Example: Testing both branches
@pytest.mark.asyncio
async def test_hypertension_assessment_normal():
    """Test normal blood pressure assessment."""
    result = await assess_hypertension(120, 80)
    assert result.level == "normal"

@pytest.mark.asyncio
async def test_hypertension_assessment_elevated():
    """Test elevated blood pressure assessment."""
    result = await assess_hypertension(135, 88)
    assert result.level == "elevated"
```

**For Edge Cases:**

```python
# Example: Boundary conditions
@pytest.mark.parametrize("value,expected", [
    (119, "low"),      # Just below threshold
    (120, "normal"),   # Exactly at threshold
    (121, "normal"),   # Just above threshold
])
async def test_blood_pressure_boundary(value, expected):
    """Test blood pressure threshold boundaries."""
    result = assess_blood_pressure(value, 80)
    assert result.category == expected
```

### 4. Use Coverage Guides

**Generate improvement guidelines:**
```bash
python scripts/check_coverage.py --guidelines
```

**Show module targets:**
```bash
python scripts/check_coverage.py --targets
```

## Common Coverage Issues

### Issue: Low Coverage in Error Handlers

**Problem:** Error paths rarely tested.

**Solution:**
```python
@pytest.mark.asyncio
async def test_database_connection_error():
    """Test handling of database connection error."""
    # Mock database to raise connection error
    with mock.patch("get_db_session", side_effect=ConnectionError):
        response = await client.post("/api/chat/send", json={...})
        assert response.status_code == 503
```

### Issue: External Dependencies

**Problem:** Can't test code that calls external APIs.

**Solution:** Use mocks to simulate external responses:
```python
@pytest.mark.asyncio
async def test_llm_service_error(mock_llm):
    """Test handling of LLM service error."""
    mock_llm.generate.side_effect = TimeoutError
    result = await skill.execute(input_data)
    assert result.success is False
    assert result.error == "LLM timeout"
```

### Issue: Complex Conditional Logic

**Problem:** Many branches make coverage difficult.

**Solution:** Use parameterized tests:
```python
@pytest.mark.parametrize("a,b,c,expected", [
    (1, 2, 3, 6),    # All positive
    (-1, 2, 3, 4),   # One negative
    (0, 0, 0, 0),    # All zeros
])
def test_calculate(a, b, c, expected):
    """Test calculate with various inputs."""
    assert calculate(a, b, c) == expected
```

## Coverage in CI/CD

### GitHub Actions Example

```yaml
name: Coverage

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python: '3.11'
      - run: pip install -e ".[test]"
      - run: pytest --cov=src --cov-report=xml --cov-report=term
      - uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest --cov=src --cov-fail-under=80
if [ $? -ne 0 ]; then
    echo "Coverage below 80%. Commit aborted."
    exit 1
fi
```

## Best Practices

1. **Focus on Quality Over Quantity**
   - meaningful tests > high coverage
   - Test behavior, not implementation
   - Maintain test readability

2. **Regular Checks**
   - Run coverage before commits
   - Track coverage trends
   - Set minimum thresholds

3. **Address Gaps Systematically**
   - Prioritize critical code
   - Focus on untested branches
   - Test error conditions

4. **Use Appropriate Test Types**
   - Unit tests for pure functions
   - Integration tests for components
   - E2E tests for critical flows

5. **Review and Refactor**
   - Remove duplicate tests
   - Consolidate similar tests
   - Improve test clarity

## Coverage vs Quality

Remember: Coverage is a tool, not a goal.

✅ **Good Coverage:**
- Tests meaningful behavior
- Covers edge cases
- Tests error conditions
- Maintains readability

❌ **Bad Coverage:**
- Tests implementation details
- Asserts without verification
- Fragile, breaking often
- Hard to understand

## Resources

- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/)
