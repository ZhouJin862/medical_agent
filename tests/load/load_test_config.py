"""
Load test configuration and scenarios.

Defines load testing scenarios with different intensity levels.
"""
from dataclasses import dataclass
from typing import Dict, List, Any
from enum import Enum


class LoadLevel(Enum):
    """Load intensity levels."""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    STRESS = "stress"


@dataclass
class LoadTestScenario:
    """
    Load test scenario configuration.

    Attributes:
        name: Scenario name
        users: Number of concurrent users
        spawn_rate: Users spawned per second
        run_time: Total test duration (seconds)
        target_rps: Target requests per second
        endpoints: List of endpoints to test with weights
    """
    name: str
    users: int
    spawn_rate: int
    run_time: int
    target_rps: int
    endpoints: List[Dict[str, Any]]  # {"path": str, "weight": int, "method": str}


# Load test scenarios
LOAD_TEST_SCENARIOS: Dict[LoadLevel, LoadTestScenario] = {
    LoadLevel.LIGHT: LoadTestScenario(
        name="Light Load",
        users=10,
        spawn_rate=2,
        run_time=60,
        target_rps=10,
        endpoints=[
            {"path": "/api/chat/send", "weight": 70, "method": "POST"},
            {"path": "/api/v3/skills", "weight": 20, "method": "GET"},
            {"path": "/api/chat/consultations/{id}/messages", "weight": 10, "method": "GET"},
        ],
    ),

    LoadLevel.MEDIUM: LoadTestScenario(
        name="Medium Load",
        users=50,
        spawn_rate=5,
        run_time=120,
        target_rps=50,
        endpoints=[
            {"path": "/api/chat/send", "weight": 70, "method": "POST"},
            {"path": "/api/v3/skills", "weight": 15, "method": "GET"},
            {"path": "/api/chat/consultations/{id}/messages", "weight": 10, "method": "GET"},
            {"path": "/api/v3/skills/{name}", "weight": 5, "method": "GET"},
        ],
    ),

    LoadLevel.HEAVY: LoadTestScenario(
        name="Heavy Load",
        users=100,
        spawn_rate=10,
        run_time=180,
        target_rps=100,
        endpoints=[
            {"path": "/api/chat/send", "weight": 65, "method": "POST"},
            {"path": "/api/v3/skills", "weight": 15, "method": "GET"},
            {"path": "/api/chat/consultations/{id}/messages", "weight": 10, "method": "GET"},
            {"path": "/api/v3/skills/{name}", "weight": 5, "method": "GET"},
            {"path": "/api/health/{patient_id}", "weight": 5, "method": "GET"},
        ],
    ),

    LoadLevel.STRESS: LoadTestScenario(
        name="Stress Test",
        users=200,
        spawn_rate=20,
        run_time=300,
        target_rps=200,
        endpoints=[
            {"path": "/api/chat/send", "weight": 60, "method": "POST"},
            {"path": "/api/v3/skills", "weight": 15, "method": "GET"},
            {"path": "/api/chat/consultations/{id}/messages", "weight": 10, "method": "GET"},
            {"path": "/api/v3/skills/{name}", "weight": 5, "method": "GET"},
            {"path": "/api/health/{patient_id}", "weight": 5, "method": "GET"},
            {"path": "/api/plan/{patient_id}", "weight": 5, "method": "GET"},
        ],
    ),
}


# Load test thresholds
LOAD_TEST_THRESHOLDS = {
    "success_rate": {
        "min": 0.99,  # 99% success rate minimum
        "target": 0.995,  # 99.5% target
    },
    "response_time": {
        "p50_max_ms": 1000,
        "p95_max_ms": 3000,
        "p99_max_ms": 5000,
    },
    "throughput": {
        "min_rps": 0.8,  # At least 80% of target RPS
    },
    "error_rate": {
        "max": 0.01,  # Max 1% error rate
    },
}


# Sample request data for different endpoints
SAMPLE_REQUEST_DATA = {
    "/api/chat/send": [
        {
            "message": "你好",
            "patient_id": "load-test-user-{user_id}",
        },
        {
            "message": "我的血压是135/88，这正常吗？",
            "patient_id": "load-test-user-{user_id}",
            "vital_signs": {"blood_pressure": {"systolic": 135, "diastolic": 88}},
        },
        {
            "message": "请帮我做一次全面的健康检查",
            "patient_id": "load-test-user-{user_id}",
        },
    ],
}


def get_scenario(level: LoadLevel) -> LoadTestScenario:
    """Get load test scenario by level."""
    return LOAD_TEST_SCENARIOS[level]


def get_all_scenarios() -> List[LoadTestScenario]:
    """Get all load test scenarios."""
    return list(LOAD_TEST_SCENARIOS.values())
