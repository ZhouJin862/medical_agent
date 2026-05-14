"""
External sync nodes - Push patient data and insight results to third-party system.

Nodes:
    sync_patient_data_node: After questionnaire completion, push data via addHumanInfo.
    push_insight_node: After skill aggregation, push insight via insightSave.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.infrastructure.agent.state import AgentState, AgentStatus
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def _gender_en_to_zh(gender: Optional[str]) -> str:
    """Convert internal English gender to Chinese for the third-party API."""
    if not gender:
        return ""
    g = str(gender).strip().lower()
    if g in ("male", "m"):
        return "男"
    if g in ("female", "f"):
        return "女"
    return gender


def _build_add_human_info_payload(state: AgentState) -> Dict[str, Any]:
    """Build addHumanInfo request payload from patient_context.

    Maps internal field names back to third-party DTO format (String values).
    """
    ctx = state.patient_context
    if not ctx:
        return {}

    bi = ctx.basic_info or {}
    vs = ctx.vital_signs or {}
    mh = ctx.medical_history or {}

    payload: Dict[str, Any] = {
        "partyId": state.party_id or state.patient_id,
    }

    # Basic info
    if bi.get("age") is not None:
        payload["age"] = int(bi["age"])
    gender_zh = _gender_en_to_zh(bi.get("gender"))
    if gender_zh:
        payload["gender"] = gender_zh
    if vs.get("height") is not None:
        payload["height"] = str(vs["height"])
    if vs.get("weight") is not None:
        payload["weight"] = str(vs["weight"])
    if vs.get("waist") is not None:
        payload["waistCircumference"] = str(vs["waist"])

    # Blood pressure DTO
    bp = {}
    if vs.get("systolic_bp") is not None:
        bp["systolicPressure"] = str(vs["systolic_bp"])
    if vs.get("diastolic_bp") is not None:
        bp["diastolicPressure"] = str(vs["diastolic_bp"])
    if bp:
        payload["healthDigitalBloodPressureDTO"] = bp

    # Uric acid DTO
    ua = {}
    if vs.get("uric_acid") is not None:
        ua["bloodUricAcid"] = str(vs["uric_acid"])
    if ua:
        payload["healthDigitalUricAcidDTO"] = ua

    # Blood lipids DTO
    bl = {}
    if vs.get("hba1c") is not None:
        bl["hbalc"] = str(vs["hba1c"])
    if vs.get("total_cholesterol") is not None:
        bl["tc"] = str(vs["total_cholesterol"])
    if vs.get("triglyceride") is not None or vs.get("tg") is not None:
        bl["tg"] = str(vs.get("triglyceride") or vs.get("tg"))
    if vs.get("ldl_c") is not None:
        bl["ldlc"] = str(vs["ldl_c"])
    if vs.get("hdl_c") is not None:
        bl["hdlc"] = str(vs["hdl_c"])
    if bl:
        payload["healthDigitalBloodLipidsDTO"] = bl

    # Blood glucose DTO
    bg = {}
    if vs.get("fasting_blood_glucose") is not None or vs.get("fasting_glucose") is not None:
        bg["fastingGlucose"] = str(vs.get("fasting_blood_glucose") or vs.get("fasting_glucose"))
    if vs.get("postprandial_blood_glucose") is not None or vs.get("postprandial_glucose") is not None:
        bg["twoHourPostprandialGlucose"] = str(vs.get("postprandial_blood_glucose") or vs.get("postprandial_glucose"))
    if bg:
        payload["healthDigitalBloodGlucoseDTO"] = bg

    # Disease DTOs
    diseases = mh.get("diseases") or mh.get("disease_labels") or []
    chronic = []
    for d in diseases:
        if isinstance(d, str):
            chronic.append({"icdCode": "", "icdName": d})
        elif isinstance(d, dict):
            chronic.append({"icdCode": d.get("code", ""), "icdName": d.get("name", d.get("code", ""))})
    if chronic:
        payload["healthDigitalDiseaseDTO"] = {
            "chronicDiseaseDTOList": chronic,
            "specialDiseaseDTOList": [],
        }

    return payload


async def sync_patient_data_node(state: AgentState) -> AgentState:
    """Sync patient data to third-party via addHumanInfo after questionnaire completion.

    Best-effort: failure is logged but does not block the pipeline.
    """
    settings = get_settings()
    if not settings.external_api_enabled:
        logger.info("External API disabled, skipping sync_patient_data")
        return state

    if not state.party_id:
        logger.info("No party_id, skipping sync_patient_data")
        return state

    state.current_step = "sync_patient_data"
    payload = _build_add_human_info_payload(state)
    if not payload:
        logger.info("Empty payload for addHumanInfo, skipping")
        return state

    try:
        from mcp_servers.profile_server.pingan_client import PingAnHealthArchiveClient
        async with PingAnHealthArchiveClient() as client:
            ok = await client.add_human_info(payload)
        if ok:
            logger.info(f"sync_patient_data success for party_id={state.party_id}")
        else:
            logger.warning(f"sync_patient_data API returned failure for party_id={state.party_id}")
    except Exception as e:
        logger.warning(f"sync_patient_data error (non-blocking): {e}")

    return state


def _build_insight_save_payload(state: AgentState) -> Optional[Dict[str, Any]]:
    """Build insightSave request payload from structured_output / skill results."""
    so = state.structured_output
    if not so:
        return None

    party_id = state.party_id or state.patient_id

    # Extract risk_level from risk_warnings or structured result
    risk_level = "low"
    risk_warnings = so.get("risk_warnings") or []
    if isinstance(risk_warnings, list) and risk_warnings:
        # Take the highest risk level from warnings
        for w in risk_warnings:
            if isinstance(w, dict):
                level = w.get("level", "").lower()
                if level == "high":
                    risk_level = "high"
                    break
                elif level == "medium" and risk_level != "high":
                    risk_level = "medium"
    # Also check top-level risk_level if present
    if so.get("risk_level"):
        risk_level = so["risk_level"]

    payload: Dict[str, Any] = {
        "party_id": party_id,
        "risk_level": risk_level,
        "population_classification": so.get("population_classification", {}),
        "abnormal_indicators": so.get("abnormal_indicators", {}),
        "recommended_data_collection": so.get("recommended_data_collection", []),
        "disease_prediction": so.get("disease_prediction", []),
        "intervention_prescriptions": so.get("intervention_prescriptions", []),
        "risk_warnings": risk_warnings,
        "assessed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recommended_target": so.get("recommended_target", []),
    }
    return payload


async def push_insight_node(state: AgentState) -> AgentState:
    """Push insight data to third-party via insightSave after skill aggregation.

    Best-effort: failure is logged but does not block the pipeline.
    """
    settings = get_settings()
    if not settings.external_api_enabled:
        logger.info("External API disabled, skipping push_insight")
        return state

    if not state.party_id and not state.patient_id:
        logger.info("No party_id/patient_id, skipping push_insight")
        return state

    state.current_step = "push_insight"
    payload = _build_insight_save_payload(state)
    if not payload:
        logger.info("No structured_output, skipping push_insight")
        return state

    try:
        from mcp_servers.profile_server.pingan_client import PingAnHealthArchiveClient
        async with PingAnHealthArchiveClient() as client:
            ok = await client.save_insight(payload)
        if ok:
            logger.info(f"push_insight success for party_id={state.party_id or state.patient_id}")
        else:
            logger.warning(f"push_insight API returned failure")
    except Exception as e:
        logger.warning(f"push_insight error (non-blocking): {e}")

    return state
