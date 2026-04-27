#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for multi-skill integration in skills_integration.py

Tests cover:
- Multi-skill selection
- Single-skill fallback
- Multi-skill execution path
- Single-skill path
- Parallel execution aggregation
- Partial success handling
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    SkillSelection,
    SkillExecutionResult as DomainSkillResult,
    ExecutionPlan,
    MultiSkillExecutionResult,
)
from src.infrastructure.agent.state import (
    AgentState,
    IntentType,
    AgentStatus,
    PatientContext,
    ConversationMemory,
    SkillExecutionResult as AgentSkillResult,
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
async def test_multi_skill_selection_detection():
    """Test that multi-skill selection is properly detected and stored."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压、糖尿病和血脂风险",
        status=AgentStatus.LOADING_PATIENT,
        intent=None,
    )

    mock_session = Mock()

    # Create multi-skill selection
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
            SkillSelection(
                skill_name="lipid-assessment",
                confidence=0.8,
                reasoning="Tertiary assessment for lipid risk",
                should_use_skill=True,
                selection_type="secondary",
            ),
        ],
        user_intent_summary="User wants blood pressure, diabetes, and lipid assessment",
        execution_suggestion="parallel",
    )

    mock_execution_plan = ExecutionPlan(
        skills=["hypertension-assessment", "diabetes-risk-assessment", "lipid-assessment"],
        execution_mode="parallel",
        aggregation_strategy="merge",
    )

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        with patch('src.infrastructure.agent.skills_integration.EnhancedLLMSkillSelector') as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_skills = AsyncMock(return_value=mock_multi_selection)
            mock_selector.create_execution_plan = AsyncMock(return_value=mock_execution_plan)
            mock_selector_class.return_value = mock_selector

            result_state = await classify_intent_with_llm_node(state)

            # Verify multi-skill selection was detected
            assert result_state.multi_skill_selection is not None
            assert result_state.multi_skill_selection["has_multiple_skills"] is True
            assert result_state.multi_skill_selection["execution_suggestion"] == "parallel"

            # Verify execution plan was created
            assert result_state.execution_plan is not None
            assert result_state.execution_plan["execution_mode"] == "parallel"
            assert result_state.execution_plan["total_skills"] == 3

            # Verify backward compatibility
            assert result_state.suggested_skill == "hypertension-assessment"
            assert result_state.confidence == 0.9


@pytest.mark.asyncio
async def test_single_skill_fallback():
    """Test single-skill fallback when only one intent is detected."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="评估我的血压",
        status=AgentStatus.LOADING_PATIENT,
        intent=None,
    )

    mock_session = Mock()

    # Create single skill selection
    mock_single_selection = MultiSkillSelection(
        primary=SkillSelection(
            skill_name="hypertension-assessment",
            confidence=0.95,
            reasoning="Single intent detected - blood pressure assessment",
            should_use_skill=True,
            selection_type="primary",
        ),
        user_intent_summary="User wants blood pressure assessment",
    )

    mock_execution_plan = ExecutionPlan(
        skills=["hypertension-assessment"],
        execution_mode="sequential",
        aggregation_strategy="single",
    )

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        with patch('src.infrastructure.agent.skills_integration.EnhancedLLMSkillSelector') as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_skills = AsyncMock(return_value=mock_single_selection)
            mock_selector.create_execution_plan = AsyncMock(return_value=mock_execution_plan)
            mock_selector_class.return_value = mock_selector

            result_state = await classify_intent_with_llm_node(state)

            # Verify single skill path
            assert result_state.suggested_skill == "hypertension-assessment"
            assert result_state.confidence == 0.95
            assert result_state.intent == IntentType.HEALTH_ASSESSMENT

            # Verify multi-skill selection exists but indicates single skill
            assert result_state.multi_skill_selection is not None
            assert result_state.multi_skill_selection["has_multiple_skills"] is False


@pytest.mark.asyncio
async def test_no_skill_selected_fallback():
    """Test fallback to general chat when no skill is selected."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="你好",
        status=AgentStatus.LOADING_PATIENT,
        intent=None,
    )

    mock_session = Mock()

    # Create empty selection
    mock_empty_selection = MultiSkillSelection(
        user_intent_summary="General greeting, no specific skill needed",
    )

    mock_execution_plan = ExecutionPlan(
        skills=[],
        execution_mode="sequential",
    )

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        with patch('src.infrastructure.agent.skills_integration.EnhancedLLMSkillSelector') as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_skills = AsyncMock(return_value=mock_empty_selection)
            mock_selector.create_execution_plan = AsyncMock(return_value=mock_execution_plan)
            mock_selector_class.return_value = mock_selector

            result_state = await classify_intent_with_llm_node(state)

            # Verify fallback to general chat
            assert result_state.suggested_skill is None
            assert result_state.confidence == 0.0
            assert result_state.intent == IntentType.GENERAL_CHAT


# ============================================================================
# Test execute_claude_skill_node execution paths
# ============================================================================


@pytest.mark.asyncio
async def test_multi_skill_execution_path():
    """Test multi-skill execution path is used when multiple skills are selected."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压和糖尿病风险",
        suggested_skill="hypertension-assessment",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户", "age": 45},
            vital_signs={},
            medical_history={},
        ),
        multi_skill_selection={
            "has_multiple_skills": True,
            "execution_suggestion": "parallel",
        },
        execution_plan={
            "skills": ["hypertension-assessment", "diabetes-risk-assessment"],
            "execution_mode": "parallel",
            "aggregation_strategy": "merge",
        },
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock SkillOrchestrator for multi-skill execution
        mock_orchestrator = Mock()
        mock_execution_result = MultiSkillExecutionResult(
            success=True,
            execution_plan=ExecutionPlan(
                skills=["hypertension-assessment", "diabetes-risk-assessment"],
                execution_mode="parallel",
            ),
            skill_results=[
                DomainSkillResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="高血压评估结果：正常",
                ),
                DomainSkillResult(
                    skill_name="diabetes-risk-assessment",
                    success=True,
                    response="糖尿病风险评估：低风险",
                ),
            ],
            aggregated_response="综合评估结果：血压正常，糖尿病低风险",
        )
        mock_orchestrator.execute_plan = AsyncMock(return_value=mock_execution_result)

        with patch('src.infrastructure.agent.skills_integration.SkillOrchestrator', return_value=mock_orchestrator):
            result_state = await execute_claude_skill_node(state)

            # Verify multi-skill execution path was used
            assert mock_orchestrator.execute_plan.called
            assert result_state.final_response is not None
            assert "综合评估" in result_state.final_response


@pytest.mark.asyncio
async def test_single_skill_execution_path():
    """Test single-skill execution path is used for single skill selection."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="评估我的血压",
        suggested_skill="hypertension-assessment",
        confidence=0.95,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户", "age": 45},
            vital_signs={},
            medical_history={},
        ),
        multi_skill_selection=None,  # No multi-skill selection
        execution_plan=None,
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock ClaudeSkillsExecutor for single skill execution
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

            # Verify single skill executor was called
            assert mock_executor.execute_skill.called
            assert result_state.final_response is not None
            assert "血压" in result_state.final_response


# ============================================================================
# Test parallel execution aggregation
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_execution_aggregation():
    """Test that parallel execution properly aggregates results from multiple skills."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压、糖尿病和血脂",
        suggested_skill="hypertension-assessment",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户", "age": 50},
            vital_signs={},
            medical_history={},
        ),
        multi_skill_selection={
            "has_multiple_skills": True,
            "execution_suggestion": "parallel",
        },
        execution_plan={
            "skills": ["hypertension-assessment", "diabetes-risk-assessment", "lipid-assessment"],
            "execution_mode": "parallel",
            "aggregation_strategy": "merge",
        },
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock SkillOrchestrator with parallel execution result
        mock_orchestrator = Mock()
        mock_execution_result = MultiSkillExecutionResult(
            success=True,
            execution_plan=ExecutionPlan(
                skills=["hypertension-assessment", "diabetes-risk-assessment", "lipid-assessment"],
                execution_mode="parallel",
            ),
            skill_results=[
                DomainSkillResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="血压评估：收缩压120mmHg，舒张压80mmHg，正常",
                    structured_output={"bp_risk": "normal"},
                ),
                DomainSkillResult(
                    skill_name="diabetes-risk-assessment",
                    success=True,
                    response="糖尿病评估：空腹血糖5.5mmol/L，正常",
                    structured_output={"diabetes_risk": "low"},
                ),
                DomainSkillResult(
                    skill_name="lipid-assessment",
                    success=True,
                    response="血脂评估：总胆固醇5.2mmol/L，正常",
                    structured_output={"lipid_risk": "normal"},
                ),
            ],
            aggregated_response="基于综合评估：\n- 血压：正常\n- 糖尿病风险：低\n- 血脂：正常",
            structured_output={"bp_risk": "normal", "diabetes_risk": "low", "lipid_risk": "normal"},
        )
        mock_orchestrator.execute_plan = AsyncMock(return_value=mock_execution_result)

        with patch('src.infrastructure.agent.skills_integration.SkillOrchestrator', return_value=mock_orchestrator):
            result_state = await execute_claude_skill_node(state)

            # Verify aggregation
            assert result_state.final_response is not None
            assert "综合评估" in result_state.final_response or "Based on" in result_state.final_response

            # Check structured_output contains metadata about multi-skill execution
            assert result_state.structured_output is not None
            assert result_state.structured_output.get("skill_type") == "multi_skill"
            assert result_state.structured_output.get("aggregation_strategy") == "merge"

            # The actual skill structured outputs are in multi_skill_result
            assert result_state.multi_skill_result is not None
            assert result_state.multi_skill_result["structured_output"].get("bp_risk") == "normal"
            assert result_state.multi_skill_result["structured_output"].get("diabetes_risk") == "low"
            assert result_state.multi_skill_result["structured_output"].get("lipid_risk") == "normal"


# ============================================================================
# Test partial success handling
# ============================================================================


@pytest.mark.asyncio
async def test_partial_success_handling():
    """Test that partial success is handled correctly when some skills fail."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压和糖尿病风险",
        suggested_skill="hypertension-assessment",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户", "age": 50},
            vital_signs={},
            medical_history={},
        ),
        multi_skill_selection={
            "has_multiple_skills": True,
            "execution_suggestion": "parallel",
        },
        execution_plan={
            "skills": ["hypertension-assessment", "diabetes-risk-assessment"],
            "execution_mode": "parallel",
            "aggregation_strategy": "merge",
        },
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock SkillOrchestrator with partial success result
        mock_orchestrator = Mock()
        mock_execution_result = MultiSkillExecutionResult(
            success=False,  # Overall is false due to one failure
            execution_plan=ExecutionPlan(
                skills=["hypertension-assessment", "diabetes-risk-assessment"],
                execution_mode="parallel",
            ),
            skill_results=[
                DomainSkillResult(
                    skill_name="hypertension-assessment",
                    success=True,
                    response="血压评估：正常",
                ),
                DomainSkillResult(
                    skill_name="diabetes-risk-assessment",
                    success=False,
                    error="血糖数据缺失，无法完成评估",
                ),
            ],
            aggregated_response="部分评估结果：\n- 血压：正常\n- 糖尿病：评估失败（血糖数据缺失）",
            errors=["diabetes-risk-assessment: 血糖数据缺失，无法完成评估"],
        )
        mock_orchestrator.execute_plan = AsyncMock(return_value=mock_execution_result)

        with patch('src.infrastructure.agent.skills_integration.SkillOrchestrator', return_value=mock_orchestrator):
            result_state = await execute_claude_skill_node(state)

            # Verify partial success handling
            assert result_state.final_response is not None
            # Should contain successful result
            assert "血压" in result_state.final_response
            # Should indicate partial failure
            assert result_state.structured_output is not None


@pytest.mark.asyncio
async def test_all_skills_failure_handling():
    """Test handling when all skills fail."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="请评估我的血压",
        suggested_skill="hypertension-assessment",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户"},
            vital_signs={},
            medical_history={},
        ),
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        # Mock executor that fails
        with patch('src.infrastructure.agent.skills_integration.ClaudeSkillsExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_skill = AsyncMock(
                return_value={
                    "success": False,
                    "error": "技能执行失败：缺少必要的数据",
                }
            )
            mock_executor_class.return_value = mock_executor

            result_state = await execute_claude_skill_node(state)

            # Verify error handling - should fall back to LLM
            assert result_state.final_response is not None
            # Error message should be set
            assert result_state.error_message is not None


# ============================================================================
# Test direct skill invocation (@skill)
# ============================================================================


@pytest.mark.asyncio
async def test_direct_skill_invocation():
    """Test @skill_name syntax for direct skill invocation."""
    from src.infrastructure.agent.skills_integration import classify_intent_with_llm_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="@hypertension-assessment 请评估我的血压",
        status=AgentStatus.LOADING_PATIENT,
        intent=None,
    )

    result_state = await classify_intent_with_llm_node(state)

    # Verify direct invocation
    assert result_state.suggested_skill == "hypertension-assessment"
    assert result_state.confidence == 1.0
    assert result_state.status == AgentStatus.CLASSIFYING_INTENT


# ============================================================================
# Test execution plan variations
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_execution_plan():
    """Test sequential execution plan with context passing."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    state = AgentState(
        patient_id="test_patient_001",
        user_input="先评估然后给出建议",
        suggested_skill="assessment-skill",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户"},
            vital_signs={},
            medical_history={},
        ),
        multi_skill_selection={
            "has_multiple_skills": True,
            "execution_suggestion": "sequential",
        },
        execution_plan={
            "skills": ["assessment-skill", "prescription-skill"],
            "execution_mode": "sequential",
            "aggregation_strategy": "chain",
        },
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        mock_orchestrator = Mock()
        mock_execution_result = MultiSkillExecutionResult(
            success=True,
            execution_plan=ExecutionPlan(
                skills=["assessment-skill", "prescription-skill"],
                execution_mode="sequential",
            ),
            skill_results=[
                DomainSkillResult(
                    skill_name="assessment-skill",
                    success=True,
                    response="评估完成",
                ),
                DomainSkillResult(
                    skill_name="prescription-skill",
                    success=True,
                    response="基于评估结果的建议：...",
                ),
            ],
            aggregated_response="基于评估结果的建议：...",  # Chain returns last
        )
        mock_orchestrator.execute_plan = AsyncMock(return_value=mock_execution_result)

        with patch('src.infrastructure.agent.skills_integration.SkillOrchestrator', return_value=mock_orchestrator):
            result_state = await execute_claude_skill_node(state)

            # Verify sequential execution
            assert mock_orchestrator.execute_plan.called
            assert result_state.final_response is not None


@pytest.mark.asyncio
async def test_mixed_execution_plan():
    """Test mixed execution plan with parallel and sequential groups."""
    from src.infrastructure.agent.skills_integration import execute_claude_skill_node

    from src.domain.shared.models.skill_selection_models import ExecutionGroup

    state = AgentState(
        patient_id="test_patient_001",
        user_input="全面健康检查",
        suggested_skill="primary-assessment",
        confidence=0.9,
        status=AgentStatus.EXECUTING_SKILL,
        intent=IntentType.HEALTH_ASSESSMENT,
        patient_context=PatientContext(
            patient_id="test_patient_001",
            basic_info={"name": "测试用户"},
            vital_signs={},
            medical_history={},
        ),
        multi_skill_selection={
            "has_multiple_skills": True,
            "execution_suggestion": "mixed",
        },
        execution_plan={
            "skills": ["bp-assessment", "diabetes-assessment", "plan-skill"],
            "execution_mode": "mixed",
            "aggregation_strategy": "enhance",
        },
    )

    mock_session = Mock()

    with patch('src.infrastructure.agent.skills_integration.get_db_session') as mock_get_db:
        async def mock_session_gen():
            yield mock_session
        mock_get_db.return_value = mock_session_gen()

        mock_orchestrator = Mock()
        mock_execution_result = MultiSkillExecutionResult(
            success=True,
            execution_plan=ExecutionPlan(
                skills=["bp-assessment", "diabetes-assessment", "plan-skill"],
                execution_mode="mixed",
            ),
            skill_results=[
                DomainSkillResult(
                    skill_name="bp-assessment",
                    success=True,
                    response="血压评估",
                ),
                DomainSkillResult(
                    skill_name="diabetes-assessment",
                    success=True,
                    response="糖尿病评估",
                ),
                DomainSkillResult(
                    skill_name="plan-skill",
                    success=True,
                    response="健康计划",
                ),
            ],
            aggregated_response="主要评估：\n\n## 附加信息\n- 血压评估\n- 糖尿病评估\n\n健康计划：...",
        )
        mock_orchestrator.execute_plan = AsyncMock(return_value=mock_execution_result)

        with patch('src.infrastructure.agent.skills_integration.SkillOrchestrator', return_value=mock_orchestrator):
            result_state = await execute_claude_skill_node(state)

            # Verify mixed execution
            assert mock_orchestrator.execute_plan.called
            assert result_state.final_response is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
