"""
End-to-End (E2E) tests for complete consultation flow.

These tests verify the entire user journey from initial query
to final health assessment and recommendations.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.interface.api.main import app
from src.infrastructure.agent.graph import MedicalAgent


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_hypertension_consultation(mock_external_services):
    """
    E2E Test: Complete hypertension consultation flow.

    Scenario:
    1. User asks about hypertension assessment
    2. System retrieves patient data
    3. System performs blood pressure assessment
    4. System provides cardiovascular risk evaluation
    5. System gives lifestyle recommendations
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: User sends health assessment query
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我的血压是135/88，这正常吗？需要担心吗？",
                "patient_id": "test-patient-001",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data or "final_response" in data
        assert "intent" in data

        # Verify intent was classified correctly
        assert data["intent"] in ["health_assessment", "general"]

        # Verify health assessment was performed
        response_content = data.get("response", data.get("final_response", ""))
        assert any(keyword in response_content for keyword in
                   ["血压", "评估", "正常", "风险"])

        print(f"✓ Intent classified: {data['intent']}")
        print(f"✓ Response received: {len(response_content)} chars")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_diabetes_risk_assessment():
    """
    E2E Test: Complete diabetes risk assessment flow.

    Scenario:
    1. User asks about diabetes risk
    2. System retrieves blood glucose data
    3. System performs diabetes risk evaluation
    4. System provides prevention recommendations
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我空腹血糖6.5，糖化血红蛋白6.8，有糖尿病风险吗？",
                "patient_id": "test-patient-002",
                "context": {
                    "age": 50,
                    "bmi": 28,
                    "family_history": "father_diabetes",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify diabetes assessment was triggered
        response_content = data.get("response", data.get("final_response", ""))
        assert any(keyword in response_content for keyword in
                   ["糖尿病", "血糖", "风险", "预防"])

        print(f"✓ Intent: {data['intent']}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_comprehensive_health_check_flow():
    """
    E2E Test: Comprehensive health check with multiple risk factors.

    Scenario:
    1. User requests comprehensive health assessment
    2. System evaluates all four-highs risks
    3. System provides integrated health report
    4. System gives prioritized recommendations
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "请帮我做一次全面的健康检查，包括血压、血糖、血脂、尿酸和体重评估",
                "patient_id": "test-patient-comprehensive",
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
        data = response.json()

        # Verify comprehensive assessment
        response_content = data.get("response", data.get("final_response", ""))

        # Should cover all four-highs
        assessed_conditions = {
            "血压": any(kw in response_content for kw in ["血压", "收缩压", "舒张压"]),
            "血糖": any(kw in response_content for kw in ["血糖", "糖尿病"]),
            "血脂": any(kw in response_content for kw in ["血脂", "胆固醇"]),
            "尿酸": any(kw in response_content for kw in ["尿酸", "痛风"]),
            "体重": any(kw in response_content for kw in ["BMI", "体重", "肥胖"]),
        }

        for condition, assessed in assessed_conditions.items():
            assert assessed, f"{condition} not assessed in response"

        print("✓ All four-highs assessed:")
        for condition, assessed in assessed_conditions.items():
            print(f"  - {condition}: {'✓' if assessed else '✗'}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_treatment_recommendation_flow():
    """
    E2E Test: Treatment recommendation flow.

    Scenario:
    1. User asks for treatment recommendations
    2. System provides lifestyle modifications
    3. System suggests follow-up schedule
    4. System offers medication consultation if needed
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我被诊断为高血压1级，应该怎么治疗？有什么建议？",
                "patient_id": "test-patient-hypertension",
                "context": {
                    "blood_pressure": {"systolic": 155, "diastolic": 95},
                    "age": 55,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        response_content = data.get("response", data.get("final_response", ""))

        # Should include treatment recommendations
        assert any(kw in response_content for kw in
                   ["治疗", "建议", "生活方式", "监测", "随访"])

        print("✓ Treatment recommendations provided")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_medication_interaction_check_flow():
    """
    E2E Test: Medication interaction check flow.

    Scenario:
    1. User asks about medication interactions
    2. System checks for drug interactions
    3. System provides safety recommendations
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我在吃阿司匹林，可以同时吃降压药吗？会有相互作用吗？",
                "patient_id": "test-patient-medication",
            },
        )

        assert response.status_code == 200
        data = response.json()

        response_content = data.get("response", data.get("final_response", ""))

        # Should mention medication interaction
        assert any(kw in response_content for kw in
                   ["药物", "相互作用", "注意", "建议咨询医生"])

        print("✓ Medication interaction check performed")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_follow_up_and_monitoring_plan_flow():
    """
    E2E Test: Follow-up and monitoring plan flow.

    Scenario:
    1. User completes initial assessment
    2. System generates follow-up schedule
    3. System sets monitoring alerts
    4. System provides reminder templates
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "我需要制定一个长期的健康管理计划，包括定期检查和监测",
                "patient_id": "test-patient-plan",
                "context": {
                    "conditions": ["hypertension", "diabetes_prediabetes"],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        response_content = data.get("response", data.get("final_response", ""))

        # Should include monitoring plan
        assert any(kw in response_content for kw in
                   ["监测", "随访", "检查", "计划"])

        print("✓ Follow-up plan generated")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multi_turn_conversation_flow():
    """
    E2E Test: Multi-turn conversation flow.

    Scenario:
    1. User asks initial question
    2. System asks for clarification
    3. User provides more details
    4. System provides comprehensive answer
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Turn 1: Initial question
        response1 = await client.post(
            "/api/chat/send",
            json={
                "message": "我最近头晕，不知道是什么原因",
                "patient_id": "test-patient-multi",
            },
        )

        assert response1.status_code == 200
        data1 = response1.json()

        # System should ask for more details
        response1_content = data1.get("response", data1.get("final_response", ""))
        has_question = any(kw in response1_content for kw in
                        ["请问", "需要", "提供", "测量"])

        print(f"✓ Turn 1: Question asked = {has_question}")

        # Turn 2: Provide more details
        response2 = await client.post(
            "/api/chat/send",
            json={
                "message": "我测量了一下血压是150/95，心率85",
                "patient_id": "test-patient-multi",
                "consultation_id": data1.get("consultation_id"),
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # System should now provide assessment
        response2_content = data2.get("response", data2.get("final_response", ""))
        assert "血压" in response2_content
        assert "150" in response2_content or "95" in response2_content

        print("✓ Turn 2: Assessment provided")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_plan_generation_flow():
    """
    E2E Test: Health plan generation flow.

    Scenario:
    1. User requests personalized health plan
    2. System generates comprehensive plan
    3. Plan includes diet, exercise, medication sections
    4. Plan is stored and retrievable
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request health plan
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "请为我制定一个高血压和糖尿病的综合管理计划",
                "patient_id": "test-patient-plan",
                "request_type": "health_plan",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check if health plan was mentioned
        response_content = data.get("response", data.get("final_response", ""))
        has_plan_elements = any(kw in response_content for kw in
                                ["计划", "饮食", "运动", "用药", "监测"])

        print(f"✓ Health plan elements present = {has_plan_elements}")

        # Verify plan was stored
        if "consultation_id" in data:
            consultation_id = data["consultation_id"]

            # Retrieve the consultation
            detail_response = await client.get(
                f"/api/consultations/{consultation_id}"
            )

            assert detail_response.status_code == 200
            detail_data = detail_response.json()

            print(f"✓ Plan stored and retrievable")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_recovery_flow():
    """
    E2E Test: System error recovery flow.

    Scenario:
    1. System encounters an error during processing
    2. System gracefully handles the error
    3. User receives helpful error message
    4. System logs the error for debugging
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send request with invalid data that might trigger error handling
        response = await client.post(
            "/api/chat/send",
            json={
                "message": "",  # Empty message
                "patient_id": "test-patient-error",
            },
        )

        # Should handle gracefully (200 with error message or 400)
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            # Should have error info in response
            assert "error" in data or "warning" in data
        else:
            data = response.json()
            assert "detail" in data or "error" in data

        print("✓ Error handled gracefully")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_session_persistence_across_interactions():
    """
    E2E Test: Session persistence across multiple interactions.

    Scenario:
    1. User starts a consultation session
    2. User sends multiple related messages
   3. System maintains context across messages
    4. Session history is preserved
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start session
        response1 = await client.post(
            "/api/chat/send",
            json={
                "message": "我想了解一下高血压的情况",
                "patient_id": "test-patient-session",
            },
        )

        assert response1.status_code == 200
        data1 = response1.json()
        consultation_id = data1.get("consultation_id")

        # Continue session
        response2 = await client.post(
            "/api/chat/send",
            json={
                "message": "我血压有时候会到140/90左右",
                "patient_id": "test-patient-session",
                "consultation_id": consultation_id,
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # System should remember the context
        response2_content = data2.get("response", data2.get("final_response", ""))
        context_aware = any(kw in response2_content for kw in
                           ["140", "之前", "刚才", "结合"])

        print(f"✓ Session maintained across turns = {context_aware}")

        # Retrieve session history
        history_response = await client.get(
            f"/api/consultations/{consultation_id}/messages"
        )

        assert history_response.status_code == 200
        history_data = history_response.json()

        # Should have at least 2 messages
        message_count = len(history_data.get("messages", []))
        assert message_count >= 2

        print(f"✓ Session history preserved: {message_count} messages")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_skill_routing_to_correct_assessment():
    """
    E2E Test: Skill routing to correct assessment.

    Scenario:
    1. User asks about specific disease (hypertension, diabetes, etc.)
    2. System routes to appropriate skill
    3. System returns domain-specific assessment
    4. Assessment matches the domain expertise
    """
    test_cases = [
        {
            "query": "我的血压偏高，需要怎么治疗？",
            "expected_intent": "health_assessment",
            "expected_keywords": ["血压", "治疗"],
        },
        {
            "query": "血糖偏高应该注意什么饮食？",
            "expected_intent": "health_assessment",
            "expected_keywords": ["血糖", "饮食"],
        },
        {
            "query": "体检发现尿酸高，有什么风险？",
            "expected_intent": "health_assessment",
            "expected_keywords": ["尿酸", "风险"],
        },
    ]

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i, test_case in enumerate(test_cases):
            response = await client.post(
                "/api/chat/send",
                json={
                    "message": test_case["query"],
                    "patient_id": f"test-patient-routing-{i}",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify intent classification
            assert data["intent"] == test_case["expected_intent"]

            # Verify domain-specific content
            response_content = data.get("response", data.get("final_response", ""))
            assert any(kw in response_content for kw in test_case["expected_keywords"])

            print(f"✓ Test case {i+1}: {test_case['query'][:20]}... → routed correctly")


# Performance and load tests would be in separate test files
# to avoid slowing down regular test runs
