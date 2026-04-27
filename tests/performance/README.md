# Performance Tests

Performance testing suite for the Medical Agent API to ensure response times meet requirements.

## Overview

These tests measure API response times to ensure they meet performance requirements:
- **Simple queries**: < 1 second (p95)
- **Health assessments**: < 2 seconds (p95)
- **Complex workflows**: < 3 seconds (p95)

## Performance Thresholds

| Test Type | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Simple Query | 0.5s | 1.0s | 1.5s |
| Health Assessment | 1.0s | 2.0s | 2.5s |
| Complex Workflow | 1.5s | 3.0s | 4.0s |
| Skill Execution | 0.8s | 1.5s | 2.0s |

## Test Scenarios

### 1. Simple Query Performance (`test_chat_send_simple_query_performance`)
Tests basic chat message response time with a simple greeting.

**Thresholds:**
- P50: < 0.5s
- P95: < 1.0s
- P99: < 1.5s

### 2. Health Assessment Performance (`test_health_assessment_performance`)
Tests response time for blood pressure assessment query.

**Thresholds:**
- P50: < 1.0s
- P95: < 2.0s
- P99: < 2.5s

### 3. Complex Workflow Performance (`test_complex_workflow_performance`)
Tests response time for comprehensive health check covering all four-highs.

**Thresholds:**
- P50: < 1.5s
- P95: < 3.0s
- P99: < 4.0s

### 4. Skill List Performance (`test_skill_list_performance`)
Tests response time for retrieving available skills.

**Thresholds:**
- P50: < 0.3s
- P95: < 0.5s
- P99: < 0.8s

### 5. Consultation History Retrieval (`test_consultation_history_retrieval_performance`)
Tests response time for retrieving consultation message history.

**Thresholds:**
- P50: < 0.4s
- P95: < 0.8s
- P99: < 1.2s

### 6. Concurrent Requests Performance (`test_concurrent_requests_performance`)
Tests system ability to handle multiple simultaneous requests.

## Running Tests

### Run all performance tests:
```bash
pytest -m performance tests/performance/
```

### Run with verbose output:
```bash
pytest -m performance -vv tests/performance/
```

### Run specific test:
```bash
pytest tests/performance/test_api_performance.py::test_chat_send_simple_query_performance
```

### Run with custom iterations:
```bash
PERF_ITERATIONS=50 pytest -m performance tests/performance/
```

### Run using the provided script:
```bash
python scripts/run_performance_tests.py
```

With iterations:
```bash
python scripts/run_performance_tests.py --iterations 50
```

Generate report:
```bash
python scripts/run_performance_tests.py --report
```

## Performance Metrics

Each test reports the following metrics:

- **Count**: Number of iterations
- **Mean**: Average response time
- **Median**: Median response time (P50)
- **Min/Max**: Minimum and maximum response times
- **Stdev**: Standard deviation
- **P50**: 50th percentile (median)
- **P95**: 95th percentile
- **P99**: 99th percentile

## Test Fixtures

### `benchmark`
Fixture for measuring code execution time:

```python
async def test_something(benchmark):
    async def operation():
        # code to benchmark
        return result

    result = await benchmark(operation, iterations=100)
    assert result["mean"] < 0.1
```

### `performance_report`
Collector for tracking test results:

```python
def test_with_report(performance_report):
    report = PerformanceReport(
        test_name="my_test",
        iterations=10,
        durations=[...],
    )
    performance_report.add_report(report)
```

### `performance_thresholds`
Dictionary of performance threshold configurations.

### `memory_profiler`
For tracking memory usage during tests:

```python
def test_memory(memory_profiler):
    memory_profiler.start()
    # ... code to profile ...
    memory_profiler.snapshot("after_setup")
    # ... more code ...
    memory_profiler.snapshot("after_processing")
    memory_profiler.stop()
```

## Continuous Integration

Performance tests should run in CI/CD pipeline with:

1. **Separate Stage**: Run after unit/integration tests
2. **Baseline Comparison**: Compare against previous runs
3. **Alert on Degradation**: Fail if performance degrades > 20%
4. **Historical Tracking**: Store results for trend analysis

## Interpreting Results

### Success Criteria
- All percentile thresholds met (P50, P95, P99)
- No significant performance degradation vs baseline
- Stable standard deviation (consistent performance)

### Warning Signs
- P99 significantly higher than P95 (outliers)
- High standard deviation (inconsistent performance)
- Gradual increase in response times (memory leak?)

### Common Issues

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| All tests slow | LLM latency | Check LLM provider status |
| Intermittent spikes | Resource contention | Check CPU/memory usage |
| Gradual slowdown | Memory leak | Profile memory usage |
| First request slow | Cold start | Add warmup period |

## Adding New Tests

To add a new performance test:

1. Create test function with `@pytest.mark.performance` decorator
2. Use `measure_performance` helper or `benchmark` fixture
3. Define appropriate thresholds based on operation type
4. Run multiple iterations (10-30) for statistical significance
5. Include warmup iterations (2-5)

Example:

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_new_feature_performance():
    async def new_feature_operation():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/new-endpoint", json={...})
            assert response.status_code == 200

    metrics = await measure_performance(
        new_feature_operation,
        iterations=15,
        warmup=3,
    )
    stats = metrics.get_statistics()

    # Assert thresholds
    assert stats["p95"] < 2.0  # P95 under 2 seconds
```

## Performance Optimization Checklist

When performance tests fail:

1. **Database Queries**
   - Add indexes
   - Use eager loading
   - Implement caching

2. **LLM Calls**
   - Reduce prompt size
   - Use streaming for long responses
   - Implement model caching

3. **API Layer**
   - Add response compression
   - Implement connection pooling
   - Use async operations

4. **Caching**
   - Cache skill results
   - Cache patient data
   - Implement Redis caching

## Troubleshooting

### Tests timeout:
- Increase timeout in pytest config
- Check for blocking operations
- Verify async/await usage

### Inconsistent results:
- Increase warmup iterations
- Check system load
- Disable other processes during testing

### Memory issues:
- Use memory profiler fixture
- Check for connection leaks
- Verify cleanup in fixtures
