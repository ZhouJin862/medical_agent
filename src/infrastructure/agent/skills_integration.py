"""
Skills Integration - Integrates SkillsRegistry with the agent workflow.

Provides updated nodes and utilities for LLM-based skill selection
and Claude Skills execution (including composite skills).
"""
import asyncio
import json
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
from src.infrastructure.agent.nodes.external_sync import sync_patient_data_node, push_insight_node
from src.infrastructure.database import get_db_session

logger = logging.getLogger(__name__)

# Module-level phase callback registry for incremental SSE push.
# Set by streaming_chat.py before calling agent.process(), consumed by
# _execute_package_assessment. This avoids passing non-serializable
# async callbacks through LangGraph's AgentState.
_phase_callback_registry: Dict[str, Any] = {}


def set_phase_callback(session_id: str, callback):
    """Register a phase callback for a session."""
    _phase_callback_registry[session_id] = callback


def get_phase_callback(session_id: str):
    """Get the phase callback for a session, or None."""
    return _phase_callback_registry.get(session_id)


def clear_phase_callback(session_id: str):
    """Remove the phase callback for a session."""
    _phase_callback_registry.pop(session_id, None)


async def classify_intent_with_llm_node(state: AgentState) -> AgentState:
    """
    Classify user intent using LLM-based skill selection with multi-skill support.
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

            # Path -1: Package assessment orchestration (highest priority)
            if state.suggested_skill == "package@assessment":
                # Get phase callback from registry (set by streaming_chat.py)
                session_id = state.session_id if hasattr(state, 'session_id') and state.session_id else None
                cb = get_phase_callback(session_id) if session_id else None
                skill_executed = await _execute_package_assessment(session, state, phase_callback=cb)

            # Path 0: Multi-skill execution (highest priority - P1 integration)
            elif has_multi_skill_plan:
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
# Package Assessment Orchestration
# ============================================================================

_INSIGHT_SKILLS = [
    "cvd-risk-assessment",
    "hypertension-risk-assessment",
    "hyperglycemia-risk-assessment",
    "hyperlipidemia-risk-assessment",
    "hyperuricemia-risk-assessment",
    "obesity-risk-assessment",
]


def _build_phase_markdown(phase_name: str, data: Dict[str, Any]) -> str:
    """Build markdown for a single phase section from structured_result data.

    Used for incremental SSE push — each phase gets formatted independently
    with a fixed template matching the structured_result structure.

    Args:
        phase_name: One of population_classification, abnormal_indicators,
                    risk_warnings, intervention_prescriptions
        data: Dict containing the phase data (e.g. {"population_classification": {...}})
    """
    lines = []

    if phase_name == "population_classification":
        pc = data.get("population_classification", {})
        if isinstance(pc, str):
            try:
                pc = json.loads(pc)
            except (json.JSONDecodeError, TypeError):
                pc = {}
        if not isinstance(pc, dict):
            pc = {}
        category = pc.get("primary_category", "")
        if category:
            lines.append(f"## 健康人群分组：**{category}**")
            basis_list = pc.get("grouping_basis", [])
            if basis_list:
                lines.append("")
                lines.append("**分组依据：**")
                for b in basis_list:
                    if isinstance(b, dict):
                        disease = b.get("disease", "")
                        note = b.get("note", "")
                        disease_type = b.get("type", "")
                        level = b.get("level", "")
                        if note:
                            detail = f"- {disease}：{note}"
                        elif disease_type and level:
                            detail = f"- {disease}：{disease_type}{level}"
                        elif level:
                            detail = f"- {disease}：{level}"
                        else:
                            detail = f"- {disease}"
                        lines.append(detail)
            lines.append("")

    elif phase_name == "recommended_data_collection":
        items = data.get("recommended_data_collection", [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except (json.JSONDecodeError, TypeError):
                items = []
        if isinstance(items, list) and items:
            # Group by new priority tiers
            critical = [r for r in items if isinstance(r, dict) and r.get("priority") == "critical"]
            important = [r for r in items if isinstance(r, dict) and r.get("priority") == "important"]
            optional = [r for r in items if isinstance(r, dict) and r.get("priority") == "optional"]
            # Legacy: items with "required" priority
            required = [r for r in items if isinstance(r, dict) and r.get("priority") == "required"]
            # Items without recognized new priority → treat as important
            other = [r for r in items if isinstance(r, dict) and r.get("priority") not in ("critical", "important", "optional", "required")]

            if required:
                lines.append("## 缺少必填数据")
                lines.append("")
                for r in required:
                    item = r.get("item", "")
                    reason = r.get("reason", "")
                    line = f"- **{item}**"
                    if reason:
                        line += f"：{reason}"
                    lines.append(line)
                lines.append("")
            if critical:
                lines.append("## 建议尽快补充")
                lines.append("")
                for r in critical:
                    item = r.get("item", "")
                    reason = r.get("reason", "")
                    line = f"- **{item}**"
                    if reason:
                        line += f"：{reason}"
                    lines.append(line)
                lines.append("")
            if important or other:
                lines.append("## 建议近期补充")
                lines.append("")
                for r in (important + other):
                    item = r.get("item", "")
                    reason = r.get("reason", "")
                    line = f"- {item}"
                    if reason:
                        line += f"：{reason}"
                    lines.append(line)
                lines.append("")
            if optional:
                lines.append("## 后续随访可补充")
                lines.append("")
                for r in optional:
                    item = r.get("item", "")
                    reason = r.get("reason", "")
                    line = f"- {item}"
                    if reason:
                        line += f"：{reason}"
                    lines.append(line)
                lines.append("")

    elif phase_name == "abnormal_indicators":
        indicators = data.get("abnormal_indicators", [])
        if isinstance(indicators, str):
            try:
                indicators = json.loads(indicators)
            except (json.JSONDecodeError, TypeError):
                indicators = []
        if isinstance(indicators, dict):
            indicators = indicators.get("indicators", [])
        if isinstance(indicators, list) and indicators:
            lines.append("## 异常指标")
            lines.append("")
            for a in indicators:
                if not isinstance(a, dict):
                    continue
                name = a.get("name", "")
                value = a.get("value", "")
                unit = a.get("unit", "")
                ref = a.get("reference_range", a.get("reference", ""))
                severity = a.get("severity", "")
                line = f"- **{name}**：{value} {unit}"
                if ref:
                    line += f"（参考范围：{ref}）"
                if severity:
                    line += f" — {severity}"
                lines.append(line)
            lines.append("")

    elif phase_name == "risk_warnings":
        warnings = data.get("risk_warnings", [])
        if isinstance(warnings, str):
            try:
                warnings = json.loads(warnings)
            except (json.JSONDecodeError, TypeError):
                warnings = []
        if isinstance(warnings, list) and warnings:
            lines.append("## 风险提示")
            lines.append("")
            for w in warnings:
                if not isinstance(w, dict):
                    continue
                title = w.get("title", "")
                desc = w.get("description", "")
                level = w.get("level", "")
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(level, "⚠️")
                line = f"- {icon} **{title}**"
                if desc:
                    line += f"：{desc}"
                lines.append(line)
                # Render prediction if present
                pred = w.get("prediction")
                if pred and isinstance(pred, dict):
                    pred_parts = []
                    risk_type = pred.get("risk_type", "")
                    timeframe = pred.get("timeframe", "")
                    risk_level = pred.get("risk_level", "")
                    factors = pred.get("key_factors", [])
                    follow_up = pred.get("follow_up", "")
                    if risk_level:
                        pred_parts.append(f"风险等级：{risk_level}")
                    if timeframe:
                        pred_parts.append(f"预测时段：{timeframe}")
                    if factors:
                        pred_parts.append(f"关键因素：{'、'.join(factors)}")
                    if follow_up:
                        pred_parts.append(f"随访建议：{follow_up}")
                    if pred_parts:
                        lines.append(f"  - 预测信息：{'；'.join(pred_parts)}")
            lines.append("")

    elif phase_name == "intervention_prescriptions":
        prescriptions = data.get("intervention_prescriptions", [])
        if isinstance(prescriptions, str):
            try:
                prescriptions = json.loads(prescriptions)
            except (json.JSONDecodeError, TypeError):
                prescriptions = []
        if isinstance(prescriptions, list) and prescriptions:
            lines.append("## 干预建议")
            lines.append("")
            type_order = ["diet", "exercise", "sleep", "monitoring", "medication"]
            type_labels = {
                "diet": "饮食处方",
                "exercise": "运动处方",
                "sleep": "睡眠处方",
                "monitoring": "监测建议",
                "medication": "药物建议",
            }
            by_type: Dict[str, list] = {}
            for p in prescriptions:
                if not isinstance(p, dict):
                    continue
                t = p.get("type", "other")
                by_type.setdefault(t, []).append(p)

            for t in type_order:
                items = by_type.get(t, [])
                if not items:
                    continue
                label = type_labels.get(t, t)
                lines.append(f"### {label}")
                for item in items:
                    contents = item.get("content", [])
                    if isinstance(contents, list):
                        for c in contents:
                            lines.append(f"- {c}")
                    elif isinstance(contents, str):
                        lines.append(f"- {contents}")
                lines.append("")

    return "\n".join(lines) if lines else ""


async def _execute_package_assessment(
    session, state: AgentState,
    phase_callback=None,
) -> bool:
    """Orchestrate package@assessment: population-classification → goal-recommendation → insight skills.

    Phase 1: population-classification
    Phase 2: goal-recommendation → returns goal_selection
    Phase 3: parallel insight skills (after user selects goal)

    Args:
        session: Database session
        state: Agent state
        phase_callback: Optional async callback(phase_name, phase_label, content, structured_data)
                         called after each phase/skill completes for incremental SSE push.
    """
    import asyncio
    from src.domain.questionnaire.services.questionnaire_service import QuestionnaireService

    health_data = state.ping_an_health_data or {}

    # Determine orchestration phase from session data
    phase = health_data.get("_orchestration_phase", 0)
    logger.info(f"Package assessment: phase={phase}, health_data_keys={list(health_data.keys())[:10]}")

    # Also check patient_context for sport_target (set by load_patient_node
    # when LLM extracts it from user's plain text message)
    if phase < 3 and state.patient_context:
        basic_info = getattr(state.patient_context, 'basic_info', None)
        if isinstance(basic_info, dict) and basic_info.get("sport_target"):
            phase = 3
            logger.info(f"Phase boosted to 3 because patient_context.basic_info has sport_target: {basic_info['sport_target']}")

    # Also handles phase=2 when sport_target was submitted (assessment.py bumps to 3)
    if phase >= 3 or (phase == 2 and health_data.get("sport_target")):
        logger.info("Package assessment Phase 3: executing insight skills")
        population_result = health_data.get("_population_result", {})
        selected_goal = health_data.get("sport_target", "")
        # Also check patient_context for sport_target
        if not selected_goal and state.patient_context:
            basic_info = getattr(state.patient_context, 'basic_info', None)
            if isinstance(basic_info, dict) and basic_info.get("sport_target"):
                selected_goal = basic_info["sport_target"]

        # If population_result is missing (e.g. streaming chat path),
        # run Phase 1 first to get population_classification
        if not population_result or not population_result.get("population_classification"):
            logger.info("Phase 3: population_result missing, running Phase 1 first")
            pop_result = await _execute_single_skill_for_orchestration(
                session, state, "population-classification"
            )
            if pop_result:
                pop_structured = _extract_modules(pop_result)
                if pop_structured:
                    modules = pop_structured.get("modules", {})
                    pc = modules.get("population_classification", modules.get("population_group", {}))
                    sr = pop_structured.get("structured_result") or (isinstance(pop_result, dict) and pop_result.get("structured_result"))
                    if isinstance(sr, dict) and sr.get("population_classification"):
                        pc = sr["population_classification"]
                    if pc:
                        population_result = {"population_classification": pc}
                        logger.info(f"Phase 1 re-run: got population_classification primary_category={pc.get('primary_category')}")
                        # Push population_classification via callback
                        if phase_callback:
                            try:
                                await phase_callback(
                                    "population_classification",
                                    "人群分类",
                                    _build_phase_markdown("population_classification", {"population_classification": pc}),
                                    {"population_classification": pc},
                                )
                            except Exception as e:
                                logger.warning(f"Phase 1 re-run callback failed: {e}")
                    else:
                        logger.warning("Phase 1 re-run: population_classification still empty")

        async def _run_insight(skill_name: str) -> tuple:
            try:
                executor = ClaudeSkillsExecutor(session)
                patient_context = None
                if state.patient_context:
                    patient_context = {
                        "basic_info": state.patient_context.basic_info,
                        "vital_signs": state.patient_context.vital_signs,
                        "medical_history": state.patient_context.medical_history,
                    }
                result = await executor.execute_skill(
                    skill_name=skill_name,
                    user_input=state.user_input,
                    patient_context=patient_context,
                )
                return skill_name, result, None
            except Exception as e:
                logger.warning(f"Insight skill {skill_name} failed: {e}")
                return skill_name, None, e

        # Run insight skills with incremental callback push
        # Use as_completed to push each skill result as it finishes
        all_modules = {}
        all_structured_results = []
        tasks_map = {}
        for skill_name in _INSIGHT_SKILLS:
            coro = _run_insight(skill_name)
            task = asyncio.ensure_future(coro)
            tasks_map[task] = skill_name

        for coro in asyncio.as_completed(tasks_map.keys()):
            skill_name, result, error = await coro
            if error or not result:
                continue
            # Extract structured_output from result
            structured = result.get("structured_output") or result.get("final_output") or {}
            if isinstance(structured, dict):
                # Extract modules (for SSE markdown)
                if "modules" in structured:
                    modules = structured["modules"]
                    for k, v in modules.items():
                        if k in all_modules and isinstance(v, list) and isinstance(all_modules[k], list):
                            all_modules[k].extend(v)
                        else:
                            all_modules[k] = v
                # Extract structured_result (for assessment JSON)
                sr = structured.get("structured_result")
                if sr and isinstance(sr, dict):
                    all_structured_results.append(sr)
                    logger.debug(f"Phase 3 skill {skill_name}: extracted structured_result")
            # Also check top-level structured_result (some skills put it there)
            if result.get("structured_result") and isinstance(result["structured_result"], dict):
                # Avoid duplicate if already extracted from structured_output
                sr_from_result = result["structured_result"]
                if sr_from_result not in all_structured_results:
                    all_structured_results.append(sr_from_result)
                    logger.debug(f"Phase 3 skill {skill_name}: extracted structured_result from top-level")

            # (Phase callback for abnormal_indicators is deferred until all
            #  insight skills complete, to avoid pushing duplicate content.)

        # Merge all structured_results into one combined result
        population_classification = population_result.get("population_classification", {})
        merged_sr = _merge_all_structured_results(all_structured_results, population_classification)

        # Push abnormal_indicators once after all insight skills complete
        if phase_callback:
            try:
                final_indicators = _deduplicate_indicators(
                    _normalise_indicators(merged_sr.get("abnormal_indicators", []))
                )
                if final_indicators:
                    await phase_callback(
                        "abnormal_indicators",
                        "异常指标",
                        _build_phase_markdown("abnormal_indicators", {"abnormal_indicators": final_indicators}),
                        {"abnormal_indicators": final_indicators},
                    )
            except Exception as e:
                logger.warning(f"Phase 3 abnormal_indicators callback failed: {e}")

        # Phase 3.5 + 3.6: Execute all 3 pure-LLM skills in parallel
        # (risk-warning, prescription-recommendation, data-recommendation)
        # All three take the same inputs (structured_result + health_data) with no
        # inter-dependencies, so they can run concurrently via asyncio.gather.

        # Build shared inputs once
        llm_input = json.dumps({
            "structured_result": merged_sr,
            "health_data": health_data,
        }, ensure_ascii=False)
        patient_context = None
        if state.patient_context:
            patient_context = {
                "basic_info": state.patient_context.basic_info,
                "vital_signs": state.patient_context.vital_signs,
                "medical_history": state.patient_context.medical_history,
            }

        # Build health_data_for_llm for data-recommendation (needs patient_context fields)
        _pc = {}
        if state.patient_context:
            _bi = state.patient_context.basic_info
            if isinstance(_bi, str):
                try: _bi = json.loads(_bi)
                except (json.JSONDecodeError, TypeError): _bi = {}
            elif not isinstance(_bi, dict): _bi = {}
            _vs = state.patient_context.vital_signs
            if isinstance(_vs, str):
                try: _vs = json.loads(_vs)
                except (json.JSONDecodeError, TypeError): _vs = {}
            elif not isinstance(_vs, dict): _vs = {}
            _mh = state.patient_context.medical_history
            if isinstance(_mh, str):
                try: _mh = json.loads(_mh)
                except (json.JSONDecodeError, TypeError): _mh = {}
            elif not isinstance(_mh, dict): _mh = {}
            _pc = {"basic_info": _bi, "vital_signs": _vs, "medical_history": _mh}
        _basic_info = _pc.get("basic_info", {})
        if not isinstance(_basic_info, dict):
            _basic_info = {}
        health_data_for_llm = {
            "age": _basic_info.get("age"),
            "gender": _basic_info.get("gender"),
            "sport_target": _basic_info.get("sport_target"),
            "disease_labels": _basic_info.get("disease_labels", []),
        }
        dl = health_data_for_llm.get("disease_labels", [])
        if isinstance(dl, str):
            health_data_for_llm["disease_labels"] = [dl]

        async def _run_llm_skill(skill_name: str) -> Dict[str, Any]:
            """Run a single LLM skill and return its result."""
            try:
                executor = ClaudeSkillsExecutor(session)
                return await executor.execute_skill(
                    skill_name=skill_name,
                    user_input=llm_input,
                    patient_context=patient_context,
                )
            except Exception as e:
                logger.warning(f"Phase 3.5 LLM skill {skill_name} failed: {e}")
                return {"success": False, "error": str(e), "skill_name": skill_name}

        async def _run_data_recommendation() -> list:
            """Run data-recommendation skill and return ranked items."""
            raw_rdc = merged_sr.get("recommended_data_collection", [])
            if not raw_rdc:
                return []
            try:
                from src.domain.shared.services.llm_risk_prescription_skills import generate_data_recommendations
                ranked = await generate_data_recommendations(
                    raw_items=raw_rdc,
                    structured_result=merged_sr,
                    health_data=health_data_for_llm,
                )
                logger.info(f"Phase 3.6 LLM data-recommendation: {len(raw_rdc)} raw → {len(ranked)} ranked")
                return ranked
            except Exception as e:
                import traceback
                logger.warning(f"Phase 3.6 LLM data-recommendation failed, using raw items: {e}\n{traceback.format_exc()}")
                return raw_rdc

        # Launch all 3 LLM calls concurrently
        rw_result, pr_result, ranked_rdc = await asyncio.gather(
            _run_llm_skill("risk-warning"),
            _run_llm_skill("prescription-recommendation"),
            _run_data_recommendation(),
        )

        # Process risk-warning result
        if rw_result.get("success") and rw_result.get("structured_output"):
            so = rw_result["structured_output"]
            if "risk_warnings" in so:
                merged_sr["risk_warnings"] = so["risk_warnings"]
                if phase_callback:
                    try:
                        await phase_callback(
                            "risk_warnings", "风险预警",
                            _build_phase_markdown("risk_warnings", {"risk_warnings": so["risk_warnings"]}),
                            {"risk_warnings": so["risk_warnings"]},
                        )
                    except Exception as e:
                        logger.warning(f"Phase 3.5 risk_warnings callback failed: {e}")
        logger.info(f"Phase 3.5 LLM skill risk-warning: success={rw_result.get('success')}")

        # Process prescription-recommendation result
        if pr_result.get("success") and pr_result.get("structured_output"):
            so = pr_result["structured_output"]
            if "intervention_prescriptions" in so:
                merged_sr["intervention_prescriptions"] = so["intervention_prescriptions"]
                if phase_callback:
                    try:
                        await phase_callback(
                            "intervention_prescriptions", "干预建议",
                            _build_phase_markdown("intervention_prescriptions", {"intervention_prescriptions": so["intervention_prescriptions"]}),
                            {"intervention_prescriptions": so["intervention_prescriptions"]},
                        )
                    except Exception as e:
                        logger.warning(f"Phase 3.5 prescriptions callback failed: {e}")
        logger.info(f"Phase 3.5 LLM skill prescription-recommendation: success={pr_result.get('success')}")

        # Process data-recommendation result
        if ranked_rdc:
            merged_sr["recommended_data_collection"] = ranked_rdc
            if phase_callback:
                try:
                    await phase_callback(
                        "recommended_data_collection", "推荐补充数据",
                        _build_phase_markdown("recommended_data_collection", {"recommended_data_collection": ranked_rdc}),
                        {"recommended_data_collection": ranked_rdc},
                    )
                    logger.info(f"Phase 3.6 pushed recommended_data_collection: {len(ranked_rdc)} items")
                except Exception as e:
                    logger.warning(f"Phase 3.6 recommended_data_collection callback failed: {e}")

        state.structured_output = {
            "population_classification": merged_sr.get("population_classification", population_classification),
            "modules": all_modules,
            "structured_result": merged_sr,
            "sport_target": selected_goal,
        }
        state.final_response = json.dumps(state.structured_output, ensure_ascii=False, default=str)
        logger.info(f"Package assessment Phase 3 complete: {len(all_structured_results)} structured_results, {len(all_modules)} modules")
        return True

    # ---- Phase 1: population-classification ----
    logger.info("Package assessment Phase 1: population-classification")
    pop_result = await _execute_single_skill_for_orchestration(
        session, state, "population-classification"
    )
    if not pop_result:
        logger.error("population-classification failed, falling back to single skill execution")
        return False

    # Extract population classification result
    pop_structured = _extract_modules(pop_result)
    population_classification = {}
    recommended_data_collection = []
    if pop_structured:
        modules = pop_structured.get("modules", {})
        # population_classifier uses "population_group" key in modules,
        # but downstream expects "population_classification"
        population_classification = modules.get("population_classification", modules.get("population_group", {}))
        # Also check structured_result (more detailed grouping_basis)
        sr = pop_structured.get("structured_result") or (isinstance(pop_result, dict) and pop_result.get("structured_result"))
        if isinstance(sr, dict) and sr.get("population_classification"):
            population_classification = sr["population_classification"]
        # Extract recommended_data_collection from structured_result
        if isinstance(sr, dict) and sr.get("recommended_data_collection"):
            recommended_data_collection = sr["recommended_data_collection"]

    # Phase 1 callback: push population_classification result
    if phase_callback and population_classification:
        try:
            await phase_callback(
                "population_classification",
                "人群分类",
                _build_phase_markdown("population_classification", {"population_classification": population_classification}),
                {"population_classification": population_classification},
            )
        except Exception as e:
            logger.warning(f"Phase 1 callback failed: {e}")

    # Phase 1.1: Skip raw recommended_data_collection push
    # (Phase 3.6 will push LLM-ranked results instead)

    # ---- Phase 2: goal-recommendation ----
    logger.info("Package assessment Phase 2: goal-recommendation")

    # Load goal pool from DB
    goal_pool = []
    try:
        questionnaire = await QuestionnaireService.get_by_type(session, "health-goals")
        if questionnaire and questionnaire.questions:
            for q in questionnaire.questions:
                if q.get("id") == "sport_target1":
                    goal_pool = q.get("options", [])
                    break
    except Exception as e:
        logger.warning(f"Failed to load goal pool: {e}")

    # Build goal-recommender input
    abnormal_indicators = {}
    disease_prediction = []
    symptoms = health_data.get("symptoms", [])

    goal_input = {
        "population_classification": population_classification,
        "abnormal_indicators": abnormal_indicators,
        "disease_prediction": disease_prediction,
        "symptoms": symptoms,
        "goal_pool": goal_pool,
    }

    # Execute via ClaudeSkillsExecutor — supports both script and LLM paths
    recommended_goals = []
    try:
        executor = ClaudeSkillsExecutor(session)
        patient_context = None
        if state.patient_context:
            patient_context = {
                "basic_info": state.patient_context.basic_info,
                "vital_signs": state.patient_context.vital_signs,
                "medical_history": state.patient_context.medical_history,
            }
        goal_result = await executor.execute_skill(
            skill_name="goal-recommendation",
            user_input=json.dumps(goal_input, ensure_ascii=False),
            patient_context=patient_context,
        )
        if goal_result and isinstance(goal_result, dict):
            # Workflow path: structured_output / final_output
            structured = goal_result.get("structured_output") or goal_result.get("final_output") or {}
            if isinstance(structured, dict):
                recommended_goals = structured.get("recommended_goals", [])
            # Direct key in result
            if not recommended_goals:
                recommended_goals = goal_result.get("recommended_goals", [])
            # LLM path: response is a string — try parse JSON from it
            if not recommended_goals:
                response_str = goal_result.get("response", "")
                if isinstance(response_str, str) and response_str.strip().startswith("{"):
                    try:
                        parsed = json.loads(response_str)
                        recommended_goals = parsed.get("recommended_goals", [])
                    except (json.JSONDecodeError, ValueError):
                        pass
                elif isinstance(response_str, str) and response_str.strip().startswith("["):
                    try:
                        recommended_goals = json.loads(response_str)
                    except (json.JSONDecodeError, ValueError):
                        pass
    except Exception as e:
        logger.warning(f"Goal-recommendation skill failed: {e}")

    if not recommended_goals:
        # Fallback: use all goals
        recommended_goals = goal_pool[:4]
        logger.info(f"Goal recommendation fallback: using {len(recommended_goals)} goals")

    # Return goal_selection status
    sport_question = {
        "questionnaire_type": "health-goals",
        "id": "sport_target1",
        "type": "single",
        "componentType": "image",
        "title": "选择您的运动目标",
        "options": recommended_goals,
        "required": True,
        "showNavigation": True,
        "nextButtonText": "加油我可以",
    }

    state.structured_output = {
        "status": "goal_selection",
        "questionnaire_type": "health-goals",
        "current_question": sport_question,
        "population_classification": population_classification,
        "_orchestration_phase": 2,
    }
    state.final_response = json.dumps(state.structured_output, ensure_ascii=False, default=str)
    logger.info(f"Package assessment Phase 2 complete: {len(recommended_goals)} goals recommended")
    return True


async def _execute_single_skill_for_orchestration(
    session, state: AgentState, skill_name: str,
) -> Optional[Dict]:
    """Execute a single skill and return its result dict."""
    try:
        executor = ClaudeSkillsExecutor(session)
        patient_context = None
        if state.patient_context:
            patient_context = {
                "basic_info": state.patient_context.basic_info,
                "vital_signs": state.patient_context.vital_signs,
                "medical_history": state.patient_context.medical_history,
            }

        result = await executor.execute_skill(
            skill_name=skill_name,
            user_input=state.user_input,
            patient_context=patient_context,
        )

        structured = result.get("structured_output")
        if structured and isinstance(structured, dict) and "modules" in structured:
            return structured

        # Try extracting from result_data
        result_data = result.get("result_data")
        if isinstance(result_data, dict):
            return result_data

        return result
    except Exception as e:
        logger.error(f"Failed to execute skill {skill_name}: {e}")
        return None


def _merge_all_structured_results(
    structured_results: list,
    population_classification: dict,
) -> dict:
    """Merge structured_result dicts from multiple skills into one combined result.

    - Array fields (disease_prediction, abnormal_indicators, etc.) are concatenated.
    - abnormal_indicators items are normalised to a unified schema.
    - intervention_prescriptions are deduplicated by type (merging content lists).
    - population_classification is taken from the dedicated skill result.
    """
    if not structured_results:
        return {
            "population_classification": population_classification or {
                "primary_category": "健康",
                "grouping_basis": [],
            },
            "recommended_data_collection": [],
            "abnormal_indicators": [],
            "disease_prediction": [],
            "intervention_prescriptions": [],
            "risk_warnings": [],
        }

    merged: Dict[str, Any] = {}
    array_keys = [
        "disease_prediction",
        "abnormal_indicators",
        "intervention_prescriptions",
        "recommended_data_collection",
        "risk_warnings",
    ]

    # Start with first structured_result as base
    merged.update(structured_results[0])

    # Concat array fields from remaining results
    for key in array_keys:
        primary_list = merged.get(key, [])
        if not isinstance(primary_list, list):
            primary_list = []
        for extra in structured_results[1:]:
            extra_list = extra.get(key, [])
            if isinstance(extra_list, list):
                primary_list.extend(extra_list)
        merged[key] = primary_list

    # --- Post-merge clean-up ---

    # 1. Normalise + deduplicate abnormal_indicators
    merged["abnormal_indicators"] = _deduplicate_indicators(
        _normalise_indicators(merged.get("abnormal_indicators", []))
    )

    # 2. Deduplicate intervention_prescriptions by canonical type
    merged["intervention_prescriptions"] = _deduplicate_prescriptions(
        merged.get("intervention_prescriptions", [])
    )

    # 3. Deduplicate risk_warnings by title
    merged["risk_warnings"] = _deduplicate_risk_warnings(merged.get("risk_warnings", []))

    # 4. Deduplicate recommended_data_collection by item name
    merged["recommended_data_collection"] = _deduplicate_recommended_data(
        merged.get("recommended_data_collection", [])
    )

    # 5. Use population_classification from dedicated skill
    if population_classification:
        merged["population_classification"] = population_classification

    return merged


# ---------------------------------------------------------------------------
# Indicator normalisation
# ---------------------------------------------------------------------------

def _deduplicate_indicators(indicators: list) -> list:
    """Remove duplicate indicators by normalised name.

    Multiple skills may report the same indicator (e.g. 收缩压).
    Keep the one with the richest field set (prefer format-A with severity/summary).
    """
    seen: Dict[str, dict] = {}  # normalised_name → best item
    for item in indicators:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "").strip()
        if not name:
            continue
        # Normalise key: strip parenthetical qualifiers for matching
        # e.g. "总胆固醇(TC)" → "总胆固醇", "低密度脂蛋白胆固醇(LDL-C)" → "低密度脂蛋白"
        key = name
        for short, long in [
            ("总胆固醇", "总胆固醇"), ("低密度脂蛋白", "低密度脂蛋白"),
            ("高密度脂蛋白", "高密度脂蛋白"), ("甘油三酯", "甘油三酯"),
        ]:
            if long in name:
                key = long
                break
        # Check if this name already tracked under a variant
        matched_key = None
        for existing_key in seen:
            if key in existing_key or existing_key in key:
                matched_key = existing_key
                break
        if matched_key is None:
            matched_key = key
        # Prefer item with more fields (format-A over format-B)
        existing = seen.get(matched_key)
        if existing is None or len(item) > len(existing):
            seen[matched_key] = item
        # If same field count, prefer one with severity="high" over "elevated"
        elif existing.get("severity") == "elevated" and item.get("severity") == "high":
            seen[matched_key] = item
    return list(seen.values())


def _deduplicate_risk_warnings(warnings: list) -> list:
    """Remove duplicate risk_warnings by title, keeping the one with highest level."""
    level_order = {"high": 0, "中高": 1, "medium": 2, "中危": 2, "low": 3, "低危": 3}
    seen: Dict[str, dict] = {}  # title → best item
    for w in warnings:
        if not isinstance(w, dict):
            continue
        title = w.get("title", "")
        if not title:
            continue
        existing = seen.get(title)
        if existing is None:
            seen[title] = w
        else:
            # Keep higher severity
            cur_rank = level_order.get(existing.get("level", ""), 99)
            new_rank = level_order.get(w.get("level", ""), 99)
            if new_rank < cur_rank:
                seen[title] = w
    return list(seen.values())


def _deduplicate_recommended_data(items: list) -> list:
    """Remove duplicate recommended_data_collection items by item name."""
    seen: Dict[str, dict] = {}  # item name → first occurrence
    for r in items:
        if not isinstance(r, dict):
            continue
        name = r.get("item", "")
        if not name:
            continue
        if name not in seen:
            seen[name] = r
    return list(seen.values())


def _normalise_indicators(indicators: list) -> list:
    """Normalise indicator items to a unified schema.

    Skill scripts emit two formats:
    - Format A (hypertension/obesity): {name, value, unit, reference, severity, summary}
    - Format B (blood-sugar/lipid/uric-acid): {indicator, value, reference}

    We convert everything to Format A, inferring ``clinical_note`` from the
    indicator name so that ``transform_abnormal_indicators`` can later group
    them into warnings.
    """
    # Keyword → clinical_note mapping for warning grouping
    _NAME_TO_CLINICAL_NOTE = {
        "收缩压": "高血压", "舒张压": "高血压", "血压": "高血压",
        "空腹血糖": "血糖异常", "餐后血糖": "血糖异常", "糖化血红蛋白": "血糖异常",
        "血糖": "血糖异常",
        "总胆固醇": "血脂异常", "甘油三酯": "血脂异常", "低密度脂蛋白": "血脂异常",
        "高密度脂蛋白": "血脂异常", "胆固醇": "血脂异常", "TC": "血脂异常",
        "TG": "血脂异常", "LDL": "血脂异常", "HDL": "血脂异常",
        "血尿酸": "高尿酸", "尿酸": "高尿酸",
        "BMI": "BMI≥24", "体脂": "BMI≥24", "腰围": "BMI≥24",
    }

    normalised = []
    for item in indicators:
        if not isinstance(item, dict):
            continue
        # Already in Format A — just add clinical_note if missing
        if "name" in item:
            n = item.get("name", "")
            note = item.get("clinical_note", "")
            if not note:
                for kw, cn in _NAME_TO_CLINICAL_NOTE.items():
                    if kw in n:
                        note = cn
                        break
            new_item = dict(item)
            if note:
                new_item["clinical_note"] = note
            normalised.append(new_item)
            continue
        # Format B — convert to Format A
        if "indicator" in item:
            raw_name = item.get("indicator", "")
            raw_value = item.get("value", "")
            ref = item.get("reference", "")
            # Parse numeric value + unit from "152.0 mmHg"
            num_val = raw_value
            unit = ""
            if isinstance(raw_value, str):
                parts = raw_value.strip().split(None, 1)
                try:
                    num_val = float(parts[0])
                    unit = parts[1] if len(parts) > 1 else ""
                except (ValueError, IndexError):
                    num_val = raw_value
            # Infer severity from name + value
            severity = "elevated"
            # Infer clinical_note
            note = ""
            for kw, cn in _NAME_TO_CLINICAL_NOTE.items():
                if kw in raw_name:
                    note = cn
                    break
            normalised.append({
                "name": raw_name,
                "value": num_val,
                "unit": unit,
                "reference": ref,
                "severity": severity,
                "summary": f"{raw_name}{raw_value}，偏高" if isinstance(raw_value, str) else f"{raw_name}{num_val}，偏高",
                "clinical_note": note,
            })
            continue
        # Unknown format — pass through
        normalised.append(item)
    return normalised


# ---------------------------------------------------------------------------
# Prescription deduplication
# ---------------------------------------------------------------------------

# Canonical type mapping: Chinese / English variants → canonical key
_PRESCRIPTION_TYPE_MAP = {
    "饮食": "diet", "diet": "diet",
    "运动": "exercise", "exercise": "exercise",
    "睡眠": "sleep", "sleep": "sleep",
    "监测": "monitoring", "monitoring": "monitoring",
    "药物": "medication", "药物治疗": "medication", "medication": "medication",
    "用药": "medication",
    "饮水": "hydration",
}

_PRESCRIPTION_TYPE_LABELS = {
    "diet": "饮食处方",
    "exercise": "运动处方",
    "sleep": "睡眠处方",
    "monitoring": "监测建议",
    "medication": "用药建议",
    "hydration": "饮水建议",
    "other": "其他建议",
}

_PRESCRIPTION_PRIORITY = {"high": 0, "中": 1, "medium": 1, "低": 2, "low": 2}


def _deduplicate_prescriptions(prescriptions: list) -> list:
    """Merge prescriptions by canonical type, deduplicating content items."""
    if not prescriptions:
        return []

    # Group by canonical type
    by_type: Dict[str, dict] = {}  # canonical_type → {content: list, priority: str, title: str}
    for p in prescriptions:
        if not isinstance(p, dict):
            continue
        raw_type = p.get("type", "other")
        canonical = _PRESCRIPTION_TYPE_MAP.get(raw_type, raw_type)
        contents = p.get("content", [])
        if isinstance(contents, str):
            contents = [contents]
        if canonical not in by_type:
            by_type[canonical] = {"content": [], "priority": "medium", "title": ""}
        # Extend content (dedupe by exact string match)
        seen = set(by_type[canonical]["content"])
        for c in contents:
            if c not in seen:
                by_type[canonical]["content"].append(c)
                seen.add(c)
        # Keep highest priority
        cur_pri = _PRESCRIPTION_PRIORITY.get(by_type[canonical]["priority"], 1)
        new_pri = _PRESCRIPTION_PRIORITY.get(p.get("priority", "medium"), 1)
        if new_pri < cur_pri:
            by_type[canonical]["priority"] = p.get("priority", "medium")
        # Keep best title
        if not by_type[canonical]["title"] or len(p.get("title", "")) > len(by_type[canonical]["title"]):
            by_type[canonical]["title"] = p.get("title", "") or _PRESCRIPTION_TYPE_LABELS.get(canonical, canonical)

    # Build sorted result (high → medium → low)
    result = []
    for canonical, data in sorted(
        by_type.items(),
        key=lambda kv: _PRESCRIPTION_PRIORITY.get(kv[1]["priority"], 1),
    ):
        result.append({
            "type": canonical,
            "title": data["title"] or _PRESCRIPTION_TYPE_LABELS.get(canonical, canonical),
            "content": data["content"],
            "priority": data["priority"],
        })
    return result


def _extract_modules(result: Any) -> Optional[Dict]:
    """Extract modules dict from a skill execution result."""
    if isinstance(result, dict):
        if "modules" in result:
            return result
        if "structured_output" in result and isinstance(result["structured_output"], dict):
            return result["structured_output"]
    return result if isinstance(result, dict) else None


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
    workflow.add_node("sync_patient_data", sync_patient_data_node)
    workflow.add_node("retrieve_memory", retrieve_memory_node)
    workflow.add_node("classify_intent", classify_intent_with_llm_node)
    workflow.add_node("execute_skill", execute_claude_skill_node)
    workflow.add_node("aggregate", aggregate_results_node)
    workflow.add_node("save_memory", save_memory_node)
    workflow.add_node("push_insight", push_insight_node)
    workflow.add_node("error", lambda s: s)

    # Define the entry point
    workflow.set_entry_point("load_patient")

    # Add edges: load_patient → check_basic_questionnaire → (conditional)
    workflow.add_edge("load_patient", "check_basic_questionnaire")

    # Conditional routing after basic questionnaire check
    def route_after_questionnaire_check(state: AgentState) -> str:
        if state.missing_basic_fields and len(state.missing_basic_fields) > 0:
            return "save_memory"
        if state.questionnaire_answers_submitted:
            return "sync_patient_data"
        return "retrieve_memory"

    workflow.add_conditional_edges(
        "check_basic_questionnaire",
        route_after_questionnaire_check,
        {
            "sync_patient_data": "sync_patient_data",
            "retrieve_memory": "retrieve_memory",
            "save_memory": "save_memory",
        },
    )

    # sync_patient_data → retrieve_memory
    workflow.add_edge("sync_patient_data", "retrieve_memory")

    workflow.add_edge("retrieve_memory", "classify_intent")
    workflow.add_edge("classify_intent", "execute_skill")
    workflow.add_edge("execute_skill", "aggregate")

    # Conditional routing for error handling / fan-out
    def should_continue(state: AgentState) -> str:
        if state.error_message:
            return "error"
        return "save_and_push"

    workflow.add_conditional_edges(
        "aggregate",
        should_continue,
        {
            "save_and_push": "save_memory",
            "error": "error",
        }
    )

    # Fan-out: save_memory → push_insight → END
    # push_insight runs after save_memory (sequential fan-out to avoid state conflicts)
    workflow.add_edge("save_memory", "push_insight")
    workflow.add_edge("push_insight", END)
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
        is_re_assessment: bool = False,
        questionnaire_answers_submitted: bool = False,
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
            questionnaire_answers_submitted: If True, trigger sync_patient_data after check passes

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
        if is_re_assessment:
            initial_state.is_re_assessment = True
        if questionnaire_answers_submitted:
            initial_state.questionnaire_answers_submitted = True

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
