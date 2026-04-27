# Implementation Tasks

## 1. AgentState Extensions

- [x] 1.1 Add `multi_skill_selection: Optional[MultiSkillSelection]` field to AgentState
- [x] 1.2 Add `execution_plan: Optional[ExecutionPlan]` field to AgentState
- [x] 1.3 Add `multi_skill_result: Optional[MultiSkillExecutionResult]` field to AgentState
- [x] 1.4 Update AgentState `model_config` to include new fields for serialization

## 2. Import Updates

- [x] 2.1 Add imports for `EnhancedLLMSkillSelector` in `skills_integration.py`
- [x] 2.2 Add imports for `SkillOrchestrator` in `skills_integration.py`
- [x] 2.3 Add imports for `MultiSkillSelection`, `ExecutionPlan`, `MultiSkillExecutionResult` in `skills_integration.py`

## 3. Intent Classification Integration

- [x] 3.1 Replace `LLMSkillSelector` with `EnhancedLLMSkillSelector` in `classify_intent_with_llm_node()`
- [x] 3.2 Update `classify_intent_with_llm_node()` to call `select_skills()` instead of `select_skill()`
- [x] 3.3 Store `MultiSkillSelection` result in `state.multi_skill_selection`
- [x] 3.4 Create `ExecutionPlan` from selection using `selector.create_execution_plan()`
- [x] 3.5 Store `ExecutionPlan` in `state.execution_plan`
- [x] 3.6 Keep `state.suggested_skill` populated for backward compatibility (use `selection.primary.skill_name`)

## 4. Skill Execution Integration

- [x] 4.1 Add conditional branch in `execute_claude_skill_node()` for multi-skill path
- [x] 4.2 Implement multi-skill branch: create `SkillOrchestrator` and call `execute_plan()`
- [x] 4.3 Extract `aggregated_response` from `MultiSkillExecutionResult` into `state.final_response`
- [x] 4.4 Extract `structured_output` from `MultiSkillExecutionResult` into `state.structured_output`
- [x] 4.5 Add `multi_skill_result` to `state` for debugging/telemetry
- [x] 4.6 Ensure single-skill path remains functionally identical (backward compatibility)

## 5. Result Handling

- [x] 5.1 Update `aggregate_results_node()` to handle `MultiSkillExecutionResult` if present
- [x] 5.2 Ensure successful multi-skill execution sets `state.error_message = None`
- [x] 5.3 Ensure partial success (some skills failed) still produces valid response

## 6. Testing - Unit Tests

- [x] 6.1 Write test: `classify_intent_with_llm_node()` returns multi-skill selection for multi-intent input
- [x] 6.2 Write test: `classify_intent_with_llm_node()` returns single skill for single-intent input
- [x] 6.3 Write test: `execute_claude_skill_node()` uses orchestrator for multi-skill selection
- [x] 6.4 Write test: `execute_claude_skill_node()` uses existing executor for single skill
- [x] 6.5 Write test: Multi-skill parallel execution produces aggregated response
- [x] 6.6 Write test: Multi-skill execution with one failure produces partial success result

## 7. Testing - Integration Tests

- [x] 7.1 Write integration test: User requests "blood pressure and diabetes" → both skills executed in parallel
- [x] 7.2 Write integration test: User requests single assessment → single skill executed
- [x] 7.3 Write integration test: Sequential skills execute with context passing
- [x] 7.4 Write integration test: Mixed execution (parallel + sequential) works correctly

## 8. Verification

- [x] 8.1 Run all existing tests to ensure no regression
- [x] 8.2 Run new unit tests (6.1-6.6) - all must pass
- [x] 8.3 Run new integration tests (7.1-7.4) - all must pass
- [x] 8.4 Manual test: "check my blood pressure and diabetes" request produces coherent multi-skill response
- [x] 8.5 Manual test: Single skill request works as before

## 9. Documentation

- [x] 9.1 Update docstring for `classify_intent_with_llm_node()` to mention multi-skill support
- [x] 9.2 Update docstring for `execute_claude_skill_node()` to describe both execution paths
- [x] 9.3 Add inline comments explaining multi-skill vs single-skill branching logic
