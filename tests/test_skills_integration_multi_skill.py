#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for multi-skill orchestration in skills_integration.

Tests cover:
- Intent classification for single and multi-skill scenarios
- execute_claude_skill_node behavior with single vs multiple skills
- Parallel execution with result aggregation
- Partial success handling when some skills fail
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    SkillSelection,
    SkillExecutionResult,
    ExecutionPlan,
    MultiSkillExecutionResult,
)
from src.infrastructure.agent.state import (
    AgentState,
    AgentStatus,
    PatientContext,
)
from src.domain.shared.services.enhanced_llm_skill_selector import (
    EnhancedLLMSkillSelector,
)
from src.domain.shared.services.skill_orchestrator import (
    SkillOrchestrator,
)


# ============================================================================
# Test classify_intent_with_llm_node
# ============================================================================


@pytest.mark.asyncio
async def test_classify_intent_returns_multi_skill_selection_for_multi_intent_input():
    """Test that classify_intent returns multi-skill selection for multi-intent input."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    # Create initial state with multi-intent input
    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压和糖尿病风险",
        status=AgentStatus.CLASSIFYING_INTENT,
        intent="general_chat",
    )

    mock_session = Mock()

    # Mock the EnhancedLLMSkillSelector to return multi-skill selection
    mock_multi_selection = MultiSkillSelection(
        primary=SkillSelection(
            skill_name="hypertension-assessment",
            confidence=0.9,
            reasoning="Primary assessment for blood pressure",
            should_use_skill=True,
            selection_type="primary",
        ),
        secondary=[
            SkillSelection(
                skill_name="diabetes-risk-assessment",
                confidence=0.85,
                reasoning="Secondary assessment for diabetes risk",
                should_use_skill=True,
                selection_type="secondary",
            ),
        ],
        user_intent_summary="User wants blood pressure and diabetes assessment",
        execution_suggestion="parallel",
    )

    # Mock execution plan
    mock_execution_plan = ExecutionPlan(
        skills=["hypertension-assessment", "diabetes-risk-assessment"],
        execution_mode="parallel",
        aggregation_strategy="merge",
    )

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock EnhancedLLMSkillSelector to return multi-skill result
        with patch('src.infrastructure.agent.skills_integration.EnhancedLLMSkillSelector') as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_skills = AsyncMock(return_value=mock_multi_selection)
            mock_selector.create_execution_plan = AsyncMock(return_value=mock_execution_plan)
            mock_selector_class.return_value = mock_selector

            result_state = await classify_intent_with_llm_node(state)

            # Verify basic intent classification worked (intent is string, not enum)
            assert result_state.intent == "health_assessment"
            assert result_state.suggested_skill == "hypertension-assessment"
            assert result_state.confidence == 0.9
            assert result_state.status == "classifying_intent"
            assert result_state.multi_skill_selection is not None
            assert result_state.execution_plan is not None


@pytest.mark.asyncio
async def test_classify_intent_returns_single_skill_for_single_intent_input():
    """Test that classify_intent returns single skill for single-intent input."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    # Create initial state with single-intent input
    state = AgentState(
        patient_id="test_patient_001",
        user_input="评估我的血压",
        status="classifying_intent",
        intent="general_chat",
    )

    mock_session = Mock()

    # Mock single skill selection
    mock_single_selection = MultiSkillSelection(
        primary=SkillSelection(
            skill_name="hypertension-assessment",
            confidence=0.95,
            reasoning="Single intent detected",
            should_use_skill=True,
            selection_type="primary",
        ),
        user_intent_summary="User wants blood pressure assessment",
    )

    # Mock execution plan for single skill
    mock_execution_plan = ExecutionPlan(
        skills=["hypertension-assessment"],
        execution_mode="sequential",
        aggregation_strategy="single",
    )

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock EnhancedLLMSkillSelector to return single skill
        with patch('src.infrastructure.agent.skills_integration.EnhancedLLMSkillSelector') as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_skills = AsyncMock(return_value=mock_single_selection)
            mock_selector.create_execution_plan = AsyncMock(return_value=mock_execution_plan)
            mock_selector_class.return_value = mock_selector

            result_state = await classify_intent_with_llm_node(state)

            # Verify single skill was selected
            assert result_state.intent == "health_assessment"
            assert result_state.suggested_skill == "hypertension-assessment"
            assert result_state.confidence == 0.95
            assert result_state.status == "classifying_intent"


# ============================================================================
# Test execute_claude_skill_node with multi-skill orchestration
# ============================================================================


@pytest.mark.asyncio
async def test_execute_claude_skill_node_uses_orchestrator_for_multi_skill():
    """Test that execute_claude_skill_node uses orchestrator for multi-skill execution."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    # Create state with multi-skill context
    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压和糖尿病风险",
        suggested_skill="hypertension-assessment",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent="health_assessment",
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={
                "name": "测试用户",
                "age": 45,
                "gender": "male",
            },
            vital_signs={},
            medical_history={},
        ),
        # Use multi_skill_selection field
        multi_skill_selection={
            "has_multiple_skills": True,
            "secondary_skills": ["diabetes-risk-assessment"],
            "execution_mode": "parallel",
        },
        execution_plan={
            "skills": ["hypertension-assessment", "diabetes-risk-assessment"],
            "execution_mode": "parallel",
        },
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock SkillOrchestrator
        mock_orchestrator = Mock()
        mock_execution_result = MultiSkillExecutionResult(
            success=True,
            execution_plan=ExecutionPlan(
                skills=["hypertension-assessment", "diabetes-risk-assessment"],
                execution_mode="parallel",
                aggregation_strategy="merge",
            ),
            skill_results=[
                SkillExecutionResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="高血压评估结果：正常",
                ),
                SkillExecutionResult(
                    skill_name="diabetes-risk-assessment",
                    success=True,
                    response="糖尿病风险评估：低风险",
                ),
            ],
            aggregated_response="基于综合评估：高血压正常，糖尿病低风险",
            structured_output={
                "hypertension_risk": "normal",
                "diabetes_risk": "low",
            },
        )
        mock_orchestrator.execute_plan = AsyncMock(return_value=mock_execution_result)

        with patch('src.infrastructure.agent.skills_integration.SkillOrchestrator', return_value=mock_orchestrator):
            result_state = await execute_claude_skill_node(state)

            # Verify orchestrator was called
            assert mock_orchestrator.execute_plan.called
            assert result_state.final_response is not None
            assert "综合评估" in result_state.final_response or "assess" in result_state.final_response.lower()


@pytest.mark.asyncio
async def test_execute_claude_skill_node_uses_executor_for_single_skill():
    """Test that execute_claude_skill_node uses single executor for single skill."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    # Create state with single skill
    state = AgentState(
        patient_id="test_patient_001",
        user_input="评估我的血压",
        suggested_skill="hypertension-assessment",
        confidence=0.95,
        status=AgentStatus.EXECUTING_SKILL,
        intent="health_assessment",
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户", "age": 45},
            vital_signs={},
            medical_history={},
        ),
        # No multi-skill data
        multi_skill_selection=None,
        execution_plan=None,
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock ClaudeSkillsExecutor
        with patch('src.infrastructure.agent.skills_integration.ClaudeSkillsExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_skill = AsyncMock(
                return_value={
                    "success": True,
                    "response": "高血压评估结果：血压正常",
                    "skill_source": "file",
                }
            )
            mock_executor_class.return_value = mock_executor

            result_state = await execute_claude_skill_node(state)

            # Verify single executor was called
            assert mock_executor.execute_skill.called
            assert result_state.final_response is not None
            assert "血压" in result_state.final_response or "blood pressure" in result_state.final_response.lower()


# ============================================================================
# Test parallel execution with aggregation
# ============================================================================


@pytest.mark.asyncio
async def test_multi_skill_parallel_execution_produces_aggregated_response():
    """Test that parallel multi-skill execution produces aggregated response."""
    mock_session = Mock()

    with patch('src.domain.shared.services.skill_orchestrator.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        orchestrator = SkillOrchestrator(mock_session)

        # Create parallel execution plan
        plan = ExecutionPlan(
            skills=["hypertension-assessment", "diabetes-risk-assessment", "lipid-assessment"],
            execution_mode="parallel",
            aggregation_strategy="merge",
        )

        user_input = "请评估我的血压、糖尿病和血脂风险"

        # Mock the executor's execute_skill method
        with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
            # Setup return values for parallel execution
            mock_execute.side_effect = [
                SkillExecutionResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="高血压评估：收缩压120mmHg，舒张压80mmHg，属于正常范围",
                    structured_output={"hypertension_risk": "low"},
                ),
                SkillExecutionResult(
                    skill_name="diabetes-risk-assessment",
                    success=True,
                    response="糖尿病风险评估：空腹血糖5.5mmol/L，属于正常范围",
                    structured_output={"diabetes_risk": "low"},
                ),
                SkillExecutionResult(
                    skill_name="lipid-assessment",
                    success=True,
                    response="血脂评估：总胆固醇5.2mmol/L，属于正常范围",
                    structured_output={"lipid_risk": "low"},
                ),
            ]

            result = await orchestrator.execute_plan(
                plan=plan,
                user_input=user_input,
            )

            # Verify all skills executed successfully
            assert result.success
            assert len(result.skill_results) == 3
            assert all(r.success for r in result.skill_results)

            # Verify aggregated response contains all skill results
            assert result.aggregated_response is not None
            assert len(result.aggregated_response) > 0

            # Verify structured output was merged
            assert result.structured_output is not None
            assert "hypertension_risk" in result.structured_output
            assert "diabetes_risk" in result.structured_output
            assert "lipid_risk" in result.structured_output


# ============================================================================
# Test partial success handling
# ============================================================================


@pytest.mark.asyncio
async def test_multi_skill_execution_with_one_failure_produces_partial_success():
    """Test that multi-skill execution with one failure produces partial success."""
    mock_session = Mock()

    with patch('src.domain.shared.services.skill_orchestrator.UnifiedSkillsRepository') as mock_repo_class:
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        orchestrator = SkillOrchestrator(mock_session)

        # Create parallel execution plan
        plan = ExecutionPlan(
            skills=["hypertension-assessment", "diabetes-risk-assessment", "lipid-assessment"],
            execution_mode="parallel",
            aggregation_strategy="merge",
        )

        user_input = "请评估我的血压、糖尿病和血脂风险"

        # Mock the executor to have one failure
        with patch.object(orchestrator._executor, 'execute_skill') as mock_execute:
            mock_execute.side_effect = [
                SkillExecutionResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="高血压评估：正常",
                ),
                SkillExecutionResult(
                    skill_name="diabetes-risk-assessment",
                    success=False,
                    error="血糖数据缺失",
                ),
                SkillExecutionResult(
                    skill_name="lipid-assessment",
                    success=True,
                    response="血脂评估：正常",
                ),
            ]

            result = await orchestrator.execute_plan(
                plan=plan,
                user_input=user_input,
            )

            # Verify partial success
            assert not result.success  # Overall success is False when any skill fails
            assert len(result.successful_skills) == 2
            assert len(result.failed_skills) == 1
            assert result.success_rate == 2/3

            # Verify aggregated response contains successful results
            assert result.aggregated_response is not None

            # Verify error tracking
            assert len(result.errors) > 0
            assert "血糖数据缺失" in result.errors[0]


# ============================================================================
# Test direct @skill invocation
# ============================================================================


@pytest.mark.asyncio
async def test_classify_intent_handles_direct_skill_invocation():
    """Test that classify_intent correctly handles @skill_name syntax."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="@hypertension-assessment 请评估我的血压",
        status=AgentStatus.LOADING_PATIENT,
        intent="general_chat",  # Use valid intent type
    )

    result_state = await classify_intent_with_llm_node(state)

    # Verify direct invocation was detected
    assert result_state.suggested_skill == "hypertension-assessment"
    assert result_state.confidence == 1.0
    assert result_state.status == "classifying_intent"


# ============================================================================
# Test execution mode detection
# ============================================================================


def test_execution_mode_detection_from_multi_skill_selection():
    """Test execution mode is correctly detected from multi-skill selection."""
    # Parallel selection
    parallel_selection = MultiSkillSelection(
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
    )

    assert parallel_selection.has_multiple_skills
    assert parallel_selection.execution_suggestion == "parallel"
    assert len(parallel_selection.all_selected_skills) == 2

    # Sequential selection
    sequential_selection = MultiSkillSelection(
        primary=SkillSelection(
            skill_name="assessment-skill",
            confidence=0.9,
            reasoning="Primary",
            should_use_skill=True,
            selection_type="primary",
        ),
        secondary=[
            SkillSelection(
                skill_name="prescription-skill",
                confidence=0.85,
                reasoning="Secondary",
                should_use_skill=True,
                selection_type="secondary",
            ),
        ],
        execution_suggestion="sequential",
    )

    assert sequential_selection.has_multiple_skills
    assert sequential_selection.execution_suggestion == "sequential"

    # Single skill selection
    single_selection = MultiSkillSelection(
        primary=SkillSelection(
            skill_name="hypertension-assessment",
            confidence=0.9,
            reasoning="Primary",
            should_use_skill=True,
            selection_type="primary",
        ),
    )

    assert not single_selection.has_multiple_skills
    assert len(single_selection.all_selected_skills) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
