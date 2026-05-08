"""Questionnaire detail API route."""
import json
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.domain.questionnaire.services.questionnaire_service import QuestionnaireService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["questionnaire"])

_SESSIONS_DIR = os.path.join("data", "assessment_sessions")

# Reverse mapping: health_data flat key → question ID
_HEALTH_DATA_KEY_TO_QUESTION_ID: Dict[str, str] = {
    "gender": "gender-select",
    "age": "q_age_picker",
    "height": "height-input",
    "weight": "weight-input",
    "diseaseLabels": "disease-history",
}


def _load_session_answers(session_id: str, party_id: str) -> Dict[str, Any]:
    """Load session data and reverse-map health_data keys to question answers.

    Returns {question_id: answer_value} for all known answers.
    """
    path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            health_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    answers: Dict[str, Any] = {}
    for health_key, value in health_data.items():
        q_id = _HEALTH_DATA_KEY_TO_QUESTION_ID.get(health_key)
        if q_id and value is not None and value != "" and value != []:
            answers[q_id] = value

    return answers


def _inject_answers(questions: list, answers: Dict[str, Any]) -> list:
    """Add 'answer' field to each question that has a known answer."""
    if not answers:
        return questions

    enriched = []
    for q in questions:
        q_copy = dict(q)
        q_id = q_copy.get("id")
        if q_id and q_id in answers:
            q_copy["answer"] = answers[q_id]
        enriched.append(q_copy)
    return enriched


@router.get("/questionnaire/{questionnaire_type}")
async def get_questionnaire(
    questionnaire_type: str,
    session_id: Optional[str] = Query(None, description="会话ID，传入后返回已有答案"),
    party_id: Optional[str] = Query(None, description="客户号"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get full questionnaire by type (e.g. 'health-basic').

    When session_id and party_id are provided, each question includes
    an ``answer`` field with the previously submitted value.
    """
    record = await QuestionnaireService.get_by_type(db_session, questionnaire_type)
    if not record:
        raise HTTPException(status_code=404, detail="问卷不存在")

    questions = record.questions or []

    # Load session answers if both session_id and party_id are provided
    answers = {}
    if session_id and party_id:
        answers = _load_session_answers(session_id, party_id)

    questions = _inject_answers(questions, answers)

    return JSONResponse(content={
        "code": 200,
        "success": True,
        "data": {
            "questionnaire_id": record.questionnaire_id,
            "title": record.title,
            "description": record.description,
            "skill_name": record.skill_name,
            "questions": questions,
            "version": record.version,
            "created_at": record.created_date.isoformat() if record.created_date else "",
            "updated_at": record.updated_date.isoformat() if record.updated_date else "",
        },
    })


@router.get("/questionnaire/{questionnaire_type}/{question_id}")
async def get_question(
    questionnaire_type: str,
    question_id: str,
    session_id: Optional[str] = Query(None, description="会话ID，传入后返回已有答案"),
    party_id: Optional[str] = Query(None, description="客户号"),
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get a single question by questionnaire type and question ID.

    When session_id and party_id are provided, the response includes
    an ``answer`` field with the previously submitted value.
    """
    record = await QuestionnaireService.get_by_type(db_session, questionnaire_type)
    if not record:
        raise HTTPException(status_code=404, detail="问卷不存在")

    questions = record.questions or []
    for q in questions:
        if q.get("id") == question_id:
            result = dict(q)

            if session_id and party_id:
                answers = _load_session_answers(session_id, party_id)
                if question_id in answers:
                    result["answer"] = answers[question_id]

            return JSONResponse(content={
                "code": 200,
                "success": True,
                "data": result,
            })

    raise HTTPException(status_code=404, detail="题目不存在")
