"""
Load tests for Medical Agent API.

These tests simulate concurrent user load to verify system stability
and performance under stress.
"""
import pytest
import asyncio
import time
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from statistics import mean, median

from src.interface.api.main import app
from .load_test_config import (
    LoadLevel,
    get_scenario,
    LOAD_TEST_THRESHOLDS,
    SAMPLE_REQUEST_DATA,
)


class LoadTestMetrics:
    """Container for load test metrics."""

    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.start_time = None
        self.end_time = None
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times: List[float] = []
        self.errors: Dict[str, int] = {}
        self.endpoint_stats: Dict[str, Dict] = {}

    def record_request(self, endpoint: str, success: bool, duration: float, error: str = None):
        """Record a request result."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            self.response_times.append(duration)
        else:
            self.failed_requests += 1
            if error:
                self.errors[error] = self.errors.get(error, 0) + 1

        # Track per-endpoint stats
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "times": [],
            }

        self.endpoint_stats[endpoint]["total"] += 1
        if success:
            self.endpoint_stats[endpoint]["success"] += 1
            self.endpoint_stats[endpoint]["times"].append(duration)
        else:
            self.endpoint_stats[endpoint]["failed"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get load test summary."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0

        sorted_times = sorted(self.response_times) if self.response_times else []
        count = len(sorted_times)

        return {
            "scenario": self.scenario_name,
            "duration_seconds": duration,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "requests_per_second": self.total_requests / duration if duration > 0 else 0,
            "response_times": {
                "mean": mean(sorted_times) if sorted_times else 0,
                "median": median(sorted_times) if sorted_times else 0,
                "min": min(sorted_times) if sorted_times else 0,
                "max": max(sorted_times) if sorted_times else 0,
                "p50": sorted_times[int(count * 0.5)] if count > 0 else 0,
                "p95": sorted_times[int(count * 0.95)] if count >= 20 else (sorted_times[-1] if count > 0 else 0),
                "p99": sorted_times[int(count * 0.99)] if count >= 100 else (sorted_times[-1] if count > 0 else 0),
            },
            "errors": self.errors,
            "endpoint_stats": self.endpoint_stats,
        }

    def print_summary(self):
        """Print load test summary."""
        summary = self.get_summary()

        print(f"\n{'='*80}")
        print(f"LOAD TEST SUMMARY: {self.scenario_name}")
        print(f"{'='*80}")
        print(f"Duration: {summary['duration_seconds']:.1f}s")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Successful: {summary['successful_requests']} ({summary['success_rate']*100:.2f}%)")
        print(f"Failed: {summary['failed_requests']}")
        print(f"Requests/Second: {summary['requests_per_second']:.2f}")

        print(f"\nResponse Times:")
        rt = summary["response_times"]
        print(f"  Mean: {rt['mean']*1000:.1f}ms")
        print(f"  P50: {rt['p50']*1000:.1f}ms")
        print(f"  P95: {rt['p95']*1000:.1f}ms")
        print(f"  P99: {rt['p99']*1000:.1f}ms")

        if summary["errors"]:
            print(f"\nErrors:")
            for error, count in summary["errors"].items():
                print(f"  {error}: {count}")

        print(f"{'='*80}\n")


class LoadTestUser:
    """Simulated user for load testing."""

    def __init__(self, user_id: int, client: AsyncClient):
        self.user_id = user_id
        self.client = client

    async def make_request(self, endpoint: str, method: str, data: Dict = None, params: Dict = None):
        """Make a request to the endpoint."""
        start = time.perf_counter()

        try:
            # Format endpoint path
            path = endpoint.format(
                id=f"test-{self.user_id}",
                patient_id=f"load-test-user-{self.user_id}",
                name="health_assessment",
            )

            if method == "GET":
                response = await self.client.get(path, params=params)
            elif method == "POST":
                response = await self.client.post(path, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            duration = time.perf_counter() - start
            success = response.status_code == 200

            return {
                "success": success,
                "duration": duration,
                "status_code": response.status_code,
                "error": None if success else f"HTTP {response.status_code}",
            }

        except Exception as e:
            duration = time.perf_counter() - start
            return {
                "success": False,
                "duration": duration,
                "status_code": None,
                "error": str(e),
            }


async def run_load_test(
    scenario: LoadLevel,
    run_duration_seconds: int = None,
) -> LoadTestMetrics:
    """
    Run a load test with the specified scenario.

    Args:
        scenario: Load level to test
        run_duration_seconds: Override default duration

    Returns:
        LoadTestMetrics with test results
    """
    config = get_scenario(scenario)
    metrics = LoadTestMetrics(config.name)
    duration = run_duration_seconds or config.run_time

    print(f"\nStarting load test: {config.name}")
    print(f"  Users: {config.users}")
    print(f"  Spawn Rate: {config.spawn_rate}/s")
    print(f"  Duration: {duration}s")
    print(f"  Target RPS: {config.target_rps}")

    transport = ASGITransport(app=app)
    metrics.start_time = datetime.now()

    # Create users
    users = []
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(config.users):
            users.append(LoadTestUser(i, client))

        # Spawn users gradually
        spawned_users = []
        for i in range(config.users):
            spawned_users.append(users[i])
            if len(spawned_users) >= config.spawn_rate:
                await asyncio.sleep(0.1)

        # Run load test for duration
        end_time = time.time() + duration
        request_tasks = []

        while time.time() < end_time:
            # Select endpoint based on weights
            endpoints = config.endpoints
            total_weight = sum(e["weight"] for e in endpoints)
            rand = random.uniform(0, total_weight)
            current_weight = 0

            selected_endpoint = endpoints[0]
            for endpoint in endpoints:
                current_weight += endpoint["weight"]
                if rand <= current_weight:
                    selected_endpoint = endpoint
                    break

            # Select random user
            user = random.choice(users)

            # Prepare request data
            request_data = None
            if selected_endpoint["method"] == "POST" and selected_endpoint["path"] in SAMPLE_REQUEST_DATA:
                sample = random.choice(SAMPLE_REQUEST_DATA[selected_endpoint["path"]])
                request_data = {
                    k: v.format(user_id=user.user_id) if isinstance(v, str) else v
                    for k, v in sample.items()
                }

            # Make request
            result = await user.make_request(
                selected_endpoint["path"],
                selected_endpoint["method"],
                request_data,
            )

            metrics.record_request(
                selected_endpoint["path"],
                result["success"],
                result["duration"],
                result["error"],
            )

            # Small delay between requests
            await asyncio.sleep(random.uniform(0.01, 0.05))

    metrics.end_time = datetime.now()
    return metrics


# ========== Load Tests ==========

@pytest.mark.load
@pytest.mark.asyncio
async def test_light_load():
    """Load Test: Light load (10 users, 10 RPS)."""
    metrics = await run_load_test(LoadLevel.LIGHT)
    summary = metrics.get_summary()

    metrics.print_summary()

    # Verify success rate
    assert summary["success_rate"] >= LOAD_TEST_THRESHOLDS["success_rate"]["min"], \
        f"Success rate {summary['success_rate']*100:.2f}% below minimum"

    # Verify response times
    assert summary["response_times"]["p95"] <= LOAD_TEST_THRESHOLDS["response_time"]["p95_max_ms"] / 1000, \
        f"P95 response time exceeds threshold"


@pytest.mark.load
@pytest.mark.asyncio
async def test_medium_load():
    """Load Test: Medium load (50 users, 50 RPS)."""
    metrics = await run_load_test(LoadLevel.MEDIUM)
    summary = metrics.get_summary()

    metrics.print_summary()

    # Verify success rate
    assert summary["success_rate"] >= LOAD_TEST_THRESHOLDS["success_rate"]["min"], \
        f"Success rate {summary['success_rate']*100:.2f}% below minimum"

    # Verify throughput
    assert summary["requests_per_second"] >= LOAD_TEST_THRESHOLDS["throughput"]["min_rps"] * 50, \
        f"Throughput {summary['requests_per_second']:.2f} RPS below minimum"


@pytest.mark.load
@pytest.mark.asyncio
async def test_heavy_load():
    """Load Test: Heavy load (100 users, 100 RPS)."""
    metrics = await run_load_test(LoadLevel.HEAVY, run_duration_seconds=60)
    summary = metrics.get_summary()

    metrics.print_summary()

    # Verify success rate (allow slightly lower for heavy load)
    assert summary["success_rate"] >= 0.98, \
        f"Success rate {summary['success_rate']*100:.2f}% below minimum for heavy load"

    # Verify error rate not excessive
    error_rate = summary["failed_requests"] / summary["total_requests"] if summary["total_requests"] > 0 else 0
    assert error_rate <= LOAD_TEST_THRESHOLDS["error_rate"]["max"], \
        f"Error rate {error_rate*100:.2f}% exceeds maximum"


@pytest.mark.load
@pytest.mark.asyncio
async def test_sustained_load():
    """Load Test: Sustained load over extended period."""
    config = get_scenario(LoadLevel.MEDIUM)
    metrics = LoadTestMetrics(f"Sustained {config.name}")

    print(f"\nStarting sustained load test: {config.name} (2 minutes)")
    print(f"  Users: {config.users}")

    transport = ASGITransport(app=app)
    metrics.start_time = datetime.now()

    users = []
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(config.users):
            users.append(LoadTestUser(i, client))

        # Run for 2 minutes
        end_time = time.time() + 120

        while time.time() < end_time:
            user = random.choice(users)

            result = await user.make_request(
                "/api/chat/send",
                "POST",
                {"message": "测试消息", "patient_id": f"sustained-test-{user.user_id}"},
            )

            metrics.record_request(
                "/api/chat/send",
                result["success"],
                result["duration"],
                result["error"],
            )

            await asyncio.sleep(random.uniform(0.01, 0.1))

    metrics.end_time = datetime.now()
    summary = metrics.get_summary()

    metrics.print_summary()

    # Check for performance degradation over time
    # (Would require more detailed time-series analysis)
    assert summary["success_rate"] >= 0.98, "Success rate degraded over time"


@pytest.mark.load
@pytest.mark.asyncio
async def test_ramp_up_load():
    """Load Test: Gradual ramp-up of users."""
    metrics = LoadTestMetrics("Ramp-up Test")
    max_users = 50
    ramp_duration = 30  # seconds to reach max users

    print(f"\nStarting ramp-up load test")
    print(f"  Max Users: {max_users}")
    print(f"  Ramp Duration: {ramp_duration}s")

    transport = ASGITransport(app=app)
    metrics.start_time = datetime.now()

    active_users: List[LoadTestUser] = []
    start_time = time.time()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        while time.time() - start_time < ramp_duration:
            # Add new users over time
            target_users = int((time.time() - start_time) / ramp_duration * max_users)

            while len(active_users) < target_users:
                new_user = LoadTestUser(len(active_users), client)
                active_users.append(new_user)

            # Make requests from active users
            user = random.choice(active_users)

            result = await user.make_request(
                "/api/chat/send",
                "POST",
                {"message": "Ramp up test", "patient_id": f"ramp-test-{user.user_id}"},
            )

            metrics.record_request(
                "/api/chat/send",
                result["success"],
                result["duration"],
                result["error"],
            )

            await asyncio.sleep(random.uniform(0.01, 0.05))

    metrics.end_time = datetime.now()
    summary = metrics.get_summary()

    metrics.print_summary()

    # Check that success rate remained good during ramp-up
    assert summary["success_rate"] >= 0.97, "Success rate degraded during ramp-up"
