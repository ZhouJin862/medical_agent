"""
Standard Assessment API Route.

Provides a synchronous JSON endpoint for third-party integration.
Uses the same LangGraph pipeline as the streaming endpoint.
The only difference is the response format (structured JSON vs SSE markdown).
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.interface.api.dto.request import AssessmentRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["assessment"])

# ---------------------------------------------------------------------------
# Lightweight JSON file session store for multi-turn questionnaire answers
# ---------------------------------------------------------------------------
_SESSIONS_DIR = os.path.join("data", "assessment_sessions")


def _load_session_data(session_id: str) -> dict:
    """Load previously collected health_data for a session."""
    path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_session_data(session_id: str, data: dict):
    """Persist the latest health_data snapshot for a session."""
    os.makedirs(_SESSIONS_DIR, exist_ok=True)
    path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


async def _fetch_ping_an_data(party_id: str) -> Optional[Dict[str, Any]]:
    """Fetch patient data from Ping An Health Archive API."""
    try:
        from mcp_servers.profile_server.tools import get_health_data
        health_data = await get_health_data(party_id=party_id)
        api_code = health_data.get("code") or health_data.get("_api_response", {}).get("code")
        if health_data and api_code == "S000000":
            logger.info(f"Successfully fetched Ping An data for party_id={party_id}")
            return health_data
        else:
            logger.warning(f"Ping An API non-success: code={api_code}")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch Ping An data: {e}")
        return None


@router.post("/assessment")
async def run_assessment(request: AssessmentRequest):
    """
    Run a health assessment and return structured JSON.

    Uses the same LangGraph pipeline as the streaming endpoint.
    The only difference is the response format — returns structured JSON
    instead of SSE markdown stream.

    The ``skill`` field accepts a single skill name (string), an array of
    skill names, or a package shorthand like ``package@assessment``.
    When multiple skills are provided, they are executed sequentially and
    results are merged.
    """
    start_time = time.time()
    skills = request.skill  # Already normalized to list[str] by validator
    logger.info(f"Assessment request: party_id={request.party_id}, skills={skills}")

    # Generate or reuse session_id for multi-turn questionnaire
    skill_slug = skills[0] if len(skills) == 1 else "multi"
    session_id = request.session_id or f"asm_{request.party_id}_{skill_slug}_{int(time.time())}"

    # 1. Fetch Ping An data (same as streaming endpoint)
    health_data = None
    data_source = "request_body"
    try:
        health_data = await asyncio.wait_for(
            _fetch_ping_an_data(request.party_id),
            timeout=15.0,
        )
        if health_data:
            data_source = "ping_an_api"
    except asyncio.TimeoutError:
        logger.warning(f"Ping An API timeout for party_id={request.party_id}")

    # Restore previously collected data for this session (multi-turn)
    # Skip for re_assessment — start fresh
    if request.session_id and not request.re_assessment:
        prev_data = _load_session_data(request.session_id)
        if prev_data:
            if not health_data:
                health_data = {}
            # Previous session data as base, current request overrides
            health_data = {**prev_data, **health_data}

    if request.questionnaire_answers:
        from src.infrastructure.agent.nodes.check_basic_questionnaire import map_questionnaire_answers_to_health_data
        if not health_data:
            health_data = {}
        health_data.update(map_questionnaire_answers_to_health_data(request.questionnaire_answers))

    if request.patient_data or request.vital_signs or request.medical_history:
        if not health_data:
            health_data = {}
        # Vital signs → top-level keys (systolic_bp, total_cholesterol, etc.)
        if request.vital_signs:
            health_data.update(request.vital_signs)
        # Patient basic info → top-level keys (age, gender, etc.)
        if request.patient_data:
            health_data.update(request.patient_data)
        # Medical history
        if request.medical_history:
            if "diseaseLabels" not in health_data and "disease_labels" in request.medical_history:
                health_data["diseaseLabels"] = request.medical_history["disease_labels"]
            if "diseaseHistory" not in health_data and "disease_history" in request.medical_history:
                health_data["diseaseHistory"] = request.medical_history["disease_history"]
        if data_source == "request_body":
            data_source = "request_body_merged"

    # Persist the latest merged health_data snapshot for this session
    _save_session_data(session_id, health_data or {})

    # 2. Process through SkillsIntegratedAgent (same LangGraph pipeline)
    is_package = len(skills) > 1 or (len(skills) == 1 and skills[0] == "package@assessment")
    all_structured_results: list[Dict[str, Any]] = []

    try:
        from src.infrastructure.agent.skills_integration import SkillsIntegratedAgent

        agent = SkillsIntegratedAgent()

        if is_package:
            # Package assessment: orchestration handled inside execute_claude_skill_node
            # Phase transition: if user submitted sport_target answer, bump to Phase 3
            current_phase = health_data.get("_orchestration_phase", 0)
            if current_phase == 2 and health_data.get("sport_target"):
                health_data["_orchestration_phase"] = 3
            _save_session_data(session_id, health_data or {})

            t0 = time.time()
            agent_state = await asyncio.wait_for(
                agent.process(
                    user_input="请进行全面健康评估",
                    patient_id=f"patient_{request.party_id}",
                    party_id=request.party_id,
                    ping_an_health_data=health_data,
                    suggested_skill="package@assessment",
                    session_id=session_id,
                    require_basic_questionnaire=True,
                ),
                timeout=120.0,
            )
            elapsed = int((time.time() - t0) * 1000)
            _log_skill_perf("package@assessment", elapsed, agent_state)
        else:
            # Single skill execution
            first_skill = skills[0]
            t0 = time.time()
            agent_state = await asyncio.wait_for(
                agent.process(
                    user_input=f"请进行{first_skill}评估",
                    patient_id=f"patient_{request.party_id}",
                    party_id=request.party_id,
                    ping_an_health_data=health_data,
                    suggested_skill=first_skill,
                    session_id=session_id,
                    require_basic_questionnaire=True,
                ),
                timeout=120.0,
            )
            elapsed = int((time.time() - t0) * 1000)
            _log_skill_perf(first_skill, elapsed, agent_state)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Assessment timed out (120s)")
    except Exception as e:
        logger.error(f"Agent processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

    # Early exit: if first skill returned missing_basic_info, skip remaining skills
    so = getattr(agent_state, 'structured_output', None)
    first_skill_needs_questionnaire = isinstance(so, dict) and so.get("status") == "missing_basic_info"

    if not first_skill_needs_questionnaire and not is_package:
        # Run remaining skills sequentially (only for non-package single skill mode)
        remaining_skills = skills[1:]
        all_structured_results: list[Dict[str, Any]] = []
        for extra_skill in remaining_skills:
            t1 = time.time()
            try:
                extra_state = await asyncio.wait_for(
                    agent.process(
                        user_input=f"请进行{extra_skill}评估",
                        patient_id=f"patient_{request.party_id}",
                        party_id=request.party_id,
                        ping_an_health_data=health_data,
                        suggested_skill=extra_skill,
                        session_id=session_id,
                        require_basic_questionnaire=False,
                    ),
                    timeout=120.0,
                )
                elapsed = int((time.time() - t1) * 1000)
                _log_skill_perf(extra_skill, elapsed, extra_state)
                extra_sr = _extract_structured_result(extra_state)
                if extra_sr:
                    all_structured_results.append(extra_sr)
            except Exception as e:
                elapsed = int((time.time() - t1) * 1000)
                logger.warning(f"PERF skill={extra_skill} time={elapsed}ms FAILED: {e}")

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 3. Check for missing basic questionnaire fields
    so = getattr(agent_state, 'structured_output', None)
    if isinstance(so, dict) and so.get("status") == "missing_basic_info":
        recommended = so.get("recommended_data_collection", [])
        questions = so.get("questions", [])

        if request.re_assessment:
            # Return ALL questions in order for re-assessment
            all_questions = _build_all_questions(questions)
            return JSONResponse(content={
                "code": 200,
                "success": True,
                "data": {
                    "party_id": request.party_id,
                    "skill": request.skill,
                    "session_id": session_id,
                    "status": "re_assessment",
                    "questionnaire_type": so.get("questionnaire_type"),
                    "questions": all_questions,
                    "metadata": {
                        "data_source": data_source,
                        "execution_time_ms": elapsed_ms,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            })

        # Normal flow: return single current question
        current_q = _build_current_question(questions, recommended)

        return JSONResponse(content={
            "code": 200,
            "success": True,
            "data": {
                "party_id": request.party_id,
                "skill": request.skill,
                "session_id": session_id,
                "status": "missing_basic_info",
                "questionnaire_type": so.get("questionnaire_type"),
                "missing_fields": so.get("missing_fields", []),
                "current_question": current_q,
                "recommended_data_collection": recommended,
                "metadata": {
                    "data_source": data_source,
                    "execution_time_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat(),
                },
            },
        })

    # 3.5 Check for goal_selection status (package assessment orchestration)
    so = getattr(agent_state, 'structured_output', None)
    if isinstance(so, dict) and so.get("status") == "goal_selection":
        # Save orchestration state to session for next request
        health_data["_orchestration_phase"] = so.get("_orchestration_phase", 2)
        health_data["_population_result"] = so.get("population_classification", {})
        _save_session_data(session_id, health_data or {})

        return JSONResponse(content={
            "code": 200,
            "success": True,
            "data": {
                "party_id": request.party_id,
                "skill": request.skill,
                "session_id": session_id,
                "status": "goal_selection",
                "current_question": so.get("current_question"),
                "population_classification": so.get("population_classification"),
                "metadata": {
                    "data_source": data_source,
                    "execution_time_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat(),
                },
            },
        })

    # 4. Check for incomplete assessment (skill needs more data)
    incomplete_info = _check_incomplete(agent_state)
    if incomplete_info:
        return JSONResponse(content={
            "code": 200,
            "success": True,
            "data": {
                "party_id": request.party_id,
                "skill": request.skill,
                "session_id": session_id,
                "status": "incomplete",
                "assessment_result": _extract_structured_result(agent_state),
                "required_data": incomplete_info.get("required_fields", []),
                "message": incomplete_info.get("message", ""),
                "metadata": {
                    "data_source": data_source,
                    "execution_time_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat(),
                    "skill_version": "1.0",
                },
            },
        })

    # 4. Extract structured_result from agent state
    structured_result = _extract_structured_result(agent_state)

    # 5. Merge multi-skill results if any
    if all_structured_results:
        structured_result = _merge_structured_results(structured_result, all_structured_results)

    # 5.5 Transform abnormal_indicators into indicators + warnings structure
    transform_abnormal_indicators(structured_result)

    # 5.6 LLM 生成个性化处方
    try:
        from src.domain.shared.services.prescription_generator import generate_prescriptions
        structured_result["intervention_prescriptions"] = await generate_prescriptions(
            structured_result, health_data or {}
        )
    except Exception as e:
        logger.warning(f"Prescription generation failed, keeping script defaults: {e}")

    # 6. Build response
    response_data = {
        "party_id": request.party_id,
        "skill": skills,
        "session_id": session_id,
        "assessment_result": structured_result,
        "metadata": {
            "data_source": data_source,
            "execution_time_ms": elapsed_ms,
            "timestamp": datetime.now().isoformat(),
            "skill_version": "1.0",
        },
    }

    # 7. Persist insight (best-effort, never blocks response)
    try:
        from src.infrastructure.database import get_db_session_context
        from src.domain.insight.services.insight_service import InsightService
        async with get_db_session_context() as save_session:
            await InsightService.save(save_session, request.party_id, skills[0], structured_result)
    except Exception as save_err:
        logger.warning(f"Failed to persist insight for party_id={request.party_id}: {save_err}")

    return JSONResponse(content={"code": 200, "success": True, "data": response_data})


def _log_skill_perf(skill_name: str, elapsed_ms: int, state):
    """Log performance and status info for a single skill execution."""
    so = getattr(state, 'structured_output', None)
    is_llm_fallback = isinstance(so, dict) and so.get("response_type") == "llm_fallback"
    is_incomplete = isinstance(so, dict) and so.get("is_incomplete")
    exec_skills = getattr(state, 'executed_skills', None)
    skill_success = exec_skills and len(exec_skills) > 0 and exec_skills[0].success
    logger.info(
        f"PERF skill={skill_name} time={elapsed_ms}ms "
        f"success={skill_success} llm_fallback={is_llm_fallback} "
        f"incomplete={is_incomplete}"
    )


def _build_all_questions(questions: list) -> list:
    """Build the full ordered question list for re-assessment.

    Filters out intro-type questions and enriches each with navigation metadata.
    """
    data_questions = [q for q in questions if q.get("type") not in ("intro",)]
    total_qs = len(data_questions)
    result = []
    for i, q in enumerate(data_questions):
        item = {
            "id": q.get("id"),
            "type": q.get("type"),
            "title": q.get("title", ""),
            "componentType": q.get("componentType", q.get("component_type")),
            "required": q.get("required", False),
            "options": q.get("options"),
            "showNavigation": True,
            "hasNext": i < total_qs - 1,
            "hasPrev": i > 0,
            "currentIndex": i + 1,
            "totalQs": total_qs,
        }
        if i > 0:
            item["prevQuestionId"] = data_questions[i - 1].get("id")
        if i < total_qs - 1:
            item["nextQuestionId"] = data_questions[i + 1].get("id")
        result.append(item)
    return result


def _build_current_question(
    questions: list,
    recommended: list,
) -> Optional[Dict[str, Any]]:
    """Build a full current_question object for the first missing required question.

    Takes the complete question definition from the ``questions`` array (which
    includes type, componentType, options, etc.) and enriches it with
    navigation metadata (hasNext, hasPrev, currentIndex, totalQs).
    """
    if not questions:
        return None

    # Fallback: no recommended but have questions → use first question
    if not recommended:
        target_id = questions[0].get("id")
    else:
        target_id = recommended[0].get("id")
    if not target_id:
        return recommended[0]

    # Build a lookup for quick access
    q_by_id = {q.get("id"): q for q in questions if isinstance(q, dict)}

    q = q_by_id.get(target_id)
    if not q:
        return recommended[0]

    # Navigation: position among data questions
    data_questions = [q for q in questions if q.get("type") not in ("intro",)]
    total_qs = len(data_questions)

    current_index = 0
    for i, dq in enumerate(data_questions):
        if dq.get("id") == target_id:
            current_index = i
            break

    result = {
        "id": q.get("id"),
        "type": q.get("type"),
        "title": q.get("title", ""),
        "componentType": q.get("componentType", q.get("component_type")),
        "required": q.get("required", False),
        "options": q.get("options"),
        "showNavigation": True,
        "hasNext": current_index < total_qs - 1,
        "hasPrev": current_index > 0,
        "currentIndex": current_index + 1,
        "totalQs": total_qs,
    }

    # Include next/prev question IDs if available
    if current_index > 0:
        result["prevQuestionId"] = data_questions[current_index - 1].get("id")
    if current_index < total_qs - 1:
        result["nextQuestionId"] = data_questions[current_index + 1].get("id")

    return result


def _merge_structured_results(
    primary: Dict[str, Any],
    extras: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Merge multiple skill results into a single structured_result.

    Arrays (disease_prediction, abnormal_indicators, intervention_prescriptions,
    recommended_data_collection) are concatenated. population_classification is
    kept from the primary result.
    """
    if not extras:
        return primary

    merged = dict(primary)

    array_keys = [
        "disease_prediction",
        "abnormal_indicators",
        "intervention_prescriptions",
        "recommended_data_collection",
        "risk_warnings",
    ]
    for key in array_keys:
        primary_list = merged.get(key, [])
        if not isinstance(primary_list, list):
            primary_list = []
        for extra in extras:
            extra_list = extra.get(key, [])
            if isinstance(extra_list, list):
                primary_list.extend(extra_list)
        merged[key] = primary_list

    return merged


def _check_incomplete(agent_state) -> Optional[Dict[str, Any]]:
    """Check if the skill returned an incomplete status (needs more data)."""
    # Check structured_output flag
    so = getattr(agent_state, 'structured_output', None)
    if isinstance(so, dict) and so.get("is_incomplete"):
        # Find required_fields from executed_skills result_data
        for skill_result in (agent_state.executed_skills or []):
            rd = skill_result.result_data
            if isinstance(rd, dict):
                data = rd.get("data", rd)
                if isinstance(data, dict):
                    return {
                        "required_fields": data.get("required_fields", []),
                        "message": data.get("message", ""),
                    }
        return {"required_fields": [], "message": ""}

    if not hasattr(agent_state, 'executed_skills') or not agent_state.executed_skills:
        return None
    for skill_result in agent_state.executed_skills:
        rd = skill_result.result_data
        if isinstance(rd, dict):
            if rd.get("status") == "incomplete":
                return {
                    "required_fields": rd.get("required_fields", []),
                    "message": rd.get("message", ""),
                }
            data = rd.get("data", {})
            if isinstance(data, dict) and data.get("status") == "incomplete":
                return {
                    "required_fields": data.get("required_fields", []),
                    "message": data.get("message", ""),
                }
    return None


def _extract_structured_result(agent_state) -> Dict[str, Any]:
    """Extract structured_result from the LangGraph agent state.

    The skill pipeline may output structured_result directly (if the script
    provides it), or we extract it from the health_assessment modules.
    """
    # 1. Try to get structured_result from skill execution results
    if hasattr(agent_state, 'executed_skills') and agent_state.executed_skills:
        for skill_result in agent_state.executed_skills:
            result_data = skill_result.result_data
            if isinstance(result_data, dict):
                # Direct structured_result key
                structured = result_data.get("structured_result")
                if structured and isinstance(structured, dict):
                    return structured
                # Inside structured_output (workflow skill pass-through)
                so = result_data.get("structured_output")
                if isinstance(so, dict):
                    sr = so.get("structured_result")
                    if sr and isinstance(sr, dict):
                        return sr
                # Inside modules
                modules = result_data.get("modules", {})
                if isinstance(modules, dict) and modules:
                    sr = modules.get("structured_result")
                    if sr and isinstance(sr, dict):
                        return sr
                    return _fallback_from_modules(modules)

    # 2. Try from structured_output (set by execute node on success)
    structured_output = getattr(agent_state, 'structured_output', None)
    if isinstance(structured_output, dict):
        # Phase 3: prefer complete structured_result (merged from all skills)
        sr = structured_output.get("structured_result")
        if sr and isinstance(sr, dict):
            return sr
        # Fallback: return modules dict for single-skill cases
        if "modules" in structured_output and isinstance(structured_output.get("modules"), dict):
            return structured_output

    # 3. Try from health_assessment
    health_assessment = getattr(agent_state, 'health_assessment', None)
    if isinstance(health_assessment, dict):
        if "structured_result" in health_assessment:
            return health_assessment["structured_result"]

        final_output = health_assessment.get("final_output", health_assessment)
        if isinstance(final_output, dict):
            if "structured_result" in final_output:
                return final_output["structured_result"]
            modules = final_output.get("modules", {})
            if modules:
                return _fallback_from_modules(modules)

    # 4. Minimal fallback
    return {
        "population_classification": {
            "primary_category": "健康",
            "grouping_basis": [],
        },
        "recommended_data_collection": [],
        "abnormal_indicators": [],
        "disease_prediction": [],
        "intervention_prescriptions": [],
        "risk_warnings": [],
    }


def _fallback_from_modules(modules: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to extract structured fields from free-form modules."""
    result: Dict[str, Any] = {
        "population_classification": {
            "primary_category": "健康",
            "grouping_basis": [],
        },
        "recommended_data_collection": [],
        "abnormal_indicators": [],
        "disease_prediction": [],
        "intervention_prescriptions": [],
        "risk_warnings": [],
    }

    risk_assessment = modules.get("risk_assessment", {})
    if isinstance(risk_assessment, dict):
        risk_level = risk_assessment.get("risk_level_zh", risk_assessment.get("risk_level", ""))
        category = _risk_to_category(risk_level)
        result["population_classification"] = {
            "primary_category": category,
            "grouping_basis": [{
                "disease": "心血管病",
                "type": "",
                "level": risk_level or "",
                "note": risk_level or "",
            }],
        }
        if risk_assessment.get("ten_year_risk"):
            result["disease_prediction"] = [{
                "disease_name": "心血管病",
                "probability": risk_assessment.get("ten_year_risk_range", ""),
                "risk_level": risk_assessment.get("ten_year_risk_zh", risk_level),
                "timeframe": "10年",
                "risk_model": "China-PAR",
            }]
            result["risk_warnings"] = [{
                "title": "心血管风险提示",
                "description": f"10年心血管病风险{risk_assessment.get('ten_year_risk_range', '偏高')}，属于{risk_level}",
                "level": "high" if "高" in (risk_level or "") else "medium",
            }]

    return result


def _risk_to_category(risk_level: str) -> str:
    """Map risk level to population classification category."""
    if not risk_level:
        return "健康"
    level = risk_level.lower()
    if "很高危" in level or "高危" in level:
        return "重症"
    if "中危" in level or "中" in level:
        return "慢病"
    if "低" in level:
        return "亚健康"
    return "健康"


# ---------------------------------------------------------------------------
# Abnormal indicators → indicators + warnings transformation
# ---------------------------------------------------------------------------

# Map clinical_note → (warning_title, warm_tip)
_WARNING_TEMPLATES: Dict[str, Dict[str, str]] = {
    "高血压": {
        "title": "血压异常预警",
        "tip": "建议低盐饮食，规律监测血压",
    },
    "血糖异常": {
        "title": "血糖异常预警",
        "tip": "注意控制碳水摄入，定期监测血糖",
    },
    "血糖控制不佳": {
        "title": "血糖控制不佳预警",
        "tip": "建议内分泌科就诊，调整控糖方案",
    },
    "血脂异常": {
        "title": "血脂异常预警",
        "tip": "减少高脂饮食，增加膳食纤维摄入",
    },
    "BMI≥28": {
        "title": "肥胖预警",
        "tip": "建议控制饮食，增加运动，科学减重",
    },
    "BMI≥24": {
        "title": "超重预警",
        "tip": "注意控制体重，避免久坐",
    },
    "高尿酸": {
        "title": "尿酸偏高预警",
        "tip": "减少高嘌呤饮食，多饮水",
    },
}


def transform_abnormal_indicators(sr: Dict[str, Any]) -> None:
    """Convert flat abnormal_indicators array into indicators + warnings structure.

    Modifies ``sr`` in place.  The old ``abnormal_indicators`` list is
    replaced by::

        {
            "indicators": [...],    # original items, normalised
            "warnings": [
                {
                    "title": "血压异常预警",
                    "tip": "建议低盐饮食，规律监测血压",
                    "indicator_indices": [0, 1]
                },
                ...
            ]
        }

    Indicators are grouped into warnings by ``clinical_note`` field.
    If ``clinical_note`` is missing, a best-effort inference from the
    indicator name is performed.
    """
    raw = sr.get("abnormal_indicators", [])
    if not isinstance(raw, list) or not raw:
        return

    # Keyword → clinical_note fallback when field is missing
    _NAME_TO_NOTE = {
        "收缩压": "高血压", "舒张压": "高血压",
        "血糖": "血糖异常", "糖化": "血糖异常",
        "胆固醇": "血脂异常", "甘油三酯": "血脂异常", "脂蛋白": "血脂异常",
        "尿酸": "高尿酸",
        "BMI": "BMI≥24", "腰围": "BMI≥24",
    }

    # Group by clinical_note
    groups: Dict[str, list[int]] = {}  # clinical_note → [indicator_index, ...]
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        note = item.get("clinical_note", "")
        if not note:
            # Fallback: infer from indicator name
            name = item.get("name", item.get("indicator", ""))
            for kw, cn in _NAME_TO_NOTE.items():
                if kw in name:
                    note = cn
                    break
        if note:
            groups.setdefault(note, []).append(i)

    warnings = []
    for note, indices in groups.items():
        template = _WARNING_TEMPLATES.get(note, {
            "title": f"{note}预警" if note else "异常预警",
            "tip": f"建议关注{note}指标" if note else "建议关注异常指标",
        })
        warnings.append({
            "title": template["title"],
            "tip": template["tip"],
            "indicator_indices": indices,
        })

    sr["abnormal_indicators"] = {
        "indicators": raw,
        "warnings": warnings,
    }
