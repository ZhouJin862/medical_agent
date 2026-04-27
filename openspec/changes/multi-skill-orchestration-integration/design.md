# Multi-Skill Orchestration Integration - Design

## Context

### Current State

The medical agent currently uses a single-skill execution path:

```
User Input → LLMSkillSelector → ClaudeSkillsExecutor → Single Result
           (one skill)         (one skill)
```

- `LLMSkillSelector`: Returns single `SkillSelection` with one skill
- `ClaudeSkillsExecutor`: Executes one skill, returns one result
- No parallel execution capability
- No multi-skill result aggregation

### Available But Not Integrated

The P1 implementation provides complete multi-skill support:

```
EnhancedLLMSkillSelector → MultiSkillSelection → SkillOrchestrator → MultiSkillExecutionResult
                            (primary + secondary)    (parallel/sequential)      (aggregated)
```

- `EnhancedLLMSkillSelector`: Multi-intent detection with relationship analysis
- `SkillOrchestrator`: Parallel/sequential/mixed execution with context passing
- `ResultAggregator`: Merge/chain/enhance strategies

### Integration Point

Main workflow is in `src/infrastructure/agent/skills_integration.py`:
- `classify_intent_with_llm_node()` — Uses `LLMSkillSelector`
- `execute_claude_skill_node()` — Uses `ClaudeSkillsExecutor`

## Goals / Non-Goals

**Goals:**
1. Enable multi-skill selection when user input contains multiple intents
2. Execute independent skills in parallel for better performance
3. Intelligently aggregate multi-skill results into cohesive responses
4. Maintain backward compatibility for single-skill requests

**Non-Goals:**
1. Streaming execution results (deferred to P2)
2. Caching layer for skill execution results (deferred to P2)
3. Dynamic skill loading at runtime (skills remain pre-registered)

## Decisions

### Decision 1: Replace vs Extend existing selector

**Choice:** Replace `LLMSkillSelector` with `EnhancedLLMSkillSelector`

**Rationale:**
- `EnhancedLLMSkillSelector` is a superset — handles single and multi-skill cases
- Avoids duplicate code paths
- Single integration point simplifies maintenance

**Alternative considered:** Extend `LLMSkillSelector` to support multi-skill
- Rejected: Would require significant refactoring of existing class
- `EnhancedLLMSkillSelector` already exists and is tested

### Decision 2: Execution flow branching

**Choice:** Check multi-skill selection and branch to appropriate executor

```
MultiSkillSelection
    │
    ├─ has_multiple_skills = True → SkillOrchestrator (multi-skill path)
    │
    └─ has_multiple_skills = False → ClaudeSkillsExecutor (single skill path)
```

**Rationale:**
- Preserves existing single-skill path (backward compatibility)
- Avoids overhead of orchestrator for simple cases
- Clear separation of concerns

**Alternative considered:** Always use SkillOrchestrator even for single skill
- Rejected: Adds unnecessary complexity for common case
- Would require modifying SkillOrchestrator to handle single skill

### Decision 3: AgentState modifications

**Choice:** Extend AgentState to support multi-skill results

```python
class AgentState:
    # New fields
    multi_skill_selection: Optional[MultiSkillSelection] = None
    execution_plan: Optional[ExecutionPlan] = None
    multi_skill_result: Optional[MultiSkillExecutionResult] = None
```

**Rationale:**
- Keeps multi-skill metadata separate from legacy single-skill fields
- Allows gradual migration of dependent code
- Maintains compatibility with existing LangGraph state serialization

**Alternative considered:** Reuse existing `suggested_skill` for multi-skill
- Rejected: `suggested_skill` is single string, can't represent multiple skills
- Would break type safety

### Decision 4: Result aggregation timing

**Choice:** Aggregate results in `execute_claude_skill_node()` before returning

**Rationale:**
- Node returns complete, ready-to-use response
- Simplifies downstream nodes (no conditional logic needed)
- Aggregation logic centralized in one place

**Alternative considered:** Aggregate in separate node
- Rejected: Adds unnecessary graph complexity
- Aggregation is tightly coupled with execution

### Decision 5: Error handling strategy

**Choice:** Partial success — continue on individual skill failures

**Rationale:**
- Parallel execution shouldn't fail entirely due to one bad skill
- User receives partial results + error notification
- Matches Claude Code's behavior

**Alternative considered:** Fail fast on any skill error
- Rejected: Poor user experience for parallel independent skills
- Would negate parallel execution benefits

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Updated Workflow                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User Input                                                                │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │           classify_intent_with_llm_node()                          │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│   │  │ EnhancedLLMSkillSelector.select_skills(user_input)             │ │   │
│   │  │                                                                 │ │   │
│   │  │ Returns: MultiSkillSelection                                   │ │   │
│   │  │   - primary: SkillSelection                                     │ │   │
│   │  │   - secondary: List[SkillSelection]                            │ │   │
│   │  │   - relationships: List[SkillRelationship]                     │ │   │
│   │  │   - execution_suggestion: "parallel"|"sequential"|"mixed"      │ │   │
│   │  │   - has_multiple_skills: bool                                  │ │   │
│   │  └─────────────────────────────────────────────────────────────────┘ │   │
│   │                              │                                       │   │
│   │                              ▼                                       │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│   │  │ Create execution plan from selection                           │ │   │
│   │  │ plan = await selector.create_execution_plan(selection)          │ │   │
│   │  └─────────────────────────────────────────────────────────────────┘ │   │
│   │                                                                      │   │
│   │  Store: state.multi_skill_selection, state.execution_plan           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              execute_claude_skill_node()                             │   │
│   │                                                                      │   │
│   │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│   │  │ IF has_multiple_skills:                                        │ │   │
│   │  │   ┌─────────────────────────────────────────────────────────┐  │ │   │
│   │  │   │ orchestrator = SkillOrchestrator(session)                │  │ │   │
│   │  │   │ result = await orchestrator.execute_plan(               │  │ │   │
│   │  │   │   plan=state.execution_plan,                             │  │ │   │
│   │  │   │   user_input=state.user_input,                            │  │ │   │
│   │  │   │   patient_context=...,                                     │  │ │   │
│   │  │   │ )                                                         │  │ │   │
│   │  │   │                                                          │  │ │   │
│   │  │   │ Returns: MultiSkillExecutionResult                        │  │ │   │
│   │  │   │   - success: bool                                         │  │ │   │
│   │  │   │   - skill_results: List[SkillExecutionResult]            │  │ │   │
│   │  │   │   - aggregated_response: str                              │  │ │   │
│   │  │   │   - structured_output: Dict                               │  │ │   │
│   │  │   └─────────────────────────────────────────────────────────┘  │ │   │
│   │  │                                                                 │   │
│   │  │ ELSE:                                                          │   │
│   │  │   ┌─────────────────────────────────────────────────────────┐  │ │   │
│   │  │   │ executor = ClaudeSkillsExecutor(session)                 │  │ │   │
│   │  │   │ result = await executor.execute_skill(...)              │  │ │   │
│   │  │   │                                                         │  │ │   │
│   │  │   │ Convert to MultiSkillExecutionResult for consistency     │  │ │   │
│   │  │   └─────────────────────────────────────────────────────────┘  │ │   │
│   │  └─────────────────────────────────────────────────────────────────┘ │   │
│   │                                                                      │   │
│   │  Extract: state.final_response, state.structured_output               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Multi-Skill Request Flow

```
User: "Check my blood pressure and diabetes risk"
  │
  ▼
EnhancedLLMSkillSelector.select_skills()
  │
  ├─► LLM analyzes input
  ├─► Detects two intents
  │
  ▼
MultiSkillSelection {
  primary: hypertension-assessment
  secondary: [diabetes-assessment]
  relationships: [(hypertension, diabetes, INDEPENDENT)]
  execution_suggestion: "parallel"
  has_multiple_skills: true
}
  │
  ▼
selector.create_execution_plan(selection)
  │
  ▼
ExecutionPlan {
  skills: [hypertension-assessment, diabetes-assessment]
  execution_mode: "parallel"
  aggregation_strategy: "merge"
}
  │
  ▼
SkillOrchestrator.execute_plan(plan, ...)
  │
  ├─► asyncio.gather([
  │     execute_skill(hypertension-assessment, ...),
  │     execute_skill(diabetes-assessment, ...)
  │   ])
  │
  ▼
[SkillExecutionResult, SkillExecutionResult]
  │
  ▼
ResultAggregator.merge_results(results, ...)
  │
  ▼
MultiSkillExecutionResult {
  success: true
  aggregated_response: "Based on my analysis:\n\n**Hypertension Assessment**\n..."
  structured_output: {merged_data}
  skill_results: [...]
}
  │
  ▼
state.final_response = aggregated_response
```

### Single-Skill Request Flow (Backward Compatible)

```
User: "Check my blood pressure"
  │
  ▼
EnhancedLLMSkillSelector.select_skills()
  │
  ├─► LLM analyzes input
  ├─► Detects single intent
  │
  ▼
MultiSkillSelection {
  primary: hypertension-assessment
  secondary: []
  has_multiple_skills: false
}
  │
  ▼
ExecutionPlan {skills: [hypertension-assessment], execution_mode: "sequential"}
  │
  ▼
Branch: has_multiple_skills = False
  │
  ▼
ClaudeSkillsExecutor.execute_skill(...) (existing path)
  │
  ▼
Convert result → MultiSkillExecutionResult (wrapper)
  │
  ▼
state.final_response = response
```

## Integration Points

### Modified Files

1. **src/infrastructure/agent/skills_integration.py**
   - `classify_intent_with_llm_node()`: Use `EnhancedLLMSkillSelector`
   - `execute_claude_skill_node()`: Add multi-skill branch, use `SkillOrchestrator`

2. **src/infrastructure/agent/state.py**
   - Add fields: `multi_skill_selection`, `execution_plan`, `multi_skill_result`

3. **src/infrastructure/agent/nodes.py**
   - Ensure `aggregate_results_node()` handles multi-skill results

### New Imports (skills_integration.py)

```python
from src.domain.shared.services.enhanced_llm_skill_selector import (
    EnhancedLLMSkillSelector,
)
from src.domain.shared.services.skill_orchestrator import (
    SkillOrchestrator,
)
from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    ExecutionPlan,
    MultiSkillExecutionResult,
)
```

## Risks / Trade-offs

### Risk 1: Performance regression for single-skill requests

**Risk:** Additional LLM call for multi-skill analysis may add latency even for single-skill requests.

**Mitigation:**
- `EnhancedLLMSkillSelector` uses the same LLM call pattern as `LLMSkillSelector`
- Both use Anthropic API with similar prompt sizes
- Actual latency difference expected to be <100ms

### Risk 2: Backward compatibility breakage

**Risk:** Existing code expecting single `suggested_skill` string may break.

**Mitigation:**
- Keep `suggested_skill` populated from `selection.primary.skill_name`
- New fields (`multi_skill_selection`, etc.) are optional, typed as `Optional[...]`
- Single-skill path remains functionally identical

### Risk 3: Parallel execution resource contention

**Risk:** Executing 3+ skills in parallel may overwhelm system resources.

**Mitigation:**
- Practical limit: most requests involve 2-3 skills
- asyncio has built-in concurrency control
- Each skill execution is I/O-bound (LLM calls), not CPU-bound

### Risk 4: Debugging complexity

**Risk:** Parallel execution with failures is harder to debug than sequential.

**Mitigation:**
- Comprehensive logging of each skill's execution
- `MultiSkillExecutionResult` includes per-skill success/error
- Structured output preserves individual skill results

## Migration Plan

### Phase 1: Preparation
1. Review existing tests for `skills_integration.py`
2. Identify any code that depends on single-skill behavior

### Phase 2: Implementation
1. Add new imports to `skills_integration.py`
2. Extend `AgentState` with new fields
3. Modify `classify_intent_with_llm_node()` to use `EnhancedLLMSkillSelector`
4. Modify `execute_claude_skill_node()` to branch on multi-skill
5. Add integration tests for multi-skill path

### Phase 3: Testing
1. Run existing unit tests (ensure no regression)
2. Run new multi-skill integration tests
3. Manual testing with sample multi-intent requests

### Rollback Strategy

If issues arise:
1. Revert `skills_integration.py` to use `LLMSkillSelector`
2. Revert `AgentState` changes
3. Keep P1 code in place (not harmful, just unused)

## Open Questions

1. **Should we cache multi-skill selection results?**
   - Consideration: Same user input might repeat in conversation
   - Decision: Deferred to P2 (caching not in scope)

2. **Should we support streaming intermediate results?**
   - Consideration: Users might want to see progress for multi-skill execution
   - Decision: Deferred to P2 (requires async generator API changes)

3. **Maximum number of skills to execute in parallel?**
   - Consideration: Resource usage vs user experience
   - Current approach: No artificial limit (asyncio handles it)
   - Monitor in production and add limit if needed
