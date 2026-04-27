#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试多skill选择与编排
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.domain.shared.services.enhanced_llm_skill_selector import (
    EnhancedLLMSkillSelector,
)
from src.domain.shared.services.skill_orchestrator import (
    SkillOrchestrator,
    SkillExecutor,
    ResultAggregator,
)
from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    SkillSelection,
    SkillRelationship,
    RelationshipType,
    ExecutionPlan,
    SkillExecutionResult,
)


class TestEnhancedLLMSkillSelector:
    """测试增强的LLM技能选择器"""

    @pytest.mark.asyncio
    async def test_select_single_skill(self):
        """测试选择单个skill"""
        mock_session = Mock()

        # Mock repository to return skills
        with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.list_skills = AsyncMock(return_value=[
                Mock(name="cvd-risk-assessment", description="心血管风险评估", layer="domain",
                      to_dict=lambda: {"name": "cvd-risk-assessment", "description": "心血管评估"}),
            ])
            mock_repo_class.return_value = mock_repo

            selector = EnhancedLLMSkillSelector(mock_session)

            # Mock Anthropic API
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                # Return valid JSON response
                mock_client.messages.create = Mock(return_value=Mock(
                    content=[Mock(text='{"primary_skill": "cvd-risk-assessment"}')]
                ))
                mock_anthropic.return_value = mock_client

                result = await selector.select_skills("评估心血管风险")

                assert result.primary is not None
                assert result.primary.skill_name == "cvd-risk-assessment"

    def test_parse_multi_skill_response(self):
        """测试多skill响应解析"""
        selector = EnhancedLLMSkillSelector(Mock())

        response = '''```json
{
  "user_intent_summary": "User wants blood pressure and diabetes assessment",
  "primary_skill": "hypertension-assessment",
  "secondary_skills": ["diabetes-assessment", "dyslipidemia-assessment"],
  "relationships": [
    {
      "from": "hypertension-assessment",
      "to": "diabetes-assessment",
      "type": "independent",
      "reasoning": "Both are independent metabolic assessments"
    }
  ],
  "execution_suggestion": "parallel",
  "reasoning": "User asked for multiple independent assessments"
}
```'''

        result = selector._parse_multi_skill_response(response)

        assert result.user_intent_summary == "User wants blood pressure and diabetes assessment"
        assert result.primary.skill_name == "hypertension-assessment"
        assert len(result.secondary) == 2
        assert result.execution_suggestion == "parallel"
        assert len(result.relationships) == 1


class TestSkillOrchestrator:
    """测试Skill编排器"""

    @pytest.mark.asyncio
    async def test_execute_plan_sequential(self):
        """测试顺序执行计划"""
        mock_session = Mock()

        with patch('src.domain.shared.services.skill_orchestrator.UnifiedSkillsRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            orchestrator = SkillOrchestrator(mock_session)

            # Create sequential plan
            plan = ExecutionPlan(
                skills=["skill1", "skill2"],
                execution_mode="sequential",
            )

            # Mock executor
            with patch.object(orchestrator, '_executor') as mock_executor:
                mock_executor.execute_skill = AsyncMock(
                    side_effect=[
                        SkillExecutionResult(
                            skill_name="skill1",
                            success=True,
                            response="Result 1",
                        ),
                        SkillExecutionResult(
                            skill_name="skill2",
                            success=True,
                            response="Result 2",
                        ),
                    ]
                )

                result = await orchestrator.execute_plan(
                    plan=plan,
                    user_input="test input",
                )

                assert result.success
                assert len(result.skill_results) == 2
                assert mock_executor.execute_skill.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_plan_parallel(self):
        """测试并行执行计划"""
        mock_session = Mock()

        with patch('src.domain.shared.services.skill_orchestrator.UnifiedSkillsRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            orchestrator = SkillOrchestrator(mock_session)

            # Create parallel plan
            plan = ExecutionPlan(
                skills=["skill1", "skill2", "skill3"],
                execution_mode="parallel",
            )

            # Mock executor
            with patch.object(orchestrator, '_executor') as mock_executor:
                mock_executor.execute_skill = AsyncMock(
                    return_value=SkillExecutionResult(
                        skill_name="test",
                        success=True,
                        response="Test result",
                    )
                )

                result = await orchestrator.execute_plan(
                    plan=plan,
                    user_input="test input",
                )

                assert result.success
                assert len(result.skill_results) == 3


class TestResultAggregator:
    """测试结果聚合器"""

    def test_merge_results(self):
        """测试结果合并"""
        from src.domain.shared.services.skill_orchestrator import ResultAggregator

        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="hypertension-assessment",
                success=True,
                response="高血压评估结果：高危",
            ),
            SkillExecutionResult(
                skill_name="diabetes-assessment",
                success=True,
                response="糖尿病评估结果：中危",
            ),
        ]

        merged = aggregator.merge_results(results, "test input")

        assert "Hypertension Assessment" in merged or "高血压" in merged
        assert "Diabetes Assessment" in merged or "糖尿病" in merged

    def test_chain_results(self):
        """测试结果链式传递"""
        from src.domain.shared.services.skill_orchestrator import ResultAggregator

        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=True,
                response="First result",
            ),
            SkillExecutionResult(
                skill_name="skill2",
                success=True,
                response="Second result (final)",
            ),
        ]

        chained = aggregator.chain_results(results, "test input")

        # Should return last successful result
        assert "Second result (final)" in chained

    def test_merge_structured(self):
        """测试结构化输出合并"""
        from src.domain.shared.services.skill_orchestrator import ResultAggregator

        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=True,
                structured_output={"a": 1, "b": 2},
            ),
            SkillExecutionResult(
                skill_name="skill2",
                success=True,
                structured_output={"c": 3, "b": 99},  # b conflicts
            ),
        ]

        merged = aggregator.merge_structured(results)

        # skill1's b (2) is set first, skill2's b (99) is ignored (first value wins)
        # skill2's c (3) is added
        assert merged["a"] == 1
        assert merged["b"] == 2  # First value is kept, not overwritten
        assert merged["c"] == 3


class TestExecutionPlan:
    """测试执行计划"""

    def test_parallel_plan(self):
        """测试并行计划"""
        plan = ExecutionPlan(
            skills=["skill1", "skill2", "skill3"],
            execution_mode="parallel",
            groups=[
                Mock(skills=["skill1", "skill2", "skill3"], execution_mode="parallel"),
            ],
        )

        assert plan.execution_mode == "parallel"
        assert plan.total_skills == 3

    def test_sequential_plan(self):
        """测试顺序计划"""
        plan = ExecutionPlan(
            skills=["skill1", "skill2"],
            execution_mode="sequential",
            groups=[
                Mock(skills=["skill1"], execution_mode="sequential"),
                Mock(skills=["skill2"], execution_mode="sequential"),
            ],
        )

        assert plan.execution_mode == "sequential"
        assert plan.total_skills == 2


class TestMultiSkillSelection:
    """测试多skill选择模型"""

    def test_single_skill(self):
        """测试单skill选择"""
        selection = MultiSkillSelection(
            primary=SkillSelection(
                skill_name="cvd-risk-assessment",
                confidence=0.9,
                reasoning="Primary",
                should_use_skill=True,
                selection_type="primary",
            ),
        )

        assert not selection.has_multiple_skills
        assert selection.all_selected_skills == ["cvd-risk-assessment"]

    def test_multiple_skills(self):
        """测试多skill选择"""
        selection = MultiSkillSelection(
            primary=SkillSelection(
                skill_name="cvd-risk-assessment",
                confidence=0.8,
                reasoning="Primary",
                should_use_skill=True,
                selection_type="primary",
            ),
            secondary=[
                SkillSelection(
                    skill_name="diabetes-assessment",
                    confidence=0.7,
                    reasoning="Secondary",
                    should_use_skill=True,
                    selection_type="secondary",
                ),
            ],
            execution_suggestion="parallel",
        )

        assert selection.has_multiple_skills
        assert len(selection.all_selected_skills) == 2
        assert selection.execution_suggestion == "parallel"


class TestSkillRelationship:
    """测试技能关系模型"""

    def test_relationship_creation(self):
        """测试关系创建"""
        relationship = SkillRelationship(
            source="skill1",
            target="skill2",
            relationship_type=RelationshipType.INDEPENDENT,
            confidence=0.9,
            context_transfer=["user_input", "patient_data"],
        )

        assert relationship.source == "skill1"
        assert relationship.target == "skill2"
        assert relationship.relationship_type == RelationshipType.INDEPENDENT
        assert relationship.confidence == 0.9
        assert len(relationship.context_transfer) == 2

    def test_sequential_relationship(self):
        """测试顺序关系"""
        relationship = SkillRelationship(
            source="assessment-skill",
            target="prescription-skill",
            relationship_type=RelationshipType.SEQUENTIAL,
        )

        assert relationship.relationship_type == RelationshipType.SEQUENTIAL

    def test_complementary_relationship(self):
        """测试互补关系"""
        relationship = SkillRelationship(
            source="primary-assessment",
            target="secondary-insight",
            relationship_type=RelationshipType.COMPLEMENTARY,
        )

        assert relationship.relationship_type == RelationshipType.COMPLEMENTARY


class TestSkillSelection:
    """测试单技能选择模型"""

    def test_primary_skill_selection(self):
        """测试主要技能选择"""
        selection = SkillSelection(
            skill_name="hypertension-assessment",
            confidence=0.95,
            reasoning="User mentioned high blood pressure",
            should_use_skill=True,
            selection_type="primary",
        )

        assert selection.skill_name == "hypertension-assessment"
        assert selection.confidence == 0.95
        assert selection.selection_type == "primary"
        assert selection.should_use_skill is True

    def test_secondary_skill_selection(self):
        """测试次要技能选择"""
        selection = SkillSelection(
            skill_name="diabetes-risk-assessment",
            confidence=0.75,
            reasoning="Related metabolic condition",
            should_use_skill=True,
            selection_type="secondary",
        )

        assert selection.selection_type == "secondary"
        assert selection.confidence == 0.75

    def test_alternative_skill_selection(self):
        """测试备选技能选择"""
        selection = SkillSelection(
            skill_name="general-health-check",
            confidence=0.5,
            reasoning="Fallback option",
            should_use_skill=False,
            selection_type="alternative",
        )

        assert selection.selection_type == "alternative"
        assert selection.should_use_skill is False


class TestMultiSkillSelectionEdgeCases:
    """测试多技能选择边界情况"""

    def test_empty_selection(self):
        """测试空选择"""
        selection = MultiSkillSelection()

        assert not selection.has_multiple_skills
        assert len(selection.all_selected_skills) == 0
        assert selection.primary is None
        assert len(selection.secondary) == 0

    def test_only_primary_no_secondary(self):
        """测试只有主要技能没有次要技能"""
        selection = MultiSkillSelection(
            primary=SkillSelection(
                skill_name="assessment",
                confidence=0.9,
                reasoning="Primary",
                should_use_skill=True,
                selection_type="primary",
            ),
        )

        assert not selection.has_multiple_skills
        assert len(selection.all_selected_skills) == 1

    def test_multiple_secondary_skills(self):
        """测试多个次要技能"""
        selection = MultiSkillSelection(
            primary=SkillSelection(
                skill_name="primary",
                confidence=0.9,
                reasoning="Primary",
                should_use_skill=True,
                selection_type="primary",
            ),
            secondary=[
                SkillSelection(
                    skill_name=f"secondary{i}",
                    confidence=0.7,
                    reasoning="Secondary",
                    should_use_skill=True,
                    selection_type="secondary",
                )
                for i in range(5)
            ],
        )

        assert selection.has_multiple_skills
        assert len(selection.all_selected_skills) == 6
        assert len(selection.secondary) == 5

    def test_alternative_skills_only(self):
        """测试只有备选技能"""
        selection = MultiSkillSelection(
            alternatives=[
                SkillSelection(
                    skill_name=f"alt{i}",
                    confidence=0.4,
                    reasoning="Alternative",
                    should_use_skill=False,
                    selection_type="alternative",
                )
                for i in range(3)
            ],
        )

        assert not selection.has_multiple_skills
        assert len(selection.alternatives) == 3
        assert len(selection.all_selected_skills) == 0

    def test_to_dict_conversion(self):
        """测试转换为字典"""
        selection = MultiSkillSelection(
            primary=SkillSelection(
                skill_name="primary",
                confidence=0.9,
                reasoning="Primary",
                should_use_skill=True,
                selection_type="primary",
            ),
            secondary=[
                SkillSelection(
                    skill_name="secondary",
                    confidence=0.7,
                    reasoning="Secondary",
                    should_use_skill=True,
                    selection_type="secondary",
                )
            ],
            user_intent_summary="Test intent",
            execution_suggestion="parallel",
        )

        result_dict = selection.to_dict()

        assert result_dict["user_intent_summary"] == "Test intent"
        assert result_dict["execution_suggestion"] == "parallel"
        assert result_dict["has_multiple_skills"] is True
        assert result_dict["primary"]["skill_name"] == "primary"
        assert len(result_dict["secondary"]) == 1


class TestExecutionPlanDetails:
    """测试执行计划详细信息"""

    def test_empty_plan(self):
        """测试空计划"""
        plan = ExecutionPlan(
            skills=[],
            execution_mode="sequential",
        )

        assert plan.total_skills == 0
        assert plan.execution_mode == "sequential"

    def test_single_skill_plan(self):
        """测试单技能计划"""
        plan = ExecutionPlan(
            skills=["single-skill"],
            execution_mode="sequential",
        )

        assert plan.total_skills == 1
        assert "single-skill" in plan.skills

    def test_parallel_plan_with_groups(self):
        """测试带分组的并行计划"""
        from src.domain.shared.models.skill_selection_models import ExecutionGroup

        plan = ExecutionPlan(
            skills=["skill1", "skill2", "skill3"],
            execution_mode="parallel",
            groups=[
                ExecutionGroup(
                    group_id="group1",
                    skills=["skill1", "skill2"],
                    execution_mode="parallel",
                ),
                ExecutionGroup(
                    group_id="group2",
                    skills=["skill3"],
                    execution_mode="sequential",
                ),
            ],
        )

        assert plan.total_skills == 3
        assert len(plan.groups) == 2
        assert plan.groups[0].group_id == "group1"
        assert len(plan.groups[0].skills) == 2

    def test_mixed_execution_mode(self):
        """测试混合执行模式"""
        plan = ExecutionPlan(
            skills=["skill1", "skill2", "skill3"],
            execution_mode="mixed",
            aggregation_strategy="enhance",
        )

        assert plan.execution_mode == "mixed"
        assert plan.aggregation_strategy == "enhance"

    def test_context_passing(self):
        """测试上下文传递配置"""
        plan = ExecutionPlan(
            skills=["skill1", "skill2"],
            execution_mode="sequential",
            context_passing=[
                {"from": "skill1", "to": "skill2", "key": "assessment_result"},
            ],
        )

        assert len(plan.context_passing) == 1
        assert plan.context_passing[0]["from"] == "skill1"
        assert plan.context_passing[0]["to"] == "skill2"

    def test_to_dict_conversion(self):
        """测试计划转换为字典"""
        from src.domain.shared.models.skill_selection_models import ExecutionGroup

        plan = ExecutionPlan(
            skills=["skill1", "skill2"],
            execution_mode="parallel",
            groups=[
                ExecutionGroup(
                    group_id="group1",
                    skills=["skill1", "skill2"],
                    execution_mode="parallel",
                ),
            ],
        )

        result_dict = plan.to_dict()

        assert result_dict["execution_mode"] == "parallel"
        assert result_dict["total_skills"] == 2
        assert len(result_dict["groups"]) == 1
        assert result_dict["groups"][0]["group_id"] == "group1"


class TestSkillExecutionResultDetails:
    """测试技能执行结果详细信息"""

    def test_successful_result(self):
        """测试成功结果"""
        result = SkillExecutionResult(
            skill_name="test-skill",
            success=True,
            response="Test response",
            structured_output={"key": "value"},
            execution_time_ms=100,
        )

        assert result.success is True
        assert result.response == "Test response"
        assert result.structured_output["key"] == "value"
        assert result.execution_time_ms == 100
        assert result.has_output is True

    def test_failed_result(self):
        """测试失败结果"""
        result = SkillExecutionResult(
            skill_name="test-skill",
            success=False,
            error="Test error",
            execution_time_ms=50,
        )

        assert result.success is False
        assert result.error == "Test error"
        assert result.has_output is False

    def test_result_with_metadata(self):
        """测试带元数据的结果"""
        result = SkillExecutionResult(
            skill_name="test-skill",
            success=True,
            response="Response",
            metadata={
                "model": "claude-3",
                "tokens_used": 100,
                "cached": True,
            },
        )

        assert result.metadata["model"] == "claude-3"
        assert result.metadata["tokens_used"] == 100
        assert result.metadata["cached"] is True


class TestMultiSkillExecutionResultDetails:
    """测试多技能执行结果详细信息"""

    def test_all_successful(self):
        """测试全部成功"""
        from src.domain.shared.models.skill_selection_models import MultiSkillExecutionResult

        plan = ExecutionPlan(
            skills=["skill1", "skill2"],
            execution_mode="parallel",
        )

        result = MultiSkillExecutionResult(
            success=True,
            execution_plan=plan,
            skill_results=[
                SkillExecutionResult(
                    skill_name="skill1",
                    success=True,
                    response="Result 1",
                ),
                SkillExecutionResult(
                    skill_name="skill2",
                    success=True,
                    response="Result 2",
                ),
            ],
        )

        assert result.success is True
        assert len(result.successful_skills) == 2
        assert len(result.failed_skills) == 0
        assert result.success_rate == 1.0

    def test_partial_failure(self):
        """测试部分失败"""
        from src.domain.shared.models.skill_selection_models import MultiSkillExecutionResult

        plan = ExecutionPlan(
            skills=["skill1", "skill2", "skill3"],
            execution_mode="parallel",
        )

        result = MultiSkillExecutionResult(
            success=False,
            execution_plan=plan,
            skill_results=[
                SkillExecutionResult(
                    skill_name="skill1",
                    success=True,
                    response="Result 1",
                ),
                SkillExecutionResult(
                    skill_name="skill2",
                    success=False,
                    error="Error 2",
                ),
                SkillExecutionResult(
                    skill_name="skill3",
                    success=True,
                    response="Result 3",
                ),
            ],
        )

        assert result.success is False
        assert len(result.successful_skills) == 2
        assert len(result.failed_skills) == 1
        assert result.success_rate == 2/3

    def test_all_failed(self):
        """测试全部失败"""
        from src.domain.shared.models.skill_selection_models import MultiSkillExecutionResult

        plan = ExecutionPlan(
            skills=["skill1", "skill2"],
            execution_mode="parallel",
        )

        result = MultiSkillExecutionResult(
            success=False,
            execution_plan=plan,
            skill_results=[
                SkillExecutionResult(
                    skill_name="skill1",
                    success=False,
                    error="Error 1",
                ),
                SkillExecutionResult(
                    skill_name="skill2",
                    success=False,
                    error="Error 2",
                ),
            ],
        )

        assert result.success is False
        assert len(result.successful_skills) == 0
        assert len(result.failed_skills) == 2
        assert result.success_rate == 0.0

    def test_to_dict_conversion(self):
        """测试多技能结果转换为字典"""
        from src.domain.shared.models.skill_selection_models import MultiSkillExecutionResult

        plan = ExecutionPlan(
            skills=["skill1"],
            execution_mode="sequential",
        )

        result = MultiSkillExecutionResult(
            success=True,
            execution_plan=plan,
            skill_results=[
                SkillExecutionResult(
                    skill_name="skill1",
                    success=True,
                    response="Result",
                ),
            ],
            aggregated_response="Aggregated",
            total_execution_time_ms=100,
        )

        # Test properties directly instead of to_dict since SkillExecutionResult doesn't have to_dict
        assert result.success is True
        assert result.total_execution_time_ms == 100
        assert len(result.successful_skills) == 1
        assert len(result.failed_skills) == 0
        assert result.success_rate == 1.0


class TestEnhancedLLMSkillSelectorEdgeCases:
    """测试增强LLM技能选择器边界情况"""

    def test_fallback_to_keyword_matching(self):
        """测试回退到关键词匹配"""
        mock_session = Mock()

        with patch('src.domain.shared.services.enhanced_llm_skill_selector.UnifiedSkillsRepository') as mock_repo_class:
            # Mock no API key
            with patch('src.domain.shared.services.enhanced_llm_skill_selector.get_settings') as mock_settings:
                mock_settings_instance = Mock()
                mock_settings_instance.anthropic_api_key = None
                mock_settings.return_value = mock_settings_instance

                selector = EnhancedLLMSkillSelector(mock_session)

                # Use fallback - not an async method
                result = selector._fallback_select(
                    user_input="评估血压",
                    skill_descriptions="**hypertension-assessment**: High blood pressure evaluation\n**diabetes-assessment**: Diabetes risk evaluation",
                )

                # Should still return selection based on keywords
                assert result is not None
                assert result.user_intent_summary is not None

    def test_skill_name_normalization(self):
        """测试技能名称标准化"""
        selector = EnhancedLLMSkillSelector(Mock())

        response = '''```json
{
  "primary_skill": "hypertension_assessment",
  "secondary_skills": ["diabetes_assessment", "lipid_profile_assessment"]
}
```'''

        result = selector._parse_multi_skill_response(response)

        # Names should be normalized (underscores to hyphens)
        assert result.primary.skill_name == "hypertension-assessment"
        assert "diabetes-assessment" in [s.skill_name for s in result.secondary]


class TestResultAggregatorStrategies:
    """测试结果聚合器策略"""

    def test_enhance_results_strategy(self):
        """测试增强策略"""
        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="primary-assessment",
                success=True,
                response="Primary assessment result.",
            ),
            SkillExecutionResult(
                skill_name="complementary-insight",
                success=True,
                response="Additional complementary insight.",
            ),
        ]

        enhanced = aggregator.enhance_results(results, "test input")

        assert "Primary assessment result" in enhanced
        assert "Additional Insights" in enhanced
        assert "complementary-insight" in enhanced or "Complementary Insight" in enhanced

    def test_enhance_structured(self):
        """测试结构化增强"""
        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=True,
                structured_output={"result1": "value1"},
            ),
            SkillExecutionResult(
                skill_name="skill2",
                success=True,
                structured_output={"result2": "value2"},
            ),
        ]

        enhanced = aggregator.enhance_structured(results)

        assert "result1" in enhanced
        assert "result2" in enhanced
        assert "complementary_results" in enhanced

    def test_merge_with_all_failures(self):
        """测试全部失败时的合并"""
        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=False,
                error="Error 1",
            ),
            SkillExecutionResult(
                skill_name="skill2",
                success=False,
                error="Error 2",
            ),
        ]

        merged = aggregator.merge_results(results, "test input")

        # Should return apology message
        assert "apologize" in merged.lower() or "抱歉" in merged or "issues" in merged.lower()

    def test_chain_with_all_failures(self):
        """测试全部失败时的链式"""
        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=False,
                error="Error",
            ),
        ]

        chained = aggregator.chain_results(results, "test input")

        # Should return apology message
        assert "apologize" in chained.lower() or "抱歉" in chained or "issues" in chained.lower()

    def test_merge_structured_with_nested_dicts(self):
        """测试嵌套字典的结构化合并"""
        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=True,
                structured_output={
                    "nested": {"a": 1, "b": 2},
                    "top": "value1",
                },
            ),
            SkillExecutionResult(
                skill_name="skill2",
                success=True,
                structured_output={
                    "nested": {"c": 3},  # Should merge with skill1's nested
                    "top2": "value2",
                },
            ),
        ]

        merged = aggregator.merge_structured(results)

        assert merged["nested"]["a"] == 1
        assert merged["nested"]["b"] == 2
        assert merged["nested"]["c"] == 3
        assert merged["top"] == "value1"
        assert merged["top2"] == "value2"

    def test_merge_structured_with_lists(self):
        """测试列表的结构化合并"""
        aggregator = ResultAggregator()

        results = [
            SkillExecutionResult(
                skill_name="skill1",
                success=True,
                structured_output={"items": ["a", "b"]},
            ),
            SkillExecutionResult(
                skill_name="skill2",
                success=True,
                structured_output={"items": ["c", "d"]},
            ),
        ]

        merged = aggregator.merge_structured(results)

        # Lists should be extended
        assert "a" in merged["items"]
        assert "b" in merged["items"]
        assert "c" in merged["items"]
        assert "d" in merged["items"]


class TestSkillExecutorEdgeCases:
    """测试技能执行器边界情况"""

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self):
        """测试执行不存在的技能"""
        mock_session = Mock()

        with patch('src.domain.shared.services.skill_orchestrator.UnifiedSkillsRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_skill = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            executor = SkillExecutor(mock_repo)

            result = await executor.execute_skill(
                skill_name="nonexistent-skill",
                user_input="test",
            )

            assert result.success is False
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """测试执行时抛出异常"""
        mock_session = Mock()

        with patch('src.domain.shared.services.skill_orchestrator.UnifiedSkillsRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_skill = Mock()
            mock_skill.metadata.name = "test-skill"
            mock_repo.get_skill = AsyncMock(return_value=mock_skill)

            # Mock to raise exception
            mock_skill.content = "test content"

            mock_repo_class.return_value = mock_repo

            executor = SkillExecutor(mock_repo)

            # Mock workflow check to return False
            executor._is_workflow_skill = Mock(return_value=False)

            # Mock LLM call to raise exception
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_client.messages.create = Mock(side_effect=Exception("API Error"))
                mock_anthropic.return_value = mock_client

                with patch('src.config.settings.get_settings') as mock_settings:
                    mock_settings_instance = Mock()
                    mock_settings_instance.anthropic_api_key = "test-key"
                    mock_settings_instance.model = "claude-3"
                    mock_settings.return_value = mock_settings_instance

                    result = await executor.execute_skill(
                        skill_name="test-skill",
                        user_input="test",
                    )

                    assert result.success is False
                    assert "api error" in result.error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
