"""
Fixtures for E2E (End-to-End) tests.

E2E tests verify complete user journeys through the entire system.
These fixtures provide properly mocked services and test clients.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from src.interface.api.main import app


@pytest.fixture
def mock_external_services():
    """
    Mock external services for E2E testing.

    This fixture provides mock implementations of all MCP clients
    to allow E2E tests to run without requiring actual external services.

    Returns:
        Dictionary containing mock services:
        - profile: Mock ProfileMCPClient
        - triage: Mock TriageMCPClient
        - medication: Mock MedicationMCPClient
        - service: Mock ServiceMCPClient
    """
    from src.infrastructure.mcp.clients import (
        ProfileMCPClient,
        TriageMCPClient,
        MedicationMCPClient,
        ServiceMCPClient,
    )

    # Mock profile client
    mock_profile = AsyncMock()
    mock_profile.get_patient_profile.return_value = {
        "party_id": "test-patient-001",
        "name": "测试患者",
        "age": 45,
        "gender": "male",
        "vital_signs": {
            "blood_pressure": {"systolic": 135, "diastolic": 88},
            "blood_glucose": {"fasting": 6.2, "hba1c": 6.0},
            "bmi": 26.5,
        },
    }

    # Mock triage client
    mock_triage = AsyncMock()
    mock_triage.get_hospital_recommendation.return_value = {
        "department": "心内科",
        "level": "routine",
        "hospitals": [
            {"name": "市第一医院", "distance": "2km"},
        ],
    }

    # Mock medication client
    mock_medication = AsyncMock()
    mock_medication.check_drug_interaction.return_value = {
        "has_interaction": False,
        "severity": "none",
    }

    # Mock service client
    mock_service = AsyncMock()
    mock_service.get_service_recommendation.return_value = {
        "services": ["health_education", "follow_up"],
    }

    return {
        "profile": mock_profile,
        "triage": mock_triage,
        "medication": mock_medication,
        "service": mock_service,
    }


@pytest.fixture
def mock_memory_service():
    """Mock memory service for E2E testing."""
    mock_memory = AsyncMock()
    mock_memory.add_memory.return_value = {"memory_id": "mem-001"}
    mock_memory.search_memories.return_value = []
    mock_memory.get_all_memories.return_value = []

    return mock_memory


@pytest.fixture
def e2e_test_client():
    """
    Create a test HTTP client for E2E tests.

    This fixture uses ASGITransport to test the FastAPI app
    without running a server.

    Yields:
        AsyncClient configured for testing
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_e2e_scenarios():
    """
    Provide sample test scenarios for E2E testing.

    Returns:
        Dictionary of predefined test scenarios
    """
    return {
        "hypertension_assessment": {
            "query": "我的血压是135/88，这正常吗？需要担心吗？",
            "patient_id": "test-patient-hypertension",
            "expected_keywords": ["血压", "评估", "正常"],
        },
        "diabetes_assessment": {
            "query": "我空腹血糖6.5，糖化血红蛋白6.8，有糖尿病风险吗？",
            "patient_id": "test-patient-diabetes",
            "expected_keywords": ["糖尿病", "血糖", "风险"],
        },
        "comprehensive_check": {
            "query": "请帮我做一次全面的健康检查，包括血压、血糖、血脂、尿酸和体重评估",
            "patient_id": "test-patient-comprehensive",
            "expected_keywords": ["血压", "血糖", "血脂", "尿酸", "体重"],
        },
        "treatment_recommendation": {
            "query": "我被诊断为高血压1级，应该怎么治疗？有什么建议？",
            "patient_id": "test-patient-treatment",
            "expected_keywords": ["治疗", "建议", "生活方式"],
        },
        "medication_check": {
            "query": "我在吃阿司匹林，可以同时吃降压药吗？会有相互作用吗？",
            "patient_id": "test-patient-medication",
            "expected_keywords": ["药物", "相互作用", "注意"],
        },
    }


@pytest.fixture
def e2e_timeout():
    """
    Timeout for E2E tests.

    E2E tests may take longer due to full workflow execution.
    """
    return 30  # 30 seconds timeout for E2E tests


# ========== Test Data Fixtures ==========

@pytest.fixture
def patient_profiles():
    """Sample patient profiles for E2E testing."""
    return {
        "healthy_adult": {
            "party_id": "patient-healthy-001",
            "name": "健康成人",
            "age": 35,
            "gender": "male",
            "vital_signs": {
                "blood_pressure": {"systolic": 120, "diastolic": 80},
                "blood_glucose": {"fasting": 5.2, "hba1c": 5.5},
                "lipid": {
                    "total_cholesterol": 4.8,
                    "ldl_c": 2.8,
                    "hdl_c": 1.4,
                    "triglycerides": 1.2,
                },
                "uric_acid": 350,
                "bmi": 22.5,
            },
        },
        "hypertension_grade_1": {
            "party_id": "patient-htn-001",
            "name": "高血压患者1级",
            "age": 50,
            "gender": "male",
            "vital_signs": {
                "blood_pressure": {"systolic": 155, "diastolic": 95},
                "blood_glucose": {"fasting": 5.8, "hba1c": 5.8},
                "lipid": {
                    "total_cholesterol": 5.5,
                    "ldl_c": 3.2,
                    "hdl_c": 1.1,
                    "triglycerides": 1.8,
                },
                "uric_acid": 400,
                "bmi": 27,
            },
        },
        "diabetes_prediabetes": {
            "party_id": "patient-dm-001",
            "name": "糖尿病前期",
            "age": 55,
            "gender": "female",
            "vital_signs": {
                "blood_pressure": {"systolic": 135, "diastolic": 85},
                "blood_glucose": {"fasting": 6.5, "hba1c": 6.2},
                "lipid": {
                    "total_cholesterol": 5.8,
                    "ldl_c": 3.5,
                    "hdl_c": 1.0,
                    "triglycerides": 2.0,
                },
                "uric_acid": 420,
                "bmi": 28,
            },
        },
        "metabolic_syndrome": {
            "party_id": "patient-metabolic-001",
            "name": "代谢综合征",
            "age": 60,
            "gender": "male",
            "vital_signs": {
                "blood_pressure": {"systolic": 150, "diastolic": 95},
                "blood_glucose": {"fasting": 7.0, "hba1c": 6.5},
                "lipid": {
                    "total_cholesterol": 6.5,
                    "ldl_c": 4.2,
                    "hdl_c": 0.9,
                    "triglycerides": 2.8,
                },
                "uric_acid": 480,
                "bmi": 30,
            },
        },
    }


@pytest.fixture
def conversation_turns():
    """Sample multi-turn conversation data."""
    return [
        {
            "turn": 1,
            "user_message": "我最近头晕，不知道是什么原因",
            "expected_response_type": "clarification",
            "expected_keywords": ["请问", "需要", "提供", "测量"],
        },
        {
            "turn": 2,
            "user_message": "我测量了一下血压是150/95，心率85",
            "expected_response_type": "assessment",
            "expected_keywords": ["血压", "150", "95", "评估"],
        },
        {
            "turn": 3,
            "user_message": "那我需要注意什么？",
            "expected_response_type": "recommendation",
            "expected_keywords": ["建议", "注意", "生活方式", "监测"],
        },
    ]


# ========== Helper Functions ==========

@pytest.fixture
def assert_e2e_response():
    """
    Helper function to validate E2E responses.

    Returns:
        Function that validates response structure and content
    """
    def _assert(response_data, expected_keywords=None, expected_intent=None):
        """Validate E2E response."""
        # Check response exists
        assert response_data is not None

        # Check for response content
        response_content = response_data.get("response", response_data.get("final_response", ""))
        assert response_content, "Response content is empty"

        # Check for intent
        assert "intent" in response_data, "Intent missing from response"

        if expected_intent:
            assert response_data["intent"] == expected_intent, \
                f"Expected intent {expected_intent}, got {response_data['intent']}"

        if expected_keywords:
            for keyword in expected_keywords:
                assert keyword in response_content, \
                    f"Expected keyword '{keyword}' not found in response"

        return True

    return _assert


@pytest.fixture
def e2e_test_logger():
    """
    Logger for E2E test execution.

    Returns:
        Function that logs test execution details
    """
    def _log(test_name, **kwargs):
        """Log E2E test details."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "test": test_name,
            **kwargs
        }
        print(f"\n[E2E LOG] {test_name}: {log_entry}")
        return log_entry

    return _log
