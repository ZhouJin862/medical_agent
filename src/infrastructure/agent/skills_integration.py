"""
Skills Integration - Integrates SkillsRegistry with the agent workflow.

Provides updated nodes and utilities for LLM-based skill selection
and Claude Skills execution (including composite skills).
"""
import logging
import time
from typing import Optional, Dict, Any

from src.domain.shared.services.llm_skill_selector import (
    LLMSkillSelector,
    ClaudeSkillsExecutor,
    SkillSelection,
)
from src.domain.shared.services.enhanced_llm_skill_selector import (
    EnhancedLLMSkillSelector,
)
from src.domain.shared.services.skill_orchestrator import (
    SkillOrchestrator,
)
from src.domain.shared.models.skill_selection_models import (
    MultiSkillSelection,
    ExecutionPlan,
    ExecutionGroup,
    MultiSkillExecutionResult,
)
from src.domain.shared.services.composite_skill_executor import (
    CompositeSkillExecutor,
    CompositeSkillConfig,
)
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
)
from src.infrastructure.agent.state import AgentState, AgentStatus, SkillExecutionResult, IntentType, PatientContext, ConversationMemory
from src.infrastructure.database import get_db_session

logger = logging.getLogger(__name__)


async def classify_intent_with_llm_node(state: AgentState) -> AgentState:
    """
    Classify user intent using LLM-based skill selection with multi-skill support.

    This replaces the original classify_intent_node to use the EnhancedLLMSkillSelector,
    which supports both single-skill and multi-skill selection for complex user intents.

    Multi-Skill Support:
        - Detects multiple intents in user input (e.g., "assess blood pressure AND diabetes risk")
        - Returns MultiSkillSelection with primary and secondary skills
        - Creates ExecutionPlan with parallel/sequential/mixed execution modes
        - Stores selection metadata for debugging and analysis

    Args:
        state: Current agent state

    Returns:
        Updated agent state with:
        - intent: Classified intent type (IntentType)
        - suggested_skill: Primary skill name (for backward compatibility)
        - confidence: Selection confidence score
        - multi_skill_selection: Full MultiSkillSelection result as dict
        - execution_plan: ExecutionPlan for multi-skill orchestration
        - selection_metadata: Debugging metadata (reasoning, alternatives, etc.)
    """
    logger.info(f"Classifying intent with LLM: {state.user_input[:50]}...")
    state.status = "classifying_intent"
    state.current_step = "classify_intent"

    try:
        # Skip classification if skill is already specified (e.g. standard API)
        if state.suggested_skill:
            logger.info(f"Skill pre-specified: {state.suggested_skill}, skipping LLM classification")
            return state

        # Check for @skill_name syntax (direct invocation)
        if state.user_input.strip().startswith("@"):
            parts = state.user_input.strip().split(maxsplit=1)
            skill_name = parts[0][1:]  # Remove @
            state.suggested_skill = skill_name
            state.confidence = 1.0
            logger.info(f"Direct skill invocation: @{skill_name}")
            return state

        # Use enhanced LLM-based skill selector with multi-skill support
        selector = None
        async for session in get_db_session():
            selector = EnhancedLLMSkillSelector(session)
            # Process first session only
            break

        if selector:
            # Build conversation context
            conversation_context = None
            if state.conversation_memory and state.conversation_memory.context_summary:
                conversation_context = state.conversation_memory.context_summary

            # Select skills (returns MultiSkillSelection)
            selection = await selector.select_skills(
                user_input=state.user_input,
                conversation_context=conversation_context,
            )

            # Store MultiSkillSelection in state
            state.multi_skill_selection = selection.to_dict() if selection else None

            # Create ExecutionPlan from selection
            execution_plan = await selector.create_execution_plan(
                selection=selection,
                user_input=state.user_input,
            )
            state.execution_plan = execution_plan.to_dict() if execution_plan else None

            # Update state with primary skill for backward compatibility
            if selection.primary and selection.primary.skill_name:
                state.suggested_skill = selection.primary.skill_name
                state.confidence = selection.primary.confidence

                # Map to intent type
                state.intent = _map_skill_to_intent(selection.primary.skill_name)
                logger.info(
                    f"Selected primary skill: {selection.primary.skill_name} "
                    f"(intent: {state.intent.value}, confidence: {selection.primary.confidence})"
                )

                # Store selection metadata for debugging
                state.selection_metadata["selection_reasoning"] = (
                    selection.primary.reasoning if selection.primary else ""
                )
            elif selection.secondary:
                # Multi-skill case with no primary (equal priority skills)
                # Use first secondary skill for backward compatibility
                state.suggested_skill = selection.secondary[0].skill_name
                state.confidence = selection.secondary[0].confidence

                # Map to intent type
                state.intent = _map_skill_to_intent(selection.secondary[0].skill_name)
                logger.info(
                    f"Multi-skill selection (no primary), using first skill: {state.suggested_skill} "
                    f"(intent: {state.intent.value}, confidence: {state.confidence})"
                )
                state.selection_metadata["selection_reasoning"] = "Multi-skill selection with equal priority"
            else:
                state.suggested_skill = None
                state.confidence = 0.0
                state.intent = IntentType.GENERAL_CHAT
                logger.info("No skill selected, using general chat")
                state.selection_metadata["selection_reasoning"] = "No matching skills"

            # Store selection metadata
            state.selection_metadata["user_intent_summary"] = selection.user_intent_summary
            state.selection_metadata["has_multiple_skills"] = selection.has_multiple_skills
            state.selection_metadata["alternative_skills"] = [
                s.skill_name for s in selection.alternatives if s.skill_name
            ]

            # Log multi-skill information
            if selection.has_multiple_skills:
                logger.info(
                    f"Multi-skill selection detected: {len(selection.secondary)} secondary skills, "
                    f"execution_mode: {execution_plan.execution_mode if execution_plan else 'unknown'}"
                )

    except Exception as e:
        logger.error(f"Failed to classify intent: {e}")
        import traceback
        traceback.print_exc()
        state.intent = IntentType.GENERAL_CHAT
        state.confidence = 0.3

    return state


def _map_skill_to_intent(skill_name: str) -> IntentType:
    """Map skill name to intent type."""
    skill_lower = skill_name.lower()

    if any(word in skill_lower for word in ["assessment", "checkup", "evalu"]):
        return IntentType.HEALTH_ASSESSMENT
    elif any(word in skill_lower for word in ["risk", "predict"]):
        return IntentType.RISK_PREDICTION
    elif any(word in skill_lower for word in ["plan", "management"]):
        return IntentType.HEALTH_PLAN
    elif any(word in skill_lower for word in ["triage", "emergency"]):
        return IntentType.TRIAGE
    elif any(word in skill_lower for word in ["medication", "drug", "prescription"]):
        return IntentType.MEDICATION_CHECK
    elif any(word in skill_lower for word in ["service", "recommend"]):
        return IntentType.SERVICE_RECOMMENDATION
    else:
        return IntentType.HEALTH_ASSESSMENT  # Default


async def execute_claude_skill_node(state: AgentState) -> AgentState:
    """
    Execute a Claude Skill with support for composite, multi-skill, and single-skill execution.

    This replaces the original route_skill_node to use Claude Skills with three execution paths:
    1. Composite Skills: Database-defined skills that combine multiple base skills
    2. Multi-Skill Orchestration: P1 integration for parallel/sequential execution of multiple skills
    3. Single Skill: Standard backward-compatible single skill execution

    Execution Path Selection:
        - If skill has base_skills config -> Execute as composite skill
        - If execution_plan has multiple skills -> Use SkillOrchestrator for multi-skill execution
        - Otherwise -> Execute single skill via ClaudeSkillsExecutor

    Multi-Skill Execution (P1 Integration):
        - Uses SkillOrchestrator to execute multiple skills according to ExecutionPlan
        - Supports parallel execution for independent skills
        - Supports sequential execution for dependent skills
        - Aggregates results using merge/chain/enhance strategies
        - Stores aggregated response in state.multi_skill_result

    Args:
        state: Current agent state with suggested_skill and optional execution_plan

    Returns:
        Updated agent state with:
        - final_response: Skill execution response
        - structured_output: Structured result data
        - multi_skill_result: Multi-skill execution result (if applicable)
        - executed_skills: List of individual skill execution results
    """
    logger.info(f"Executing skill: {state.suggested_skill or 'none'}")
    state.status = "executing_skill"
    state.current_step = "execute_skill"

    skill_executed = False

    # Check if we have a multi-skill execution plan OR a single skill
    has_multi_skill_plan = state.execution_plan and len(state.execution_plan.get("skills", [])) > 1
    has_single_skill = state.suggested_skill is not None

    if has_multi_skill_plan or has_single_skill:
        try:
            # Get database session
            session = None
            async for s in get_db_session():
                session = s
                break

            if not session:
                logger.error("Failed to get database session")
                state.error_message = "Database session unavailable"
                return state

            # Path 0: Multi-skill execution (highest priority - P1 integration)
            if has_multi_skill_plan:
                skills = state.execution_plan.get("skills", [])
                logger.info(f"Multi-skill execution: {len(skills)} skills")
                skill_executed = await _execute_multi_skill_plan(
                    session,
                    state.execution_plan,
                    state,
                )
            # Check if this is a composite skill (database skill with base_skills)
            elif state.suggested_skill:
                composite_config = await _check_composite_skill(session, state.suggested_skill)

                if composite_config:
                    # Path 1: Composite skill execution (database-defined skill composition)
                    logger.info(f"Executing composite skill: {state.suggested_skill}")
                    skill_executed = await _execute_composite_skill(
                        session,
                        composite_config,
                        state,
                    )
                else:
                    # Path 2/3: Single skill execution (with or without execution_plan)
                    skill_executed = await _execute_single_skill(
                        session,
                        state,
                    )

        except Exception as e:
            logger.error(f"Failed to execute skill: {e}")
            import traceback
            traceback.print_exc()
            state.error_message = f"Skill execution failed: {str(e)}"

    # If no skill was executed or execution failed, use LLM fallback
    if not skill_executed:
        logger.info("No skill executed, using LLM fallback")
        from src.infrastructure.agent.nodes import _generate_llm_response

        state.final_response = await _generate_llm_response(
            state.user_input,
            state.patient_id,
            state.conversation_memory,
            patient_context=state.patient_context,
            matched_skill=state.suggested_skill,
        )

        # Create structured output
        state.structured_output = {
            "patient_id": state.patient_id,
            "response_type": "llm_fallback",
            "skill_used": state.suggested_skill,
            "confidence": state.confidence,
        }

    return state


# ============================================================================
# Composite Skill Support
# ============================================================================

async def _check_composite_skill(
    session,
    skill_name: str,
) -> Optional[CompositeSkillConfig]:
    """
    Check if a skill is a composite skill (database skill with base_skills).

    Args:
        session: Database session
        skill_name: Name of the skill to check

    Returns:
        CompositeSkillConfig if composite, None otherwise
    """
    try:
        from sqlalchemy import select
        from src.infrastructure.persistence.models.skill_models import SkillModel

        stmt = select(SkillModel).where(
            SkillModel.skill_name == skill_name,
            SkillModel.is_enabled == True,
        )
        result = await session.execute(stmt)
        skill = result.scalar_one_or_none()

        if skill and skill.skill_config:
            # Check if this is a composite skill configuration
            base_skills = skill.skill_config.get("base_skills")
            if base_skills and isinstance(base_skills, list):
                # Parse composite configuration
                return CompositeSkillConfig(
                    base_skills=base_skills,
                    override_settings=skill.skill_config.get("override_settings", {}),
                    business_rules=skill.skill_config.get("business_rules", {}),
                    workflow_config=skill.skill_config.get("workflow_config", {}),
                    display_name=skill.skill_config.get("display_name", skill.display_name),
                    response_style=skill.skill_config.get("response_style", "standard"),
                    execution_mode=skill.skill_config.get("execution_mode", "sequential"),
                )
    except Exception as e:
        logger.error(f"Error checking composite skill: {e}")

    return None


async def _execute_composite_skill(
    session,
    config: CompositeSkillConfig,
    state: AgentState,
) -> bool:
    """
    Execute a composite skill.

    Args:
        session: Database session
        config: Composite skill configuration
        state: Agent state

    Returns:
        True if execution succeeded, False otherwise
    """
    start_time = time.time()

    try:
        # Create unified repository and composite executor
        repository = UnifiedSkillsRepository(session)
        executor = CompositeSkillExecutor(repository)

        # Prepare context
        patient_context = None
        if state.patient_context:
            patient_context = {
                "basic_info": state.patient_context.basic_info,
                "vital_signs": state.patient_context.vital_signs,
                "medical_history": state.patient_context.medical_history,
            }

        conversation_context = None
        if state.conversation_memory and state.conversation_memory.context_summary:
            conversation_context = state.conversation_memory.context_summary

        # Execute composite skill
        result = await executor.execute_composite_skill(
            config=config,
            user_input=state.user_input,
            patient_context=patient_context,
            conversation_context=conversation_context,
        )

        execution_time = int((time.time() - start_time) * 1000)

        # Create skill result
        skill_result = SkillExecutionResult(
            skill_name=f"composite:{config.display_name or 'custom'}",
            success=result.success,
            result_data=result.response,
            error=result.error,
            execution_time=execution_time,
        )

        state.add_skill_result(skill_result)

        if result.success:
            state.final_response = result.response
            state.structured_output = {
                "patient_id": state.patient_id,
                "skill_type": "composite",
                "base_skills_used": result.metadata.get("loaded_skills", []),
                "execution_time_ms": execution_time,
                "execution_mode": result.metadata.get("execution_mode"),
                "confidence": state.confidence,
            }
            logger.info(
                f"Composite skill executed: {len(result.skill_results)} base skills, "
                f"{execution_time}ms"
            )
            return True
        else:
            state.error_message = result.error or "Composite skill execution failed"
            return False

    except Exception as e:
        logger.error(f"Composite skill execution failed: {e}")
        import traceback
        traceback.print_exc()
        state.error_message = f"Composite skill execution failed: {str(e)}"
        return False


async def _execute_multi_skill_plan(
    session,
    execution_plan: Dict[str, Any],
    state: AgentState,
) -> bool:
    """
    Execute multi-sill plan using SkillOrchestrator.

    Args:
        session: Database session
        execution_plan: Execution plan dict with skills, execution_mode, etc.
        state: Agent state

    Returns:
        True if execution succeeded, False otherwise
    """
    start_time = time.time()

    try:
        # Convert dict to ExecutionPlan model
        raw_groups = execution_plan.get("groups", [])
        groups = [
            ExecutionGroup(
                group_id=g.get("group_id", f"group_{i}"),
                skills=g.get("skills", []),
                execution_mode=g.get("execution_mode", "parallel"),
                dependencies=g.get("dependencies", []),
            )
            if isinstance(g, dict) else g
            for i, g in enumerate(raw_groups)
        ]

        plan = ExecutionPlan(
            skills=execution_plan.get("skills", []),
            execution_mode=execution_plan.get("execution_mode", "sequential"),
            groups=groups,
            aggregation_strategy=execution_plan.get("aggregation_strategy", "merge"),
            context_passing=execution_plan.get("context_passing", []),
        )

        # Create orchestrator
        orchestrator = SkillOrchestrator(session)

        # Prepare context
        patient_context = None
        if state.patient_context:
            patient_context = {
                "basic_info": state.patient_context.basic_info,
                "vital_signs": state.patient_context.vital_signs,
                "medical_history": state.patient_context.medical_history,
            }

        conversation_context = None
        if state.conversation_memory and state.conversation_memory.context_summary:
            conversation_context = state.conversation_memory.context_summary

        # Execute plan
        result = await orchestrator.execute_plan(
            plan=plan,
            user_input=state.user_input,
            patient_context=patient_context,
            conversation_context=conversation_context,
        )

        execution_time = int((time.time() - start_time) * 1000)

        # Store multi-skill result in state
        state.multi_skill_result = {
            "success": result.success,
            "aggregated_response": result.aggregated_response,
            "structured_output": result.structured_output,
            "execution_plan": execution_plan,
            "skill_results": [
                {
                    "skill_name": r.skill_name,
                    "success": r.success,
                    "response": r.response,
                    "structured_output": r.structured_output,  # Include structured_output
                    "error": r.error,
                }
                for r in result.skill_results
            ],
            "total_execution_time_ms": result.total_execution_time_ms,
            "errors": result.errors,
        }

        # Update state with aggregated results
        # Even if not all skills succeeded, we still want to show the aggregated response
        if result.aggregated_response:
            state.final_response = result.aggregated_response
            state.structured_output = {
                "patient_id": state.patient_id,
                "skill_type": "multi_skill",
                "execution_plan": execution_plan,
                "skills_executed": [r.skill_name for r in result.skill_results],
                "successful_skills": [r.skill_name for r in result.skill_results if r.success],
                "failed_skills": [r.skill_name for r in result.skill_results if not r.success],
                "execution_time_ms": execution_time,
                "aggregation_strategy": plan.aggregation_strategy,
                "confidence": state.confidence,
            }

            # Add individual skill results to executed_skills
            for skill_result in result.skill_results:
                state.add_skill_result(
                    SkillExecutionResult(
                        skill_name=skill_result.skill_name,
                        success=skill_result.success,
                        result_data=skill_result.response,
                        error=skill_result.error,
                        execution_time=skill_result.execution_time_ms,
                    )
                )

            successful_count = len([r for r in result.skill_results if r.success])
            failed_count = len([r for r in result.skill_results if not r.success])
            logger.info(
                f"Multi-skill execution completed: {len(result.skill_results)} skills, "
                f"{successful_count} successful, {failed_count} failed, "
                f"{execution_time}ms, aggregation={plan.aggregation_strategy}"
            )
            return True
        else:
            # No aggregated response available - this is a complete failure
            state.error_message = result.errors[0] if result.errors else "Multi-skill execution failed"
            logger.error(f"Multi-skill execution failed: {state.error_message}")
            return False

    except Exception as e:
        logger.error(f"Multi-skill execution failed: {e}")
        import traceback
        traceback.print_exc()
        state.error_message = f"Multi-skill execution failed: {str(e)}"
        return False


async def _execute_single_skill(
    session,
    state: AgentState,
) -> bool:
    """
    Execute a single skill using ClaudeSkillsExecutor.

    Args:
        session: Database session
        state: Agent state

    Returns:
        True if execution succeeded, False otherwise
    """
    executor = ClaudeSkillsExecutor(session)

    # Prepare context
    patient_context = None
    if state.patient_context:
        patient_context = {
            "basic_info": state.patient_context.basic_info,
            "vital_signs": state.patient_context.vital_signs,
            "medical_history": state.patient_context.medical_history,
        }

    conversation_context = None
    if state.conversation_memory and state.conversation_memory.context_summary:
        conversation_context = state.conversation_memory.context_summary

    # Execute skill
    start_time = time.time()
    result = await executor.execute_skill(
        skill_name=state.suggested_skill,
        user_input=state.user_input,
        patient_context=patient_context,
        conversation_context=conversation_context,
    )
    execution_time = int((time.time() - start_time) * 1000)

    # Create skill result
    # Use structured_output (dict with modules) for result_data when available,
    # so downstream aggregate_results_node can properly extract modules.
    # Fall back to response (string) otherwise.
    structured_output = result.get("structured_output")
    result_data = structured_output if (
        structured_output and isinstance(structured_output, dict) and "modules" in structured_output
    ) else result.get("response")

    skill_result = SkillExecutionResult(
        skill_name=state.suggested_skill,
        success=result.get("success", False),
        result_data=result_data,
        error=result.get("error"),
        execution_time=execution_time,
    )

    state.add_skill_result(skill_result)

    if result.get("success"):
        # Store response — use better formatter for modules if available
        if structured_output and isinstance(structured_output, dict) and "modules" in structured_output:
            from src.infrastructure.agent.nodes import _format_modules_response
            formatted = _format_modules_response(structured_output, state.patient_context)
            state.final_response = formatted
        else:
            response = result.get("response")
            state.final_response = response if isinstance(response, str) else str(response)

        # Create structured output
        state.structured_output = {
            "patient_id": state.patient_id,
            "skill_used": state.suggested_skill,
            "skill_source": result.get("skill_source"),
            "execution_time_ms": execution_time,
            "confidence": state.confidence,
            "is_incomplete": result.get("is_incomplete", False),
        }

        logger.info(f"Skill executed successfully: {state.suggested_skill}")
        return True
    else:
        logger.error(f"Skill execution failed: {result.get('error')}")
        state.error_message = result.get("error", "Unknown error")
        return False


# ============================================================================
# Utility Functions
# ============================================================================

def should_use_claude_skill(state: AgentState) -> bool:
    """
    Decide whether to use Claude Skills execution or skip.

    Args:
        state: Current agent state

    Returns:
        True if Claude Skills should be used
    """
    # Use skill if:
    # 1. A skill was suggested
    # 2. Confidence is high enough
    # 3. No errors occurred

    return (
        state.suggested_skill is not None
        and state.confidence >= 0.5
        and state.error_message is None
    )


def create_skills_integrated_graph():
    """
    Create a LangGraph workflow with Claude Skills integration.

    Replaces the original graph with LLM-based skill selection
    and Claude Skills execution.

    Returns:
        StateGraph instance
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        raise ImportError(
            "langgraph is required. Install with: pip install langgraph"
        )

    from src.infrastructure.agent.state import AgentState
    from src.infrastructure.agent.nodes import (
        load_patient_node,
        retrieve_memory_node,
        aggregate_results_node,
        save_memory_node,
    )
    from src.infrastructure.agent.nodes.check_basic_questionnaire import check_basic_questionnaire_node

    logger.info("Creating skills-integrated agent workflow graph")

    # Create the state graph
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("load_patient", load_patient_node)
    workflow.add_node("check_basic_questionnaire", check_basic_questionnaire_node)
    workflow.add_node("retrieve_memory", retrieve_memory_node)
    workflow.add_node("classify_intent", classify_intent_with_llm_node)
    workflow.add_node("execute_skill", execute_claude_skill_node)
    workflow.add_node("aggregate", aggregate_results_node)
    workflow.add_node("save_memory", save_memory_node)
    workflow.add_node("error", lambda s: s)

    # Define the entry point
    workflow.set_entry_point("load_patient")

    # Add edges: load_patient → check_basic_questionnaire → (conditional)
    workflow.add_edge("load_patient", "check_basic_questionnaire")

    # Conditional routing after basic questionnaire check
    def route_after_questionnaire_check(state: AgentState) -> str:
        if state.missing_basic_fields and len(state.missing_basic_fields) > 0:
            return "save_memory"
        return "retrieve_memory"

    workflow.add_conditional_edges(
        "check_basic_questionnaire",
        route_after_questionnaire_check,
        {"retrieve_memory": "retrieve_memory", "save_memory": "save_memory"},
    )

    workflow.add_edge("retrieve_memory", "classify_intent")
    workflow.add_edge("classify_intent", "execute_skill")
    workflow.add_edge("execute_skill", "aggregate")

    # Conditional routing for error handling
    def should_continue(state: AgentState) -> str:
        if state.error_message:
            return "error"
        return "save_memory"

    workflow.add_conditional_edges(
        "aggregate",
        should_continue,
        {
            "save_memory": "save_memory",
            "error": "error",
        }
    )

    # Final step
    workflow.add_edge("save_memory", END)
    workflow.add_edge("error", END)

    # Compile the graph
    app = workflow.compile()

    logger.info("Skills-integrated agent workflow graph created successfully")
    return app


class SkillsIntegratedAgent:
    """
    Medical Agent with Claude Skills integration.

    This agent uses:
    1. LLM-based skill selection (intelligent matching)
    2. Claude Skills (progressive disclosure)
    3. Rule engine integration (for enhanced accuracy)
    """

    def __init__(self):
        """Initialize the skills-integrated agent."""
        self._graph = None
        logger.info("SkillsIntegratedAgent initialized")

    @property
    def graph(self):
        """Get or create the workflow graph."""
        if self._graph is None:
            self._graph = create_skills_integrated_graph()
        return self._graph

    async def process(
        self,
        user_input: str,
        patient_id: str,
        party_id: str = None,
        ping_an_health_data: dict = None,
        previous_patient_context: dict = None,
        session_id: str = None,
        suggested_skill: str = None,
        require_basic_questionnaire: bool = False,
    ) -> AgentState:
        """
        Process a user request through the skills-integrated agent.

        Args:
            user_input: User's input message
            patient_id: Patient identifier
            party_id: Optional customer ID from Ping An health archive
            ping_an_health_data: Optional raw health data from Ping An API
            previous_patient_context: Optional previous patient context from session
            session_id: Optional session ID for memory isolation
            suggested_skill: Optional skill name to skip intent classification
            require_basic_questionnaire: If True, check for missing basic fields before skills

        Returns:
            Final agent state with results
        """
        from src.infrastructure.agent.state import create_initial_state

        # Create initial state
        initial_state = create_initial_state(user_input, patient_id, session_id=session_id)

        # Add optional parameters
        if party_id:
            initial_state.party_id = party_id
        if ping_an_health_data:
            initial_state.ping_an_health_data = ping_an_health_data
        if previous_patient_context:
            initial_state.previous_patient_context = previous_patient_context
        if suggested_skill:
            initial_state.suggested_skill = suggested_skill
            initial_state.confidence = 1.0
        if require_basic_questionnaire:
            initial_state.require_basic_questionnaire = True

        logger.info(
            f"Processing request: patient_id={patient_id}, "
            f"input={user_input[:50]}..."
        )

        try:
            # Run the workflow
            result_dict = await self.graph.ainvoke(initial_state)

            # Convert dict back to AgentState
            if isinstance(result_dict, dict):

                # Handle status enum
                if "status" in result_dict and isinstance(result_dict["status"], str):
                    result_dict["status"] = AgentStatus(result_dict["status"])

                # Handle intent enum
                if "intent" in result_dict and isinstance(result_dict["intent"], str):
                    result_dict["intent"] = IntentType(result_dict["intent"])

                # Handle nested models
                if "patient_context" in result_dict and isinstance(result_dict["patient_context"], dict):
                    result_dict["patient_context"] = PatientContext(**result_dict["patient_context"])
                if "conversation_memory" in result_dict and isinstance(result_dict["conversation_memory"], dict):
                    result_dict["conversation_memory"] = ConversationMemory(**result_dict["conversation_memory"])
                if "current_skill_result" in result_dict and isinstance(result_dict["current_skill_result"], dict):
                    result_dict["current_skill_result"] = SkillExecutionResult(**result_dict["current_skill_result"])
                if "executed_skills" in result_dict:
                    result_dict["executed_skills"] = [
                        SkillExecutionResult(**s) if isinstance(s, dict) else s
                        for s in result_dict["executed_skills"]
                    ]

                final_state = AgentState(**result_dict)
            else:
                final_state = result_dict

            logger.info(
                f"Request processed: status={final_state.status}, "
                f"intent={final_state.intent.value if final_state.intent else None}, "
                f"skill_used={final_state.suggested_skill}"
            )

            return final_state

        except Exception as e:
            logger.error(f"Failed to process request: {e}")
            import traceback
            traceback.print_exc()

            initial_state.error_message = str(e)
            initial_state.status = AgentStatus.ERROR
            return initial_state
