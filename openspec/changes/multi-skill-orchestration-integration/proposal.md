# Multi-Skill Orchestration Integration

## Why

The P1 multi-skill selection and orchestration system is fully implemented but completely orphaned—it exists in the codebase but is not integrated into the main agent workflow. Current `skills_integration.py` can only select and execute **one skill at a time**, missing user intents that require multiple assessments (e.g., "check my blood pressure AND diabetes risk"). Meanwhile, the complete P1 implementation with `EnhancedLLMSkillSelector`, `SkillOrchestrator`, and `ResultAggregator` sits unused.

## What Changes

### Core Integration
- Replace `LLMSkillSelector` with `EnhancedLLMSkillSelector` in `classify_intent_with_llm_node()`
- Replace `ClaudeSkillsExecutor` with `SkillOrchestrator` in `execute_claude_skill_node()`
- Add `ResultAggregator` for intelligent multi-skill result merging

### New Capabilities
- Multi-intent detection: Identify when a user request involves multiple skills
- Parallel execution: Run independent skills concurrently using `asyncio.gather()`
- Sequential execution: Chain dependent skills with context passing
- Mixed execution: Combine parallel and sequential based on skill relationships
- Result aggregation: Merge, chain, or enhance multi-skill results

### Backward Compatibility
- Single-skill requests continue to work as before
- Graceful fallback to single-skill path if multi-skill selection fails

### Testing
- Add unit tests for multi-skill selection
- Add integration tests for parallel/sequential execution
- Add tests for result aggregation strategies

## Capabilities

### New Capabilities

- `multi-skill-selection`: LLM-based detection of multiple intents in user input, with relationship analysis between skills (independent/sequential/complementary)

- `skill-orchestration`: Execution of multiple skills according to a plan, supporting parallel, sequential, and mixed execution modes with context passing

- `result-aggregation`: Intelligent merging of results from multiple skills using merge (independent), chain (sequential), or enhance (complementary) strategies

### Modified Capabilities

- `skill-integration`: Update the main agent workflow to support multi-skill execution path (implementation change, no requirement-level spec changes needed)

## Impact

### Code Changes
- `src/infrastructure/agent/skills_integration.py` — Main integration point
- `src/infrastructure/agent/state.py` — May need updates for multi-skill results
- `src/infrastructure/agent/nodes.py` — Ensure compatibility with new flow

### Dependencies
- Existing P1 implementation is fully available and tested:
  - `src/domain/shared/services/enhanced_llm_skill_selector.py`
  - `src/domain/shared/services/skill_orchestrator.py`
  - `src/domain/shared/services/skill_orchestrator.py` (ResultAggregator)
  - `src/domain/shared/models/skill_selection_models.py`

### Performance
- LLM call for multi-skill selection may add ~100-200ms latency
- Parallel execution reduces total time for independent skills (e.g., 2 skills: 5s → 3s)

### Success Metrics
- Multi-skill requests (e.g., "blood pressure AND diabetes") execute matching skills in parallel
- Single-skill requests maintain current performance (no regression)
- All existing tests pass
- New tests achieve >80% coverage for integrated code
