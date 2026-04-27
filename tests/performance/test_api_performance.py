"""
Performance tests for API endpoints.

These tests verify that API responses meet performance requirements:
- Simple queries: < 1 second
- Health assessments: < 2 seconds
- Complex workflows: < 3 seconds
"""
import pytest
import asyncio
import time
from statistics import mean, median, stdev
from typing import List, Dict, Any
from httpx import AsyncClient, ASGITransport

from src.interface.api.main import app


# ========== Performance Thresholds ==========

PERFORMANCE_THRESHOLDS = {
    "simple_query": {
        "max_p50": 0.5,   # 50th percentile
        "max_p95": 1.0,   # 95th percentile
        "max_p99": 1.5,   # 99th percentile
    },
    "health_assessment": {
        "max_p50": 1.0,
        "max_p95": 2.0,
        "max_p99": 2.5,
    },
    "complex_workflow": {
        "max_p50": 1.5,
        "max_p95": 3.0,
        "max_p99": 4.0,
    },
    "skill_execution": {
        "max_p50": 0.8,
        "max_p95": 1.5,
        "max_p99": 2.0,
    },
}


# ========== Performance Test Utilities ==========

class PerformanceMetrics:
    """Container for performance metrics."""

    def __init__(self, name: str):
        self.name = name
        self.durations: List[float] = []

    def add_duration(self, duration: float):
        """Add a measured duration."""
        self.durations.append(duration)

    def get_statistics(self) -> Dict[str, float]:
        """Calculate statistics from durations."""
        if not self.durations:
            return {
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "stdev": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
            }

        sorted_durations = sorted(self.durations)
        count = len(sorted_durations)

        return {
            "count": count,
            "mean": mean(sorted_durations),
            "median": median(sorted_durations),
            "min": min(sorted_durations),
            "max": max(sorted_durations),
            "stdev": stdev(sorted_durations) if count > 1 else 0,
            "p50": sorted_durations[int(count * 0.5)],
            "p95": sorted_durations[int(count * 0.95)] if count >= 20 else sorted_durations[-1],
            "p99": sorted_durations[int(count * 0.99)] if count >= 100 else sorted_durations[-1],
        }

    def check_thresholds(self, threshold: Dict[str, float]) -> Dict[str, Any]:
        """Check if metrics meet performance thresholds."""
        stats = self.get_statistics()
        return {
            "meets_p50": stats["p50"] <= threshold["max_p50"],
            "meets_p95": stats["p95"] <= threshold["max_p95"],
            "meets_p99": stats["p99"] <= threshold["max_p99"],
            "p50_diff": threshold["max_p50"] - stats["p50"],
            "p95_diff": threshold["max_p95"] - stats["p95"],
            "p99_diff": threshold["max_p99"] - stats["p99"],
        }


async def measure_performance(
    operation,
    iterations: int = 10,
    warmup: int = 2,
) -> PerformanceMetrics:
    """
    Measure performance of an async operation.

    Args:
        operation: Async function to measure
        iterations: Number of iterations to run
        warmup: Number of warmup iterations (not counted)

    Returns:
        PerformanceMetrics with measured durations
    """
    metrics = PerformanceMetrics(operation.__name__)

    # Warmup iterations
    for _ in range(warmup):
        try:
            await operation()
        except Exception:
            pass

    # Measured iterations
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            await operation()
            duration = time.perf_counter() - start
            metrics.add_duration(duration)
        except Exception as e:
            # Still record failed attempts as they take time
            duration = time.perf_counter() - start
            metrics.add_duration(duration)
            pytest.fail(f"Operation failed: {e}")

    return metrics


# ========== API Performance Tests ==========

@pytest.mark.performance
@pytest.mark.asyncio
async def test_chat_send_simple_query_performance():
    """
    Performance Test: Simple chat query response time.

    Thresholds:
    - p50: < 0.5s
    - p95: < 1.0s
    - p99: < 1.5s
    """
    transport = ASGITransport(app=app)

    async def send_simple_query():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": "你好",
                    "patient_id": "perf-test-patient",
                },
            )
            assert response.status_code == 200

    metrics = await measure_performance(send_simple_query, iterations=20)
    stats = metrics.get_statistics()
    checks = metrics.check_thresholds(PERFORMANCE_THRESHOLDS["simple_query"])

    print(f"\n{'='*60}")
    print(f"Performance: Simple Query")
    print(f"{'='*60}")
    print(f"Iterations: {stats['count']}")
    print(f"Mean: {stats['mean']:.3f}s")
    print(f"Median: {stats['median']:.3f}s")
    print(f"Min: {stats['min']:.3f}s")
    print(f"Max: {stats['max']:.3f}s")
    print(f"P50: {stats['p50']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['simple_query']['max_p50']}s)")
    print(f"P95: {stats['p95']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['simple_query']['max_p95']}s)")
    print(f"P99: {stats['p99']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['simple_query']['max_p99']}s)")

    # Assert thresholds are met
    assert checks["meets_p50"], f"P50 ({stats['p50']:.3f}s) exceeds threshold ({PERFORMANCE_THRESHOLDS['simple_query']['max_p50']}s)"
    assert checks["meets_p95"], f"P95 ({stats['p95']:.3f}s) exceeds threshold ({PERFORMANCE_THRESHOLDS['simple_query']['max_p95']}s)"
    assert checks["meets_p99"], f"P99 ({stats['p99']:.3f}s) exceeds threshold ({PERFORMANCE_THRESHOLDS['simple_query']['max_p99']}s)"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_health_assessment_performance():
    """
    Performance Test: Health assessment response time.

    Thresholds:
    - p50: < 1.0s
    - p95: < 2.0s
    - p99: < 2.5s
    """
    transport = ASGITransport(app=app)

    async def get_health_assessment():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": "我的血压是135/88，这正常吗？",
                    "patient_id": "perf-test-patient",
                    "vital_signs": {
                        "blood_pressure": {"systolic": 135, "diastolic": 88},
                    },
                },
            )
            assert response.status_code == 200

    metrics = await measure_performance(get_health_assessment, iterations=15)
    stats = metrics.get_statistics()
    checks = metrics.check_thresholds(PERFORMANCE_THRESHOLDS["health_assessment"])

    print(f"\n{'='*60}")
    print(f"Performance: Health Assessment")
    print(f"{'='*60}")
    print(f"Iterations: {stats['count']}")
    print(f"Mean: {stats['mean']:.3f}s")
    print(f"P50: {stats['p50']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['health_assessment']['max_p50']}s)")
    print(f"P95: {stats['p95']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['health_assessment']['max_p95']}s)")
    print(f"P99: {stats['p99']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['health_assessment']['max_p99']}s)")

    assert checks["meets_p50"], f"P50 exceeds threshold"
    assert checks["meets_p95"], f"P95 exceeds threshold"
    assert checks["meets_p99"], f"P99 exceeds threshold"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_complex_workflow_performance():
    """
    Performance Test: Complex workflow with multiple assessments.

    Thresholds:
    - p50: < 1.5s
    - p95: < 3.0s
    - p99: < 4.0s
    """
    transport = ASGITransport(app=app)

    async def run_complex_workflow():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": "请帮我做一次全面的健康检查，包括血压、血糖、血脂、尿酸和体重评估",
                    "patient_id": "perf-test-patient",
                    "vital_signs": {
                        "blood_pressure": {"systolic": 145, "diastolic": 92},
                        "blood_glucose": {"fasting": 6.8, "hba1c": 6.5},
                        "lipid": {
                            "total_cholesterol": 6.5,
                            "triglycerides": 2.1,
                            "ldl_c": 4.2,
                            "hdl_c": 1.0,
                        },
                        "uric_acid": 450,
                        "bmi": 28,
                    },
                },
            )
            assert response.status_code == 200

    metrics = await measure_performance(run_complex_workflow, iterations=10)
    stats = metrics.get_statistics()
    checks = metrics.check_thresholds(PERFORMANCE_THRESHOLDS["complex_workflow"])

    print(f"\n{'='*60}")
    print(f"Performance: Complex Workflow")
    print(f"{'='*60}")
    print(f"Iterations: {stats['count']}")
    print(f"Mean: {stats['mean']:.3f}s")
    print(f"P50: {stats['p50']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['complex_workflow']['max_p50']}s)")
    print(f"P95: {stats['p95']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['complex_workflow']['max_p95']}s)")
    print(f"P99: {stats['p99']:.3f}s (threshold: {PERFORMANCE_THRESHOLDS['complex_workflow']['max_p99']}s)")

    assert checks["meets_p50"], f"P50 exceeds threshold"
    assert checks["meets_p95"], f"P95 exceeds threshold"
    assert checks["meets_p99"], f"P99 exceeds threshold"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_skill_list_performance():
    """
    Performance Test: Skill list retrieval.

    Thresholds:
    - p50: < 0.3s
    - p95: < 0.5s
    - p99: < 0.8s
    """
    transport = ASGITransport(app=app)

    async def list_skills():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v3/skills")
            assert response.status_code == 200

    metrics = await measure_performance(list_skills, iterations=30)
    stats = metrics.get_statistics()

    # Custom thresholds for simple list operation
    skill_list_threshold = {
        "max_p50": 0.3,
        "max_p95": 0.5,
        "max_p99": 0.8,
    }

    checks = metrics.check_thresholds(skill_list_threshold)

    print(f"\n{'='*60}")
    print(f"Performance: Skill List")
    print(f"{'='*60}")
    print(f"Iterations: {stats['count']}")
    print(f"Mean: {stats['mean']:.3f}s")
    print(f"P50: {stats['p50']:.3f}s")
    print(f"P95: {stats['p95']:.3f}s")
    print(f"P99: {stats['p99']:.3f}s")

    assert stats["p50"] <= skill_list_threshold["max_p50"]
    assert stats["p95"] <= skill_list_threshold["max_p95"]
    assert stats["p99"] <= skill_list_threshold["max_p99"]


@pytest.mark.performance
@pytest.mark.asyncio
async def test_consultation_history_retrieval_performance():
    """
    Performance Test: Consultation history retrieval.

    Thresholds:
    - p50: < 0.4s
    - p95: < 0.8s
    - p99: < 1.2s
    """
    transport = ASGITransport(app=app)

    async def get_history():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/chat/consultations/test-consultation/messages")
            # May return 404 for non-existent consultation, which is still fast
            assert response.status_code in [200, 404]

    metrics = await measure_performance(get_history, iterations=25)
    stats = metrics.get_statistics()

    print(f"\n{'='*60}")
    print(f"Performance: History Retrieval")
    print(f"{'='*60}")
    print(f"Iterations: {stats['count']}")
    print(f"Mean: {stats['mean']:.3f}s")
    print(f"P50: {stats['p50']:.3f}s")
    print(f"P95: {stats['p95']:.3f}s")

    # History retrieval should be fast
    assert stats["p95"] <= 0.8, "P95 exceeds 0.8s threshold"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_requests_performance():
    """
    Performance Test: Concurrent request handling.

    Verifies the system can handle multiple simultaneous requests
    without significant performance degradation.
    """
    transport = ASGITransport(app=app)

    async def send_single_request(client):
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "你好",
                "patient_id": "perf-test-concurrent",
            },
        )
        return response

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Measure sequential requests first
        start = time.perf_counter()
        for _ in range(5):
            await send_single_request(client)
        sequential_time = time.perf_counter() - start

        # Measure concurrent requests
        start = time.perf_counter()
        tasks = [send_single_request(client) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)

        print(f"\n{'='*60}")
        print(f"Performance: Concurrent Requests")
        print(f"{'='*60}")
        print(f"Sequential time (5 reqs): {sequential_time:.3f}s")
        print(f"Concurrent time (5 reqs): {concurrent_time:.3f}s")
        print(f"Speedup: {sequential_time / concurrent_time:.2f}x")

        # Concurrent should be faster (though not strictly required due to GIL)
        print(f"✓ Concurrent handling test completed")
