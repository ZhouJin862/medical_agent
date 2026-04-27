# Load Tests

Load testing suite for the Medical Agent API to verify system stability under concurrent user load.

## Overview

Load tests simulate multiple concurrent users making requests to the API to ensure the system can handle expected traffic volumes without significant performance degradation or failures.

## Load Test Scenarios

| Scenario | Users | RPS | Duration | Description |
|----------|-------|-----|----------|-------------|
| **Light** | 10 | 10 | 60s | Basic operational load |
| **Medium** | 50 | 50 | 120s | Normal daily traffic |
| **Heavy** | 100 | 100 | 180s | Peak traffic load |
| **Stress** | 200 | 200 | 300s | Extreme stress test |
| **Sustained** | 50 | Variable | 120s | Extended duration test |
| **Ramp-up** | 0→50 | Variable | 30s | Gradual user increase |

## Load Test Thresholds

| Metric | Minimum | Target |
|--------|---------|--------|
| Success Rate | 99% | 99.5% |
| P50 Response Time | < 1s | < 0.5s |
| P95 Response Time | < 3s | < 2s |
| P99 Response Time | < 5s | < 3s |
| Error Rate | < 1% | < 0.5% |

## Running Tests

### Run all load tests:
```bash
pytest -m load tests/load/
```

### Run specific scenario:
```bash
# Light load only
pytest tests/load/test_load.py::test_light_load

# Medium load only
pytest tests/load/test_load.py::test_medium_load

# Heavy load only
pytest tests/load/test_load.py::test_heavy_load
```

### Run using the provided script:
```bash
# Run all scenarios
python scripts/run_load_tests.py

# Run specific scenario
python scripts/run_load_tests.py light
python scripts/run_load_tests.py medium
python scripts/run_load_tests.py heavy

# Show scenario information
python scripts/run_load_tests.py --info
```

### Run with verbose output:
```bash
pytest -m load -vv -s tests/load/
```

## Test Scenarios

### 1. Light Load (`test_light_load`)
**Configuration:**
- Users: 10
- Spawn Rate: 2 users/second
- Duration: 60 seconds
- Target RPS: 10

**Purpose:** Verify basic functionality under minimal load.

### 2. Medium Load (`test_medium_load`)
**Configuration:**
- Users: 50
- Spawn Rate: 5 users/second
- Duration: 120 seconds
- Target RPS: 50

**Purpose:** Verify system handles normal daily traffic.

### 3. Heavy Load (`test_heavy_load`)
**Configuration:**
- Users: 100
- Spawn Rate: 10 users/second
- Duration: 180 seconds (reduced to 60s for testing)
- Target RPS: 100

**Purpose:** Verify system handles peak traffic without significant degradation.

### 4. Sustained Load (`test_sustained_load`)
**Configuration:**
- Users: 50
- Duration: 120 seconds (extended)

**Purpose:** Verify system stability over extended periods without memory leaks or performance degradation.

### 5. Ramp-up Load (`test_ramp_up_load`)
**Configuration:**
- Max Users: 50
- Ramp Duration: 30 seconds
- Gradual user increase

**Purpose:** Verify system handles gradual increase in load without issues.

## Metrics Reported

Each load test reports the following metrics:

### Overall Metrics
- **Duration**: Total test duration
- **Total Requests**: Number of requests sent
- **Successful Requests**: Number of successful responses (HTTP 200)
- **Failed Requests**: Number of failed responses
- **Success Rate**: Percentage of successful requests
- **Requests/Second**: Actual throughput achieved

### Response Time Metrics
- **Mean**: Average response time
- **Median**: Median response time
- **Min/Max**: Minimum and maximum response times
- **P50**: 50th percentile response time
- **P95**: 95th percentile response time
- **P99**: 99th percentile response time

### Per-Endpoint Metrics
- Request count per endpoint
- Success rate per endpoint
- Response time distribution per endpoint

### Error Metrics
- Error types and counts
- Error rate percentage

## Interpreting Results

### Success Criteria
- ✅ Success rate ≥ 99%
- ✅ P95 response time < 3 seconds
- ✅ Error rate < 1%
- ✅ No significant performance degradation over time

### Warning Signs
- ⚠️ Success rate 95-99%: Degradation beginning
- ⚠️ P95 > 3 seconds: Performance issues
- ⚠️ Increasing error rate: System overload
- ⚠️ Response times increasing: Possible resource exhaustion

### Failure Indicators
- ❌ Success rate < 95%: System overloaded
- ❌ P95 > 5 seconds: Severe performance issues
- ❌ Error rate > 5%: System instability
- ❌ Connection errors: Infrastructure issues

## Troubleshooting

### High Error Rate
**Symptoms:** Many 4xx/5xx errors

**Possible Causes:**
- Database connection pool exhausted
- LLM API rate limits
- Memory exhaustion
- Network issues

**Solutions:**
1. Increase database pool size
2. Add LLM request queuing
3. Implement caching
4. Scale horizontally

### Slow Response Times
**Symptoms:** P95/P99 exceeds thresholds

**Possible Causes:**
- Database query inefficiency
- LLM latency
- CPU bottleneck
- Network latency

**Solutions:**
1. Optimize database queries
2. Add database indexes
3. Implement response caching
4. Use faster LLM models

### Performance Degradation Over Time
**Symptoms:** Response times increase during test

**Possible Causes:**
- Memory leak
- Connection pool exhaustion
- Cache thrashing
- Resource not being released

**Solutions:**
1. Profile memory usage
2. Check connection cleanup
3. Review cache strategy
4. Add resource monitoring

## Continuous Integration

Load tests should run in CI/CD pipeline:

1. **Schedule**: Run nightly or before releases
2. **Baseline Comparison**: Compare against previous runs
3. **Alerting**: Notify on performance degradation > 20%
4. **Historical Tracking**: Store metrics for trend analysis

## Load Test Configuration

Load test scenarios are defined in `load_test_config.py`:

```python
LOAD_TEST_SCENARIOS = {
    LoadLevel.LIGHT: LoadTestScenario(
        name="Light Load",
        users=10,
        spawn_rate=2,
        run_time=60,
        target_rps=10,
        endpoints=[...],
    ),
    # ...
}
```

To customize scenarios:
1. Edit `tests/load/load_test_config.py`
2. Adjust user counts, spawn rates, duration
3. Modify endpoint weights
4. Update thresholds as needed

## Adding New Load Tests

To add a new load test:

1. Create test function with `@pytest.mark.load` decorator
2. Use `run_load_test()` helper with desired `LoadLevel`
3. Verify metrics against thresholds
4. Add documentation to this README

Example:

```python
@pytest.mark.load
@pytest.mark.asyncio
async def test_custom_load_scenario():
    """Custom load test scenario."""
    # Create custom configuration
    metrics = LoadTestMetrics("Custom Scenario")

    # Run test with custom parameters
    # ...

    # Verify results
    summary = metrics.get_summary()
    assert summary["success_rate"] >= 0.99
```

## Best Practices

1. **Start Small**: Begin with light load, gradually increase
2. **Monitor Resources**: Track CPU, memory, database connections
3. **Test Realistic Scenarios**: Mirror actual traffic patterns
4. **Run Multiple Times**: Account for variability
5. **Compare Baselines**: Track performance over time
6. **Test After Changes**: Run after significant code changes

## Related Tests

- **Performance Tests** (`tests/performance/`): Measure response times under low load
- **E2E Tests** (`tests/e2e/`): Verify complete user journeys
- **Integration Tests** (`tests/integration/`): Test component interactions
