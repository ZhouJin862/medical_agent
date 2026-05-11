"""
Check Basic Questionnaire Node - Intercept workflow when basic fields are missing.

After load_patient, checks if required basic questionnaire fields (age, gender,
height, weight) are present in patient_context. If missing, returns a structured
response with the missing fields and their corresponding questionnaire questions
so the frontend can render them for the user to fill in.

The list of required fields is NOT hardcoded - it's dynamically read from the
`health-basic` questionnaire definition in the database (questions with
`required: true`). The QUESTIONNAIRE_FIELD_MAP only maps question IDs to
patient_context paths.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.infrastructure.agent.state import AgentState, AgentStatus

logger = logging.getLogger(__name__)

# Maps questionnaire question IDs to (section, key) in patient_context.
# When a new required question is added to the DB questionnaire, add its mapping here.
QUESTIONNAIRE_FIELD_MAP: Dict[str, Tuple[str, str]] = {
    "gender-select": ("basic_info", "gender"),
    "q_age_picker": ("basic_info", "age"),
    "height-input": ("vital_signs", "height"),
    "weight-input": ("vital_signs", "weight"),
    "disease-history": ("medical_history", "disease_labels"),
    "symptoms": ("medical_history", "symptoms"),
}


def map_questionnaire_answers_to_health_data(
    answers: Dict[str, Any],
) -> Dict[str, Any]:
    """Map questionnaire answers {question_id: value} to flat health_data dict.

    The returned dict uses top-level keys that load_patient_node can consume
    (e.g. {"age": 45, "gender": "male", "height": 170, "weight": 75,
            "diseaseLabels": ["hypertension"]}).

    Args:
        answers: {question_id: answer_value} from the frontend.

    Returns:
        Flat dict ready to merge into health_data.
    """
    # Maps question IDs to the key name load_patient_node expects at top level.
    _ANSWER_TO_HEALTH_DATA_KEY: Dict[str, str] = {
        "gender-select": "gender",
        "q_age_picker": "age",
        "height-input": "height",
        "weight-input": "weight",
        "disease-history": "diseaseLabels",
        "sport_target1": "sport_target",
        "symptoms": "symptoms",
    }

    result: Dict[str, Any] = {}
    for q_id, value in answers.items():
        health_key = _ANSWER_TO_HEALTH_DATA_KEY.get(q_id)
        if health_key and value is not None and value != "" and value != []:
            # disease-history: [["hypertension", "moderate"], ...] → diseaseLabels + disease_severity
            if q_id == "disease-history" and isinstance(value, list):
                labels = []
                severity_map = {}
                for item in value:
                    if isinstance(item, list) and len(item) >= 2:
                        labels.append(item[0])
                        severity_map[item[0]] = item[1]
                    elif isinstance(item, str):
                        labels.append(item)
                if labels:
                    result["diseaseLabels"] = labels
                    result["disease_severity"] = severity_map
                continue
            result[health_key] = value
        # disease-history: [] → mark as "answered_empty" to distinguish from "not answered"
        elif q_id == "disease-history" and isinstance(value, list) and len(value) == 0:
            result["diseaseLabels"] = []
            result["_dh_explicit_empty"] = True
        # symptoms: [] → mark as answered (no symptoms)
        elif q_id == "symptoms" and isinstance(value, list) and len(value) == 0:
            result["symptoms"] = []
        # symptoms: non-empty list → pass through
        elif q_id == "symptoms" and isinstance(value, list) and len(value) > 0:
            result["symptoms"] = value
    return result


def _get_field_value(patient_context, section: str, key: str) -> Any:
    """Get a value from patient_context.{section}.{key}, return None if missing/empty."""
    if patient_context is None:
        return None
    section_data = getattr(patient_context, section, None)
    if not section_data or not isinstance(section_data, dict):
        return None
    value = section_data.get(key)
    if value is None or value == "":
        return None
    # Keep empty list [] as-is to distinguish from "not set"
    return value


def _build_missing_response(
    missing_fields: List[str],
    missing_questions: List[Dict[str, Any]],
) -> str:
    """Build natural language response listing missing questions."""
    question_items = []
    for q in missing_questions:
        title = q.get("title", q.get("id", ""))
        q_type = q.get("type", "")
        hint = ""
        if q_type == "single":
            options = q.get("options", [])
            if options:
                labels = [o.get("label", o.get("value", "")) for o in options]
                hint = f"（{'/'.join(labels)}）"
        elif q_type == "number":
            hint = "（请输入数值）"
        elif q_type in ("multipleSubchoice", "multiple"):
            options = q.get("options", [])
            if options:
                labels = [o.get("label", o.get("value", "")) for o in options]
                hint = f"（{'/'.join(labels)}，可多选）"
        question_items.append(f"- **{title}**{hint}")

    questions_text = "\n".join(question_items)

    return (
        "## 需要补充基础信息\n\n"
        "为了给您提供准确的健康评估，请先回答以下问题：\n\n"
        f"{questions_text}\n\n"
        "---\n\n"
        "> 请提供以上信息，我将为您进行专业的健康评估。"
    )


async def check_basic_questionnaire_node(state: AgentState) -> AgentState:
    """
    Check if required basic questionnaire fields are present in patient_context.

    Gate: only runs when state.require_basic_questionnaire is True.
    Reads the `health-basic` questionnaire from DB, filters required questions,
    checks each against patient_context, and either passes through or returns
    only the missing required fields with their full question definitions.
    """
    # 1. Gate: skip if not required
    if not state.require_basic_questionnaire:
        state.missing_basic_fields = None
        logger.info("check_basic_questionnaire: gate disabled, skipping")
        return state

    state.current_step = "check_basic_questionnaire"
    logger.info("Checking basic questionnaire fields")

    # 2. Load questionnaire from DB
    try:
        from src.infrastructure.database import get_db_session
        from src.domain.questionnaire.services.questionnaire_service import QuestionnaireService

        questionnaire = None
        async for session in get_db_session():
            questionnaire = await QuestionnaireService.get_by_type(session, "health-basic")
            break

        if not questionnaire:
            logger.warning("health-basic questionnaire not found in DB, skipping check")
            state.missing_basic_fields = []
            return state

    except Exception as e:
        logger.warning(f"Failed to load health-basic questionnaire: {e}, skipping check")
        state.missing_basic_fields = []
        return state

    # 3. Get all data questions (skip intro/transition screens)
    questions = questionnaire.questions or []
    data_questions = [q for q in questions if q.get("type") not in ("intro",)]

    # Required questions determine routing (intercept if any missing)
    required_questions = [
        q for q in data_questions
        if q.get("required") is True and q.get("id") in QUESTIONNAIRE_FIELD_MAP
    ]

    if not required_questions:
        logger.info("No required mapped questions in questionnaire, passing through")
        state.missing_basic_fields = []
        return state

    # 4. Check each required field against patient_context
    if not state.patient_context:
        logger.warning("check_basic_questionnaire: patient_context is None")
        state.missing_basic_fields = []
        return state

    # Check each required field against patient_context
    missing_fields: List[str] = []
    missing_required_questions: List[Dict[str, Any]] = []

    for q in required_questions:
        q_id = q.get("id")
        section, key = QUESTIONNAIRE_FIELD_MAP[q_id]
        value = _get_field_value(state.patient_context, section, key)

        if value is None:
            missing_fields.append(key)
            missing_required_questions.append(q)
            logger.info(f"Missing basic field: {section}.{key} (question: {q_id})")

    # 5. Check disease-history and symptoms even when all required fields are present
    dh_section, dh_key = QUESTIONNAIRE_FIELD_MAP["disease-history"]
    dh_value = _get_field_value(state.patient_context, dh_section, dh_key)
    dh_question = next((q for q in data_questions if q.get("id") == "disease-history"), None)
    symptoms_question = next((q for q in data_questions if q.get("id") == "symptoms"), None)
    # dh_value: None = not answered, [] = answered empty (no diseases), list with items = has diseases
    dh_not_answered = dh_value is None and dh_question is not None
    dh_empty = isinstance(dh_value, list) and len(dh_value) == 0

    # Check symptoms answered status (only relevant when dh_empty)
    symp_section, symp_key = QUESTIONNAIRE_FIELD_MAP["symptoms"]
    symp_value = _get_field_value(state.patient_context, symp_section, symp_key) if dh_empty else None
    symp_not_answered = symp_value is None and symptoms_question is not None

    if not missing_fields and not dh_not_answered and not (dh_empty and symp_not_answered):
        state.missing_basic_fields = []
        logger.info("All basic questionnaire fields present, continuing workflow")
        return state

    # disease-history not answered (all required fields present) → ask disease-history
    if not missing_fields and dh_not_answered:
        missing_required_questions = []
        return_questions = [dh_question]
        state.missing_basic_fields = ["disease_labels"]  # non-empty to trigger route
        state.final_response = _build_missing_response([], return_questions)
        recommended_data_collection = [{
            "id": "disease-history",
            "question": dh_question.get("title", ""),
            "reason": "基础信息采集",
            "priority": "optional",
        }]
        state.structured_output = {
            "status": "missing_basic_info",
            "questionnaire_type": questionnaire.questionnaire_id,
            "missing_fields": [],
            "recommended_data_collection": recommended_data_collection,
            "questions": return_questions,
        }
        logger.info("All required fields present, but disease-history missing — returning it")
        return state

    # disease-history answered empty (no diseases) + symptoms not answered → ask symptoms
    if not missing_fields and dh_empty and symp_not_answered:
        return_questions = [symptoms_question] if symptoms_question else []
        if not return_questions:
            state.missing_basic_fields = []
            return state
        state.missing_basic_fields = ["symptoms"]
        state.final_response = _build_missing_response([], return_questions)
        state.structured_output = {
            "status": "missing_basic_info",
            "questionnaire_type": questionnaire.questionnaire_id,
            "missing_fields": [],
            "recommended_data_collection": [],
            "questions": return_questions,
        }
        logger.info("No diseases selected — returning symptoms question")
        return state

    # 6. Determine return strategy based on health archive data availability
    # If Ping An API returned actual data (some fields populated), only ask for
    # missing required fields. Otherwise, return the entire questionnaire
    # (including non-required like disease-history) for new users.
    has_health_data = False
    if state.patient_context.basic_info and state.patient_context.basic_info.get("source") == "ping_an_api":
        # Check if any required field was actually populated from the API
        # (API may return success for non-existent customers with empty data)
        populated_count = len(required_questions) - len(missing_required_questions)
        if populated_count > 0:
            has_health_data = True

    if has_health_data:
        # Health archive has data → only return missing required fields
        return_questions = list(missing_required_questions)
        logger.info(
            f"Has health data ({populated_count} fields populated), "
            f"returning {len(missing_required_questions)} missing required questions"
        )
    else:
        # No health data → return entire questionnaire (including non-required)
        return_questions = list(data_questions)
        logger.info(
            f"No health data, returning full questionnaire "
            f"({len(data_questions)} questions, {len(missing_required_questions)} missing required)"
        )

    # Always include disease-history if not filled
    dh_in_return = any(q.get("id") == "disease-history" for q in return_questions)
    if not dh_in_return:
        section, key = QUESTIONNAIRE_FIELD_MAP["disease-history"]
        dh_value = _get_field_value(state.patient_context, section, key)
        if dh_value is None:
            dh_q = next((q for q in data_questions if q.get("id") == "disease-history"), None)
            if dh_q:
                return_questions.append(dh_q)

    state.missing_basic_fields = missing_fields
    state.final_response = _build_missing_response(missing_fields, return_questions)

    recommended_data_collection = []
    for q in return_questions:
        recommended_data_collection.append({
            "id": q.get("id"),
            "question": q.get("title", ""),
            "reason": "基础问卷必填项缺失" if q.get("required") else "基础信息采集",
            "priority": "required" if q.get("required") else "optional",
        })

    state.structured_output = {
        "status": "missing_basic_info",
        "questionnaire_type": questionnaire.questionnaire_id,
        "missing_fields": missing_fields,
        "recommended_data_collection": recommended_data_collection,
        "questions": return_questions,
    }

    return state
