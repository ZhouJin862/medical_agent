#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests for multi-skill orchestration.

Tests cover:
- Blood pressure and diabetes request executing both skills in parallel
- Single assessment request using single skill
- Sequential skills executing with context passing
- Mixed execution (parallel and sequential) working correctly
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    SkillSelection,
    SkillRelationship,
    RelationshipType,
    SkillExecutionResult,
    ExecutionPlan,
    ExecutionGroup,
    MultiSkillExecutionResult,
)
from src.domain.shared.services.enhanced_llm_skill_selector import (
    EnhancedLLMSkillSelector,
)
from src.domain.shared.services.skill_orchestrator import (
    SkillOrchestrator,
    SkillExecutor,
)
from src.infrastructure.agent.state import (
    AgentState,
    IntentType,
    AgentStatus,
    PatientContext,
)
from src.domain.shared.services.unified_skills_repository import (
    SkillInfo,
)
from src.domain.shared.models.skill_models import SkillSource


# ============================================================================
# Test: Blood pressure and diabetes request executes both skills in parallel
# ============================================================================


@pytest.mark.asyncio
async def test_blood_pressure_and_diabetes_request_executes_both_skills_in_parallel():
    """
    Integration test: Request for blood pressure and diabetes assessment
    should execute both skills in parallel.
    """
    mock_session = Mock()

    # Mock the skills repository
    mock_skills = [
        SkillInfo(
            id="skill-1",
            name="hypertension-assessment",
            source=SkillSource.FILE,
            description="高血压评估技能",
            layer="domain",
            enabled=True,
        ),
        SkillInfo(
            id="skill-2",
            name="diabetes-risk-assessment",
            source=SkillSource.FILE,
            description="糖尿病风险评估技能",
            layer="domain",
            enabled=True,
        ),
    ]

    with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo.list_skills = AsyncMock(return_value=mock_skills)
        mock_repo.get_skill = AsyncMock(return_value=Mock(metadata=Mock()))
        mock_repo_class.return_value = mock_repo

        # Create selector
        selector = EnhancedLLMSkillSelector(mock_session)

        # Mock Anthropic API to return multi-skill selection
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create = Mock(return_value=Mock(
                content=[Mock(text='''```json
{
  "user_intent_summary": "User wants blood pressure and diabetes assessment",
  "primary_skill": "hypertension-assessment",
  "secondary_skills": ["diabetes-risk-assessment"],
  "relationships": [
    {
      "from": "hypertension-assessment",
      "to": "diabetes-risk-assessment",
      "type": "independent",
      "reasoning": "Both are independent metabolic assessments"
    }
  ],
  "execution_suggestion": "parallel",
  "reasoning": "User asked for multiple independent assessments"
}
```''')]
            ))
            mock_anthropic.return_value = mock_client

            # Step 1: Select skills
            selection = await selector.select_skills(
                user_input="请评估我的血压和糖尿病风险",
            )

            # Verify multi-skill selection
            assert selection.has_multiple_skills
            assert selection.primary.skill_name == "hypertension-assessment"
            assert len(selection.secondary) == 1
            assert selection.secondary[0].skill_name == "diabetes-risk-assessment"
            assert selection.execution_suggestion == "parallel"

            # Step 2: Create execution plan
            plan = await selector.create_execution_plan(selection, user_input="请评估我的血压和糖尿病风险")

            assert plan.execution_mode == "parallel"
            assert len(plan.skills) == 2
            assert "hypertension-assessment" in plan.skills
            assert "diabetes-risk-assessment" in plan.skills

        # Step 3: Execute plan with mocked skills
        orchestrator = SkillOrchestrator(mock_session)

        with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
            # Mock parallel execution results
            mock_execute.side_effect = [
                SkillExecutionResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="高血压评估：血压正常",
                    structured_output={"hypertension_risk": "low", "systolic": 120, "diastolic": 80},
                ),
                SkillExecutionResult(
                    skill_name="diabetes-risk-assessment",
                    success=True,
                    response="糖尿病风险评估：低风险",
                    structured_output={"diabetes_risk": "low", "fasting_glucose": 5.5},
                ),
            ]

            result = await orchestrator.execute_plan(
                plan=plan,
                user_input="请评估我的血压和糖尿病风险",
            )

            # Verify parallel execution results
            assert result.success
            assert len(result.skill_results) == 2
            assert result.aggregated_response is not None
            assert result.structured_output is not None

            # Verify both skills' outputs are in aggregated response
            assert "高血压" in result.aggregated_response or "blood pressure" in result.aggregated_response.lower()
            assert "糖尿病" in result.aggregated_response or "diabetes" in result.aggregated_response.lower()


# ============================================================================
# Test: Single assessment request uses single skill
# ============================================================================


@pytest.mark.asyncio
async def test_single_assessment_request_uses_single_skill():
    """
    Integration test: Single assessment request should use single skill.
    """
    mock_session = Mock()

    mock_skills = [
        SkillInfo(
            id="skill-1",
            name="hypertension-assessment",
            source=SkillSource.FILE,
            description="高血压评估技能",
            layer="domain",
            enabled=True,
        ),
    ]

    with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo.list_skills = AsyncMock(return_value=mock_skills)
        mock_repo.get_skill = AsyncMock(return_value=Mock(metadata=Mock()))
        mock_repo_class.return_value = mock_repo

        selector = EnhancedLLMSkillSelector(mock_session)

        # Mock Anthropic API to return single skill
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create = Mock(return_value=Mock(
                content=[Mock(text='''```json
{
  "user_intent_summary": "User wants blood pressure assessment",
  "primary_skill": "hypertension-assessment",
  "secondary_skills": [],
  "relationships": [],
  "execution_suggestion": "sequential",
  "reasoning": "Single intent detected"
}
```''')]
            ))
            mock_anthropic.return_value = mock_client

            # Select skills
            selection = await selector.select_skills(
                user_input="评估我的血压",
            )

            # Verify single skill selection
            assert not selection.has_multiple_skills
            assert selection.primary.skill_name == "hypertension-assessment"
            assert len(selection.secondary) == 0

            # Create execution plan
            plan = await selector.create_execution_plan(selection, user_input="评估我的血压")

            assert plan.execution_mode == "sequential"
            assert len(plan.skills) == 1
            assert plan.skills[0] == "hypertension-assessment"

        # Execute single skill
        orchestrator = SkillOrchestrator(mock_session)

        with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
            mock_execute.return_value = SkillExecutionResult(
                skill_name="hypertension-assessment",
                success=True,
                response="高血压评估：血压正常",
                structured_output={"hypertension_risk": "low"},
            )

            result = await orchestrator.execute_plan(
                plan=plan,
                user_input="评估我的血压",
            )

            # Verify single skill execution
            assert result.success
            assert len(result.skill_results) == 1
            assert result.skill_results[0].skill_name == "hypertension-assessment"
            assert "高血压" in result.aggregated_response or "blood pressure" in result.aggregated_response.lower()


# ============================================================================
# Test: Sequential skills execute with context passing
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_skills_execute_with_context_passing():
    """
    Integration test: Sequential skills should pass context between them.
    """
    mock_session = Mock()

    mock_skills = [
        SkillInfo(
            id="skill-1",
            name="health-assessment",
            source=SkillSource.FILE,
            description="健康评估技能",
            layer="domain",
            enabled=True,
        ),
        SkillInfo(
            id="skill-2",
            name="prescription-recommendation",
            source=SkillSource.FILE,
            description="处方建议技能",
            layer="domain",
            enabled=True,
        ),
    ]

    with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo.list_skills = AsyncMock(return_value=mock_skills)
        mock_repo.get_skill = AsyncMock(return_value=Mock(metadata=Mock()))
        mock_repo_class.return_value = mock_repo

        selector = EnhancedLLMSkillSelector(mock_session)

        # Mock sequential multi-skill selection
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create = Mock(return_value=Mock(
                content=[Mock(text='''```json
{
  "user_intent_summary": "User wants assessment followed by prescription",
  "primary_skill": "health-assessment",
  "secondary_skills": ["prescription-recommendation"],
  "relationships": [
    {
      "from": "health-assessment",
      "to": "prescription-recommendation",
      "type": "sequential",
      "reasoning": "Assessment result informs prescription"
    }
  ],
  "execution_suggestion": "sequential",
  "reasoning": "Prescription depends on assessment results"
}
```''')]
            ))
            mock_anthropic.return_value = mock_client

            selection = await selector.select_skills(
                user_input="请评估我的健康状况并给出处方建议",
            )

            assert selection.has_multiple_skills
            assert selection.execution_suggestion == "sequential"
            # Note: _analyze_relationships is heuristic and may return empty list
            # if it doesn't find same-category skills. The LLM response relationships
            # are parsed in _parse_multi_skill_response but may be overridden by
            # the heuristic analysis in select_skills.
            # We still get the correct execution mode from the LLM.

            plan = await selector.create_execution_plan(selection, user_input="请评估我的健康状况并给出处方建议")

            assert plan.execution_mode == "sequential"
            assert len(plan.skills) == 2

        # Execute sequential plan with context passing
        orchestrator = SkillOrchestrator(mock_session)

        patient_context = {
            "basic_info": {"name": "测试用户", "age": 45},
            "vital_signs": {"blood_pressure": {"systolic": 140, "diastolic": 90}},
        }

        with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
            # Track context passed to second skill
            calls_made = []

            async def track_execute(skill_name, user_input, patient_context=None, conversation_context=None):
                calls_made.append({
                    "skill": skill_name,
                    "patient_context": patient_context,
                    "conversation_context": conversation_context,
                })
                if skill_name == "health-assessment":
                    return SkillExecutionResult(
                        skill_name="health-assessment",
                        success=True,
                        response="健康评估：发现高血压",
                        structured_output={"hypertension_detected": True, "risk_level": "high"},
                    )
                else:
                    # Second skill should receive context from first
                    return SkillExecutionResult(
                        skill_name="prescription-recommendation",
                        success=True,
                        response="处方建议：建议服用降压药",
                        structured_output={"medication": "amlodipine", "dosage": "5mg"},
                    )

            mock_execute.side_effect = track_execute

            result = await orchestrator.execute_plan(
                plan=plan,
                user_input="请评估我的健康状况并给出处方建议",
                patient_context=patient_context,
            )

            # Verify sequential execution
            assert result.success
            assert len(result.skill_results) == 2
            assert mock_execute.call_count == 2

            # Verify context was passed
            # The second call's conversation_context should contain first skill's result
            second_call_context = calls_made[1]["conversation_context"]
            assert second_call_context is not None
            assert "健康评估" in second_call_context or "health-assessment" in second_call_context


# ============================================================================
# Test: Mixed execution (parallel and sequential) works correctly
# ============================================================================


@pytest.mark.asyncio
async def test_mixed_execution_parallel_and_sequential_works_correctly():
    """
    Integration test: Mixed execution mode should handle both
    parallel and sequential groups correctly.
    """
    mock_session = Mock()

    mock_skills = [
        SkillInfo(id="skill-1", name="hypertension-assessment", source=SkillSource.FILE, description="高血压评估", layer="domain", enabled=True),
        SkillInfo(id="skill-2", name="diabetes-risk-assessment", source=SkillSource.FILE, description="糖尿病评估", layer="domain", enabled=True),
        SkillInfo(id="skill-3", name="health-summary", source=SkillSource.FILE, description="健康总结", layer="composite", enabled=True),
    ]

    with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo.list_skills = AsyncMock(return_value=mock_skills)
        mock_repo.get_skill = AsyncMock(return_value=Mock(metadata=Mock()))
        mock_repo_class.return_value = mock_repo

        selector = EnhancedLLMSkillSelector(mock_session)

        # Create a multi-skill selection with mixed relationships
        selection = MultiSkillSelection(
            primary=SkillSelection(
                skill_name="hypertension-assessment",
                confidence=0.9,
                reasoning="Primary assessment",
                should_use_skill=True,
                selection_type="primary",
            ),
            secondary=[
                SkillSelection(
                    skill_name="diabetes-risk-assessment",
                    confidence=0.85,
                    reasoning="Secondary independent assessment",
                    should_use_skill=True,
                    selection_type="secondary",
                ),
                SkillSelection(
                    skill_name="health-summary",
                    confidence=0.8,
                    reasoning="Summary after assessments",
                    should_use_skill=True,
                    selection_type="secondary",
                ),
            ],
            relationships=[
                SkillRelationship(
                    source="hypertension-assessment",
                    target="diabetes-risk-assessment",
                    relationship_type=RelationshipType.INDEPENDENT,
                ),
                SkillRelationship(
                    source="hypertension-assessment",
                    target="health-summary",
                    relationship_type=RelationshipType.SEQUENTIAL,
                ),
            ],
            execution_suggestion="mixed",
            user_intent_summary="Multi-domain assessment with summary",
        )

        plan = await selector.create_execution_plan(selection, user_input="完整健康检查")

        # Verify mixed plan structure
        assert plan.execution_mode == "mixed"
        assert len(plan.groups) >= 1

        # Execute mixed plan
        orchestrator = SkillOrchestrator(mock_session)

        with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
            mock_execute.side_effect = [
                # Parallel group results
                SkillExecutionResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="高血压评估：正常",
                    structured_output={"hypertension_risk": "low"},
                ),
                SkillExecutionResult(
                    skill_name="diabetes-risk-assessment",
                    success=True,
                    response="糖尿病评估：低风险",
                    structured_output={"diabetes_risk": "low"},
                ),
                # Sequential skill result
                SkillExecutionResult(
                    skill_name="health-summary",
                    success=True,
                    response="健康总结：整体健康状况良好",
                    structured_output={"overall_health": "good"},
                ),
            ]

            result = await orchestrator.execute_plan(
                plan=plan,
                user_input="完整健康检查",
            )

            # Verify mixed execution
            assert len(result.skill_results) == 3
            assert result.success
            assert result.aggregated_response is not None


# ============================================================================
# Test: End-to-end with skills_integration module
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_multi_skill_flow_through_skills_integration():
    """
    End-to-end integration test: Multi-skill request flowing through
    the skills_integration module.
    """
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    mock_session = Mock()

    # Create initial state
    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压和糖尿病风险",
        status=AgentStatus.LOADING_PATIENT,
        intent=None,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户", "age": 45},
            vital_signs={
                "blood_pressure": {"systolic": 130, "diastolic": 85},
                "blood_glucose": {"fasting_glucose": 6.2},
            },
            medical_history={},
        ),
    )

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock EnhancedLLMSkillSelector to detect multi-skill intent
        with patch('src.infrastructure.agent.skills_integration.EnhancedLLMSkillSelector') as mock_selector_class:
            mock_selector = Mock()
            mock_selection = Mock(
                skill_name="hypertension-assessment",
                confidence=0.9,
                reasoning="Multi-skill detected",
                alternative_skills=["diabetes-risk-assessment"],
            )
            mock_selector.select_skills = AsyncMock(return_value=MultiSkillSelection(
                primary=SkillSelection(
                    skill_name="hypertension-assessment",
                    confidence=0.9,
                    reasoning="Primary",
                    should_use_skill=True,
                    selection_type="primary",
                ),
                secondary=[
                    SkillSelection(
                        skill_name="diabetes-risk-assessment",
                        confidence=0.85,
                        reasoning="Secondary",
                        should_use_skill=True,
                        selection_type="secondary",
                    ),
                ],
                execution_suggestion="parallel",
            ))
            mock_selector.create_execution_plan = AsyncMock(return_value=ExecutionPlan(
                skills=["hypertension-assessment", "diabetes-risk-assessment"],
                execution_mode="parallel",
            ))
            mock_selector_class.return_value = mock_selector

            result_state = await classify_intent_with_llm_node(state)

            assert result_state.suggested_skill == "hypertension-assessment"
            assert result_state.confidence == 0.9
            assert result_state.multi_skill_selection is not None


# ============================================================================
# Test: Multi-skill execution with context snapshot
# ============================================================================


@pytest.mark.asyncio
async def test_multi_skill_execution_with_context_snapshot():
    """
    Integration test: Multi-skill execution with patient context snapshot.
    """
    from src.domain.shared.value_objects.context_snapshot import ContextSnapshot
    from src.domain.shared.value_objects.blood_pressure import BloodPressure
    from src.domain.shared.value_objects.blood_glucose import BloodGlucose, GlucoseMeasurementType
    from src.domain.shared.value_objects.patient_data import PatientData

    mock_session = Mock()

    # Create context snapshot with proper structure
    patient_data = PatientData(
        patient_id="test_patient_001",
        name="测试用户",
        age=50,
    )

    context_snapshot = ContextSnapshot(
        patient_data=patient_data,
        vital_signs={
            "blood_pressure": {"systolic": 140, "diastolic": 90},
            "blood_glucose": {"value": 6.5, "measurement_type": "fasting"},
        },
    )

    orchestrator = SkillOrchestrator(mock_session)

    plan = ExecutionPlan(
        skills=["hypertension-assessment", "diabetes-risk-assessment"],
        execution_mode="parallel",
    )

    patient_context = {
        "basic_info": {
            "patient_id": context_snapshot.patient_data.patient_id,
            "name": context_snapshot.patient_data.name,
            "age": context_snapshot.patient_data.age,
        },
        "vital_signs": context_snapshot.vital_signs,
    }

    with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
        mock_execute.side_effect = [
            SkillExecutionResult(
                skill_name="hypertension-assessment",
                success=True,
                response="高血压评估：血压偏高",
                structured_output={"hypertension_risk": "high"},
            ),
            SkillExecutionResult(
                skill_name="diabetes-risk-assessment",
                success=True,
                response="糖尿病风险评估：血糖偏高",
                structured_output={"diabetes_risk": "elevated"},
            ),
        ]

        result = await orchestrator.execute_plan(
            plan=plan,
            user_input="评估我的健康状况",
            patient_context=patient_context,
        )

        assert result.success
        assert len(result.skill_results) == 2
        # Verify context was used (e.g., detected high values)
        assert "偏高" in result.aggregated_response or "high" in result.aggregated_response.lower()


# ============================================================================
# Test: Skill orchestration error recovery
# ============================================================================


@pytest.mark.asyncio
async def test_skill_orchestration_handles_partial_failure_gracefully():
    """
    Integration test: Skill orchestrator should handle partial failures gracefully.
    """
    mock_session = Mock()

    orchestrator = SkillOrchestrator(mock_session)

    plan = ExecutionPlan(
        skills=["skill1", "skill2", "skill3"],
        execution_mode="parallel",
        aggregation_strategy="merge",
    )

    with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
        mock_execute.side_effect = [
            SkillExecutionResult(skill_name="skill1", success=True, response="Skill 1 result"),
            SkillExecutionResult(skill_name="skill2", success=False, error="Skill 2 failed"),
            SkillExecutionResult(skill_name="skill3", success=True, response="Skill 3 result"),
        ]

        result = await orchestrator.execute_plan(
            plan=plan,
            user_input="test input",
        )

        # Verify partial failure handling
        assert not result.success  # Overall is False when any fail
        assert result.success_rate == 2/3
        assert len(result.successful_skills) == 2
        assert len(result.failed_skills) == 1
        assert len(result.errors) > 0

        # Aggregated response should still contain successful results
        assert result.aggregated_response is not None


# ============================================================================
# Test: Multi-skill selection with relationship analysis
# ============================================================================


@pytest.mark.asyncio
async def test_multi_skill_selection_analyzes_relationships_correctly():
    """
    Integration test: Multi-skill selection should analyze relationships correctly.
    """
    mock_session = Mock()

    mock_skills = [
        SkillInfo(id="skill-1", name="hypertension-assessment", source=SkillSource.FILE, description="高血压评估", layer="domain", enabled=True),
        SkillInfo(id="skill-2", name="diabetes-risk-assessment", source=SkillSource.FILE, description="糖尿病评估", layer="domain", enabled=True),
        SkillInfo(id="skill-3", name="lipid-assessment", source=SkillSource.FILE, description="血脂评估", layer="domain", enabled=True),
    ]

    with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo.list_skills = AsyncMock(return_value=mock_skills)
        mock_repo.get_skill = AsyncMock(return_value=Mock(metadata=Mock()))
        mock_repo_class.return_value = mock_repo

        selector = EnhancedLLMSkillSelector(mock_session)

        # Mock LLM to return skills with relationships
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create = Mock(return_value=Mock(
                content=[Mock(text='''```json
{
  "user_intent_summary": "User wants comprehensive metabolic assessment",
  "primary_skill": "hypertension-assessment",
  "secondary_skills": ["diabetes-risk-assessment", "lipid-assessment"],
  "relationships": [
    {
      "from": "hypertension-assessment",
      "to": "diabetes-risk-assessment",
      "type": "independent",
      "reasoning": "Independent metabolic assessments"
    },
    {
      "from": "hypertension-assessment",
      "to": "lipid-assessment",
      "type": "independent",
      "reasoning": "Independent metabolic assessments"
    }
  ],
  "execution_suggestion": "parallel",
  "reasoning": "All assessments are independent"
}
```''')]
            ))
            mock_anthropic.return_value = mock_client

            selection = await selector.select_skills(
                user_input="请评估我的血压、血糖和血脂",
            )

            # Verify relationship analysis
            assert selection.has_multiple_skills
            assert len(selection.relationships) >= 2
            assert selection.execution_suggestion == "parallel"

            # Verify all relationships are marked as independent
            independent_rels = [r for r in selection.relationships
                              if r.relationship_type == RelationshipType.INDEPENDENT]
            assert len(independent_rels) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
