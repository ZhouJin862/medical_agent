"""
LangGraph Nodes - Individual processing nodes for the agent workflow.

Each node performs a specific step in the health assessment workflow.

Skill Execution:
    Skills are executed using MS-Agent ScriptExecutor (preferred) with subprocess fallback.
    See src/infrastructure/agent/ms_agent_executor.py for details.

Available Backends:
    1. MS-Agent ScriptExecutor - In-process execution, auto-parses SKILL.md
    2. Subprocess - Direct Python script execution (fallback)
    3. DSPy - Database-driven skills (legacy)
"""

import logging
import sys
import time
from typing import Any, Dict, Optional, List
from datetime import datetime

from src.infrastructure.agent.state import (
    AgentState,
    AgentStatus,
    IntentType,
    SkillExecutionResult,
    PatientContext,
    ConversationMemory,
)

logger = logging.getLogger(__name__)


# Mapping from Ping An indicator names (Chinese) to skill field names.
# Shared by indicatorItems and cycleItems formats.
_INDICATOR_NAME_MAPPING = {
    # 血压相关
    "收缩压": "systolic_bp",
    "舒张压": "diastolic_bp",
    "高压": "systolic_bp",
    "低压": "diastolic_bp",

    # 血糖相关
    "空腹血糖": "fasting_glucose",
    "餐后血糖": "postprandial_glucose",
    "随机血糖": "random_glucose",
    "糖化血红蛋白": "hba1c",

    # 血脂相关
    "总胆固醇": "total_cholesterol",
    "甘油三酯": "tg",
    "低密度脂蛋白": "ldl_c",
    "高密度脂蛋白": "hdl_c",
    "LDL-C": "ldl_c",
    "HDL-C": "hdl_c",

    # 其他
    "尿酸": "uric_acid",
    "血尿酸": "uric_acid",
    "身高": "height",
    "体重": "weight",
    "腰围": "waist",
    "BMI": "bmi",
}


def _map_ping_an_indicators_to_vital_signs(indicator_items: List[Dict]) -> Dict[str, Any]:
    """
    Map Ping An indicatorItems format to the flat vital_signs format expected by skills.

    Args:
        indicator_items: Array of indicator objects from Ping An API
            Each object has: indicatorName, indicatorValue, indicatorUnit

    Returns:
        Flattened vital_signs dict with keys like systolic_bp, diastolic_bp, etc.
    """
    vital_signs = {}
    if not indicator_items:
        return vital_signs

    for item in indicator_items:
        indicator_name = item.get("indicatorName", "")
        indicator_value = item.get("indicatorValue")
        indicator_unit = item.get("indicatorUnit", "")

        # Skip if no value
        if indicator_value is None or indicator_value == "":
            continue

        # Find matching field name
        field_name = None
        for ping_an_name, skill_name in _INDICATOR_NAME_MAPPING.items():
            if ping_an_name in indicator_name or indicator_name in ping_an_name:
                field_name = skill_name
                break

        if not field_name:
            # If no direct mapping, try to infer from the name
            if "收缩" in indicator_name or "高压" in indicator_name:
                field_name = "systolic_bp"
            elif "舒张" in indicator_name or "低压" in indicator_name:
                field_name = "diastolic_bp"
            elif "血糖" in indicator_name and "空腹" in indicator_name:
                field_name = "fasting_glucose"
            elif "血糖" in indicator_name and "餐后" in indicator_name:
                field_name = "postprandial_glucose"
            elif "胆固醇" in indicator_name:
                field_name = "total_cholesterol"
            elif "甘油" in indicator_name:
                field_name = "tg"
            elif "低密度" in indicator_name or "LDL" in indicator_name.upper():
                field_name = "ldl_c"
            elif "高密度" in indicator_name or "HDL" in indicator_name.upper():
                field_name = "hdl_c"
            elif "尿酸" in indicator_name:
                field_name = "uric_acid"
            elif "身高" in indicator_name:
                field_name = "height"
            elif "体重" in indicator_name:
                field_name = "weight"
            elif "腰围" in indicator_name:
                field_name = "waist"
            else:
                # Store unmapped indicators in a generic format
                vital_signs[f"indicator_{indicator_name}"] = {
                    "value": indicator_value,
                    "unit": indicator_unit
                }
                continue

        # Convert value to appropriate type
        try:
            # Try to convert to float
            numeric_value = float(indicator_value)
            vital_signs[field_name] = numeric_value
        except (ValueError, TypeError):
            # Keep as string if conversion fails
            vital_signs[field_name] = indicator_value

    # Calculate BMI if height and weight are available (only if not already provided)
    if "bmi" not in vital_signs and "height" in vital_signs and "weight" in vital_signs:
        try:
            h = float(vital_signs["height"])
            height_m = h / 100.0 if h > 2.5 else h  # cm → m if needed
            weight = float(vital_signs["weight"])
            if height_m > 0:
                vital_signs["bmi"] = round(weight / (height_m * height_m), 1)
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    # Store original indicators for reference
    vital_signs["indicators"] = indicator_items

    return vital_signs


def _map_cycle_items_to_vital_signs(cycle_items: List[Dict]) -> Dict[str, Any]:
    """
    Map Ping An cycleItems format to vital_signs.

    cycleItems uses {itemName, itemValue} instead of {indicatorName, indicatorValue}.
    Multiple entries for the same indicator represent different measurements;
    the LAST (most recent) value wins.

    Args:
        cycle_items: Array of {itemName, itemValue} dicts from Ping An API

    Returns:
        Flattened vital_signs dict
    """
    vital_signs = {}
    if not cycle_items:
        return vital_signs

    for item in cycle_items:
        item_name = item.get("itemName", "")
        item_value = item.get("itemValue")

        if item_value is None or item_value == "":
            continue

        # Find matching field name from shared mapping
        field_name = None
        for cn_name, skill_name in _INDICATOR_NAME_MAPPING.items():
            if cn_name in item_name or item_name in cn_name:
                field_name = skill_name
                break

        if not field_name:
            # Fuzzy inference (same logic as indicatorItems handler)
            if "收缩" in item_name or "高压" in item_name:
                field_name = "systolic_bp"
            elif "舒张" in item_name or "低压" in item_name:
                field_name = "diastolic_bp"
            elif "血糖" in item_name and "空腹" in item_name:
                field_name = "fasting_glucose"
            elif "血糖" in item_name and "餐后" in item_name:
                field_name = "postprandial_glucose"
            elif "胆固醇" in item_name:
                field_name = "total_cholesterol"
            elif "甘油" in item_name:
                field_name = "tg"
            elif "低密度" in item_name or "LDL" in item_name.upper():
                field_name = "ldl_c"
            elif "高密度" in item_name or "HDL" in item_name.upper():
                field_name = "hdl_c"
            elif "尿酸" in item_name:
                field_name = "uric_acid"
            elif "身高" in item_name:
                field_name = "height"
            elif "体重" in item_name:
                field_name = "weight"
            elif "腰围" in item_name:
                field_name = "waist"
            else:
                continue  # Skip unmapped items (avoid bloating vital_signs)

        # Convert value to appropriate type — last value wins
        try:
            vital_signs[field_name] = float(item_value)
        except (ValueError, TypeError):
            vital_signs[field_name] = item_value

    # Calculate BMI if height and weight are available (only if not already provided)
    if "bmi" not in vital_signs and "height" in vital_signs and "weight" in vital_signs:
        try:
            h = float(vital_signs["height"])
            height_m = h / 100.0 if h > 2.5 else h  # cm → m if needed
            weight = float(vital_signs["weight"])
            if height_m > 0:
                vital_signs["bmi"] = round(weight / (height_m * height_m), 1)
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    return vital_signs


# Mapping for new Ping An API flat field format
_PING_AN_FLAT_FIELD_MAPPING = {
    "systolicPressure": "systolic_bp",
    "diastolicPressure": "diastolic_bp",
    "fastingBloodGlucose": "fasting_glucose",
    "hbalc": "hba1c",
    "tc": "total_cholesterol",
    "tg": "tg",
    "ldlc": "ldl_c",
    "hdlc": "hdl_c",
    "bloodUricAcid": "uric_acid",
    "height": "height",
    "weight": "weight",
    "waistCircumference": "waist",
}


def _map_ping_an_flat_fields_to_vital_signs(api_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map new Ping An flat field format to vital_signs dict.

    Maps known fields to skill-expected keys, then preserves all remaining
    raw API fields so no data is lost.

    Args:
        api_data: Flat API data dict

    Returns:
        Vital signs dict with mapped keys + all original fields preserved
    """
    vital_signs = {}

    # First pass: map known fields to skill-expected keys
    mapped_api_fields = set()
    for api_field, skill_field in _PING_AN_FLAT_FIELD_MAPPING.items():
        if api_field in api_data and api_data[api_field] is not None:
            value = api_data[api_field]
            try:
                vital_signs[skill_field] = float(value)
            except (ValueError, TypeError):
                vital_signs[skill_field] = value
            mapped_api_fields.add(api_field)

    # Second pass: preserve all unmapped raw API fields (age, gender, and any future fields)
    _INTERNAL_META_KEYS = {"_api_response", "_metadata", "diseaseLabels"}
    for api_field, value in api_data.items():
        if api_field in _INTERNAL_META_KEYS:
            continue
        if api_field not in mapped_api_fields and value is not None:
            try:
                vital_signs[api_field] = float(value)
            except (ValueError, TypeError):
                vital_signs[api_field] = value

    # Calculate BMI if height and weight are available (only if not already provided)
    if "bmi" not in vital_signs and "height" in vital_signs and "weight" in vital_signs:
        try:
            h = float(vital_signs["height"])
            # Height > 2.5 means it's in cm; convert to meters
            height_m = h / 100.0 if h > 2.5 else h
            weight = float(vital_signs["weight"])
            if height_m > 0:
                vital_signs["bmi"] = round(weight / (height_m * height_m), 1)
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    return vital_signs


def _extract_vital_signs_from_user_input(user_input: str, existing_vital_signs: dict = None) -> dict:
    """
    Extract vital signs from user's natural language input.

    Supports various Chinese and English formats for health metrics.

    Args:
        user_input: User's message containing health data
        existing_vital_signs: Existing vital signs to merge with extracted data

    Returns:
        Updated vital signs dict with extracted values
    """
    import re

    if existing_vital_signs is None:
        vital_signs = {}
    else:
        vital_signs = existing_vital_signs.copy()

    # Normalize the input for easier parsing
    text = user_input.lower()

    # Patterns for extracting vital signs
    # Format: (regex_pattern, field_name, conversion_func)

    patterns = [
        # 年龄 - Age (支持多种格式：45岁、年龄45、今年45岁)
        (r'(\d+)\s*岁', '_age', int),
        (r'年龄[:：]\s*(\d+)', '_age', int),

        # 血压相关 - Blood Pressure (more flexible to handle parentheses and extra text)
        (r'(?:收缩压|高压|systolic|sbp)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmhg)?', 'systolic_bp', float),
        (r'(?:舒张压|低压|diastolic|dbp)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmhg)?', 'diastolic_bp', float),
        (r'血压[:：\s]*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(?:mmhg)?', 'bp_pair', lambda m: (float(m.group(1)), float(m.group(2)))),

        # 身高体重腰围 - Height, Weight, Waist (more flexible)
        (r'(?:身高|height)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:cm|厘米)?', 'height', float),
        (r'(?:体重|weight)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:kg|公斤|千克)?', 'weight', float),
        (r'(?:腰围|waist)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:cm|厘米)?', 'waist', float),

        # 血糖相关 - Blood Glucose (more flexible)
        (r'(?:空腹血糖|fasting\s*glucose|fg|空腹)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmol/l|mmol)?', 'fasting_glucose', float),
        (r'(?:餐后血糖|postprandial\s*glucose|pg|餐后)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmol/l|mmol)?', 'postprandial_glucose', float),
        (r'(?:糖化血红蛋白|hba1c|糖化)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:%|percent)?', 'hba1c', float),

        # 血脂相关 - Blood Lipids (more flexible to handle TC, TG, LDL-C, HDL-C)
        (r'(?:总胆固醇|tc|total\s*cholesterol)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmol/l|mmol)?', 'total_cholesterol', float),
        (r'(?:甘油三酯|tg|triglycerides)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmol/l|mmol)?', 'tg', float),
        (r'(?:低密度脂蛋白|ldl-c|ldl|low\s*density\s*lipoprotein)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmol/l|mmol)?', 'ldl_c', float),
        (r'(?:高密度脂蛋白|hdl-c|hdl|high\s*density\s*lipoprotein)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:mmol/l|mmol)?', 'hdl_c', float),

        # 尿酸 - Uric Acid (more flexible)
        (r'(?:尿酸|uric\s*acid|ua|血尿酸)(?:[（(][^)）]*[)）])?[:：\s]*(\d+(?:\.\d+)?)\s*(?:μmol/l|umol/l)?', 'uric_acid', float),
    ]

    extracted_count = 0
    for pattern_str, field_name, converter in patterns:
        match = re.search(pattern_str, text, re.IGNORECASE)
        if match:
            if field_name == 'bp_pair':
                # Handle paired blood pressure values
                systolic, diastolic = converter(match)
                vital_signs['systolic_bp'] = systolic
                vital_signs['diastolic_bp'] = diastolic
                logger.info(f"Extracted BP: {systolic}/{diastolic}")
                extracted_count += 2
            else:
                # For other fields, extract the captured group and convert it
                captured_value = match.group(1)
                value = converter(captured_value) if callable(converter) else captured_value

                # Handle _age specially - extract to return separately for basic_info
                if field_name == '_age':
                    vital_signs['_extracted_age'] = value
                else:
                    vital_signs[field_name] = value
                logger.info(f"Extracted {field_name}: {value}")
                extracted_count += 1

    # Calculate BMI if height and weight are available (only if not already provided)
    if 'bmi' not in vital_signs and 'height' in vital_signs and 'weight' in vital_signs:
        try:
            h = float(vital_signs['height'])
            height_m = h / 100.0 if h > 2.5 else h  # cm → m if needed
            weight = float(vital_signs['weight'])
            if height_m > 0:
                vital_signs['bmi'] = round(weight / (height_m * height_m), 1)
                logger.info(f"Calculated BMI: {vital_signs['bmi']}")
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    if extracted_count > 0:
        logger.info(f"Extracted {extracted_count} vital signs from user input")

    return vital_signs


def _extract_vital_signs_from_memories(memories: List[Dict[str, Any]], party_id: str) -> dict:
    """
    Extract vital signs from mem0 conversation memories for a specific party_id.

    Searches through memories for messages containing health data associated with
    the given party_id, then uses _extract_vital_signs_from_user_input to parse them.

    Args:
        memories: List of mem0 memory entries
        party_id: The customer ID to filter memories for

    Returns:
        Dict of extracted vital signs
    """
    if not party_id or not memories:
        return {}

    # Collect memory content that mentions this party_id and contains health data
    health_keywords = ['血压', '血糖', '血脂', '胆固醇', '尿酸', 'mmHg', 'mmol', 'BMI',
                        'systolic', 'diastolic', 'glucose', 'cholesterol', 'HbA1c',
                        'LDL', 'HDL', '甘油三酯', '糖化', '空腹', '收缩压', '舒张压']
    best_result = {}

    for mem in memories:
        content = mem.get("memory", "")
        if not content:
            continue
        # Only consider memories that mention this party_id
        if party_id not in content:
            continue
        # Check if it contains health data
        if not any(kw in content for kw in health_keywords):
            continue
        # Try to extract vital signs from this memory
        extracted = _extract_vital_signs_from_user_input(content)
        # Filter out metadata fields like _extracted_age
        vital_only = {k: v for k, v in extracted.items() if not k.startswith('_')}
        if len(vital_only) > len(best_result):
            best_result = vital_only
            if len(best_result) >= 5:
                # Good enough, stop searching
                break

    if best_result:
        logger.info(f"Extracted {len(best_result)} vital signs from memory for party_id={party_id}: {list(best_result.keys())}")

    return best_result


async def load_patient_node(state: AgentState) -> AgentState:
    """
    Load patient data from MCP profile service (with graceful fallback).

    Args:
        state: Current agent state

    Returns:
        Updated agent state with patient context
    """
    logger.info(f"Loading patient data for patient_id: {state.patient_id}")
    state.status = AgentStatus.LOADING_PATIENT
    state.current_step = "load_patient"

    patient_data = {}
    vital_signs = {}
    medical_records = {}

    # Determine if we should use previous_patient_context
    # CRITICAL: Only use previous context if the party_id hasn't changed.
    # Mixing data from different customers leads to incorrect assessments.
    use_previous_context = False
    if state.previous_patient_context:
        prev_party_id = state.previous_patient_context.get("basic_info", {}).get("party_id")
        current_party_id = state.party_id

        if current_party_id and prev_party_id and current_party_id != prev_party_id:
            logger.warning(
                f"Party ID changed: previous={prev_party_id}, current={current_party_id}. "
                f"Discarding previous patient context to avoid data mixing."
            )
            use_previous_context = False
        else:
            use_previous_context = True

    if use_previous_context:
        logger.info("Using previous patient context as base (same party_id)")
        patient_data = state.previous_patient_context.get("basic_info", {}).copy()
        vital_signs = state.previous_patient_context.get("vital_signs", {}).copy()
        medical_records = state.previous_patient_context.get("medical_history", {}).copy()

    # Check if Ping An health data was already fetched by streaming_chat.py
    if state.ping_an_health_data:
        logger.info(f"Using pre-fetched Ping An health data from streaming_chat")
        api_data = state.ping_an_health_data
        party_id = state.party_id

        # Build basic_info from Ping An data
        basic_info = {"patient_id": state.patient_id, "party_id": party_id, "source": "ping_an_api"}
        # Extract age from multiple possible field names (direct fields)
        # IMPORTANT: Convert age to integer (Ping An API returns string)
        age_found = False
        for age_field in ["age", "customerAge", "patientAge", "personAge", "userAge"]:
            if age_field in api_data and api_data[age_field]:
                basic_info["age"] = int(str(api_data[age_field]).strip())
                logger.info(f"Found age in field '{age_field}': {api_data[age_field]} -> {basic_info['age']}")
                age_found = True
                break
        # Also check nested structures (e.g., personInfo.age, customer.age)
        if not age_found:
            for nested_key in ["personInfo", "customer", "customerInfo", "patientInfo", "basicInfo"]:
                if nested_key in api_data and isinstance(api_data[nested_key], dict):
                    if "age" in api_data[nested_key]:
                        basic_info["age"] = int(str(api_data[nested_key]["age"]).strip())
                        logger.info(f"Found age in nested field '{nested_key}.age': {api_data[nested_key]['age']} -> {basic_info['age']}")
                        age_found = True
                        break

        # Extract gender if available (normalize F/M to female/male)
        if "gender" in api_data and api_data["gender"]:
            g = str(api_data["gender"]).strip().upper()
            if g in ("F", "FEMALE", "女"):
                basic_info["gender"] = "female"
            elif g in ("M", "MALE", "男"):
                basic_info["gender"] = "male"
            else:
                basic_info["gender"] = api_data["gender"]

        # Extract diseaseLabels (new field with disease names)
        disease_labels = api_data.get("diseaseLabels", [])

        # Detect API response format: indicatorItems vs cycleItems vs flat fields
        if "indicatorItems" in api_data:
            # Old format: indicatorItems array
            vital_signs = _map_ping_an_indicators_to_vital_signs(api_data.get("indicatorItems", []))
            diagnoses = []
            if "diseaseHistory" in api_data:
                diagnoses = [{"code": code} for code in api_data["diseaseHistory"]]
            medical_records = {
                "diagnoses": diagnoses,
                "medications": api_data.get("medications", []),
                "allergies": api_data.get("allergies", []),
                "chronic_diseases": diagnoses,
                "disease_labels": disease_labels,
                "sport_records": api_data.get("sportRecords", {}),
            }
        elif "cycleItems" in api_data and isinstance(api_data["cycleItems"], list):
            # Ping An Health Archive cycleItems format: {itemName, itemValue} pairs
            vital_signs = _map_cycle_items_to_vital_signs(api_data["cycleItems"])
            # Also pick up any flat fields at top level (e.g. if API returns both)
            flat_vs = _map_ping_an_flat_fields_to_vital_signs(api_data)
            for k, v in flat_vs.items():
                if k not in vital_signs and v is not None:
                    vital_signs[k] = v
            diagnoses = []
            if "diseaseHistory" in api_data:
                diagnoses = [{"code": code} for code in api_data["diseaseHistory"]]
            medical_records = {
                "diagnoses": diagnoses,
                "medications": api_data.get("medications", []),
                "allergies": api_data.get("allergies", []),
                "chronic_diseases": diagnoses,
                "disease_labels": disease_labels,
                "sport_records": api_data.get("sportRecords", {}),
            }
        else:
            # New format: flat fields (systolicPressure, diastolicPressure, etc.)
            vital_signs = _map_ping_an_flat_fields_to_vital_signs(api_data)
            diagnoses = []
            if "diseaseHistory" in api_data:
                diagnoses = [{"code": code} for code in api_data["diseaseHistory"]]
            medical_records = {
                "diagnoses": diagnoses,
                "medications": api_data.get("medications", []),
                "allergies": api_data.get("allergies", []),
                "chronic_diseases": diagnoses,
                "disease_labels": disease_labels,
                "sport_records": api_data.get("sportRecords", {}),
            }

        patient_data = {
            "basic_info": basic_info,
            "patient_id": state.patient_id,
            "party_id": party_id,
            "source": "ping_an_api",
            "has_health_data": True,
        }

        logger.info(f"Successfully loaded pre-fetched health data from Ping An API for party_id: {party_id}")
        logger.info(f"  - Age: {api_data.get('age', 'N/A')}, Gender: {api_data.get('gender', 'N/A')}")
        logger.info(f"  - Vital signs: {list(vital_signs.keys())}")
        logger.info(f"  - Diagnoses: {len(diagnoses)} conditions")
        logger.info(f"  - Disease labels: {disease_labels}")

    else:
        # No pre-fetched data, try to load from MCP
        logger.info(f"No pre-fetched data, loading from MCP")
        try:
            # Import MCP client factory
            from src.infrastructure.mcp import MCPClientFactory

            # Get profile client
            profile_client = MCPClientFactory.get_client("profile_server")

            # Try to use get_health_data if party_id is available
            party_id = state.party_id

            # Extract party_id from user input if not set
            if not party_id and isinstance(state.user_input, str):
                import re
                patterns = [
                    r'客户号[：:]\s*([A-Za-z0-9]+)',
                    r'partyId[：:]\s*([A-Za-z0-9]+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, state.user_input, re.IGNORECASE)
                    if match:
                        party_id = match.group(1)
                        logger.info(f"Extracted party_id from user input: {party_id}")
                        break

            if party_id:
                try:
                    # Use Ping An health data API with party_id
                    logger.info(f"Using get_health_data for party_id: {party_id}")
                    health_data = await profile_client.call_tool(
                        "get_health_data",
                        {"party_id": party_id}
                    )

                    # Parse the response structure from Ping An API
                    if "error" not in health_data and health_data.get("code") == "S000000":
                        # Success - extract the data field
                        api_data = health_data.get("data", health_data)

                        # Build basic_info from Ping An data
                        basic_info = {"patient_id": state.patient_id, "party_id": party_id, "source": "ping_an_api"}
                        # Extract age from multiple possible field names (direct fields)
                        # IMPORTANT: Convert age to integer (Ping An API returns string)
                        age_found = False
                        for age_field in ["age", "customerAge", "patientAge", "personAge", "userAge"]:
                            if age_field in api_data and api_data[age_field]:
                                basic_info["age"] = int(str(api_data[age_field]).strip())
                                logger.info(f"Found age in field '{age_field}': {api_data[age_field]} -> {basic_info['age']}")
                                age_found = True
                                break
                        # Also check nested structures (e.g., personInfo.age, customer.age)
                        if not age_found:
                            for nested_key in ["personInfo", "customer", "customerInfo", "patientInfo", "basicInfo"]:
                                if nested_key in api_data and isinstance(api_data[nested_key], dict):
                                    if "age" in api_data[nested_key]:
                                        basic_info["age"] = int(str(api_data[nested_key]["age"]).strip())
                                        logger.info(f"Found age in nested field '{nested_key}.age': {api_data[nested_key]['age']} -> {basic_info['age']}")
                                        age_found = True
                                        break

                        # Map diseaseHistory to diagnoses
                        diagnoses = []
                        if "diseaseHistory" in api_data:
                            diagnoses = [{"code": code} for code in api_data["diseaseHistory"]]

                        # Detect API response format and map accordingly
                        if "indicatorItems" in api_data:
                            # Old format: indicatorItems array
                            vital_signs = _map_ping_an_indicators_to_vital_signs(api_data.get("indicatorItems", []))
                        else:
                            # New format: flat fields (systolicPressure, diastolicPressure, etc.)
                            vital_signs = _map_ping_an_flat_fields_to_vital_signs(api_data)

                        # Extract gender if available
                        if "gender" in api_data and api_data["gender"]:
                            basic_info["gender"] = api_data["gender"]

                        # Add sport records to medical history
                        medical_records = {
                            "diagnoses": diagnoses,
                            "medications": api_data.get("medications", []),
                            "allergies": api_data.get("allergies", []),
                            "chronic_diseases": diagnoses,
                            "disease_labels": api_data.get("diseaseLabels", []),
                            "sport_records": api_data.get("sportRecords", {}),
                        }

                        patient_data = {
                            "basic_info": basic_info,
                            "patient_id": state.patient_id,
                            "party_id": party_id,
                            "source": "ping_an_api",
                            "has_health_data": True,
                        }

                        logger.info(f"Successfully loaded health data from Ping An API for party_id: {party_id}")
                    else:
                        logger.warning(f"Ping An API returned error: {health_data.get('error')}")
                        raise Exception("Ping An API error")

                except Exception as e:
                    logger.warning(f"get_health_data failed: {e}, using fallback")

        except Exception as e:
            logger.warning(f"Failed to load patient data from MCP: {e}, using fallback")

    # Extract and merge vital signs from user input (for follow-up messages)
    # This allows users to provide missing data in subsequent messages
    vital_signs = _extract_vital_signs_from_user_input(state.user_input, vital_signs)

    # Check if age was extracted from user input
    if '_extracted_age' in vital_signs:
        extracted_age = vital_signs.pop('_extracted_age')
        if patient_data and 'basic_info' in patient_data:
            patient_data['basic_info']['age'] = extracted_age
            logger.info(f"Extracted age from user input: {extracted_age}")

    # Create patient context
    state.patient_context = PatientContext(
        patient_id=state.patient_id,
        basic_info=patient_data.get("basic_info", {}) if patient_data else {},
        vital_signs=vital_signs,
        medical_history=medical_records if medical_records else {},
        last_updated=datetime.now(),
    )

    logger.info(f"Successfully loaded patient data for: {state.patient_id}")

    return state


async def retrieve_memory_node(state: AgentState) -> AgentState:
    """
    Retrieve conversation memory from Mem0.

    Args:
        state: Current agent state

    Returns:
        Updated agent state with conversation memory
    """
    logger.info(f"Retrieving memory for patient_id: {state.patient_id}")
    state.status = AgentStatus.RETRIEVING_MEMORY
    state.current_step = "retrieve_memory"

    user_profile = {}
    context_parts = []

    try:
        # Import memory store
        from src.infrastructure.memory import MemoryStore

        memory_store = MemoryStore()

        # Get all memories for this patient (used for user profile & vital signs extraction)
        all_memories = await memory_store.get_all(state.patient_id)

        # Filter to current session memories for conversation context
        if state.session_id:
            session_memories = [
                m for m in all_memories
                if m.get("metadata", {}).get("session_id") == state.session_id
            ]
            logger.info(
                f"Filtered to {len(session_memories)} session memories "
                f"(session_id={state.session_id}) out of {len(all_memories)} total"
            )
        else:
            session_memories = all_memories

        # Build context summary from session memories only
        for mem in session_memories[-20:]:  # Last 20 messages in this session
            role = mem.get("metadata", {}).get("role", "unknown")
            content = mem.get("memory", "")
            if content:
                context_parts.append(f"{role}: {content}")

        # Extract user profile from ALL memories (cross-session, for continuity)
        user_profile = _extract_user_profile(all_memories)

        # Create conversation memory with session-scoped messages
        state.conversation_memory = ConversationMemory(
            conversation_id=state.session_id or state.patient_id,
            messages=session_memories,
            context_summary="\n".join(context_parts) if context_parts else None,
            previous_assessments=[],  # Could be populated from structured outputs
        )

        # Store user profile in patient context for later use
        if state.patient_context:
            if user_profile:
                # Only fill in missing fields, don't overwrite existing values
                # (e.g. party_id set by Ping An API should not be overwritten by mem0 extraction)
                for key, value in user_profile.items():
                    if key not in state.patient_context.basic_info or not state.patient_context.basic_info[key]:
                        state.patient_context.basic_info[key] = value
            # Update basic info with patient_id if not set
            if not state.patient_context.basic_info:
                state.patient_context.basic_info["patient_id"] = state.patient_id

            # Reconstruct vital signs from ALL memories (cross-session, for continuity)
            if not state.patient_context.vital_signs and state.party_id:
                memory_vital_signs = _extract_vital_signs_from_memories(all_memories, state.party_id)
                if memory_vital_signs:
                    state.patient_context.vital_signs = memory_vital_signs
                    logger.info(f"Reconstructed {len(memory_vital_signs)} vital signs from memory for party_id={state.party_id}")

        logger.info(f"Retrieved {len(session_memories)} session memories, {len(all_memories)} total memories")
        if user_profile:
            logger.info(f"Extracted user profile: {list(user_profile.keys())}")

    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        # Memory retrieval failure is not critical
        state.conversation_memory = ConversationMemory(
            conversation_id=state.patient_id,
        )

    return state


def _extract_user_profile(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract user profile information from conversation history.

    Looks for patterns like "我叫..." (name), "今年...岁" (age), party_id (客户号), etc.
    """
    import re

    profile = {}

    # Join all user messages for analysis
    user_messages = [
        mem.get("memory", "")
        for mem in memories
        if mem.get("metadata", {}).get("role") == "user"
    ]
    all_text = " ".join(user_messages)

    # Extract name
    name_patterns = [
        r'我叫(\S+)',
        r'我是(\S+)',
        r'我的名字是(\S+)',
        r'我叫(\S+)，',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, all_text)
        if match:
            profile["name"] = match.group(1)
            break

    # Extract age
    age_patterns = [
        r'(\d+)岁',
        r'(\d+)岁，',
        r'今年(\d+)岁',
        r'年龄(\d+)',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, all_text)
        if match:
            profile["age"] = match.group(1)
            break

    # Extract party_id (客户号) for Ping An health archive
    # Look for patterns like "客户号123456", "partyId: xxx", etc.
    party_id_patterns = [
        r'客户号[：:]\s*([A-Za-z0-9]+)',
        r'客户号\s*([A-Za-z0-9]+)',
        r'partyId[：:]\s*([A-Za-z0-9]+)',
        r'party_id[：:]\s*([A-Za-z0-9]+)',
        r'party\s*id[：:]\s*([A-Za-z0-9]+)',
        r'客户编号[：:]\s*([A-Za-z0-9]+)',
        r'编号[：:]\s*([A-Za-z0-9]{8,})',  # 8+ digit IDs
    ]
    for pattern in party_id_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            profile["party_id"] = match.group(1)
            logger.info(f"Extracted party_id from conversation: {match.group(1)}")
            break

    # Extract symptoms/issues mentioned
    symptom_keywords = ['头晕', '头痛', '发热', '咳嗽', '失眠', '疲劳', '高血压', '糖尿病']
    mentioned_symptoms = []
    for keyword in symptom_keywords:
        if keyword in all_text:
            mentioned_symptoms.append(keyword)

    if mentioned_symptoms:
        profile["mentioned_symptoms"] = mentioned_symptoms

    return profile


async def _execute_file_skill(
    skill_name: str,
    user_input: str,
    patient_context: Optional[PatientContext] = None,
) -> Optional[SkillExecutionResult]:
    """
    Execute a file-based skill from the skills/ directory.

    .. deprecated::
        This function is kept for backward compatibility.
        Skill execution has been moved to ms_agent_executor.py which supports:
        - MS-Agent ScriptExecutor (preferred)
        - Subprocess fallback

        Use execute_skill_via_msagent() from ms_agent_executor.py instead.

    File-based skills have:
    - skills/{skill_name}/SKILL.md - Skill definition
    - skills/{skill_name}/scripts/*.py - Execution scripts

    Args:
        skill_name: Name of the skill to execute
        user_input: User's input/query
        patient_context: Optional patient context

    Returns:
        SkillExecutionResult or None if execution failed
    """
    from pathlib import Path

    skill_dir = Path("skills") / skill_name
    if not skill_dir.exists():
        logger.debug(f"Skill directory not found: {skill_dir}")
        return None

    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        logger.debug(f"Scripts directory not found: {scripts_dir}")
        return None

    # Look for main execution script
    main_script = scripts_dir / "main.py"
    if not main_script.exists():
        # Try alternative script names
        for script_file in scripts_dir.glob("*.py"):
            if script_file.name.startswith("main") or script_file.name.startswith(skill_name.replace("-", "_")):
                main_script = script_file
                break

    if not main_script.exists():
        logger.debug(f"No main execution script found in: {scripts_dir}")
        return None

    try:
        # Import and execute the skill script
        import subprocess
        import json

        # Prepare input data
        input_data = {
            "user_input": user_input,  # Pass actual user input for natural language parsing
            "patient_data": patient_context.basic_info if patient_context else {},
            "vital_signs": patient_context.vital_signs if patient_context else {},
            "medical_history": patient_context.medical_history if patient_context else {},
        }

        # Debug log the input data
        logger.info(f"Executing file skill: {skill_name}, input keys={list(input_data.keys())}")

        # For now, use subprocess to execute the script
        start_time = time.time()

        # Create a temporary input file with explicit UTF-8 encoding
        # Use a simple filename to avoid encoding issues on Windows
        import tempfile
        import uuid
        temp_dir = Path(tempfile.gettempdir())
        input_filename = f"skill_input_{uuid.uuid4().hex[:8]}.json"
        input_file = temp_dir / input_filename

        # Write JSON data with explicit UTF-8 encoding
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(input_data, f, ensure_ascii=False)

        logger.info(f"Created skill input file: {input_file}")

        try:
            # Execute the script using absolute path
            # Set cwd to the script's directory so imports work correctly
            # Also modify PYTHONPATH to ensure sibling modules can be imported
            import os
            env = os.environ.copy()
            # Add the skills directory to PYTHONPATH
            # This allows scripts to import sibling modules like risk_calculator, template_manager
            skills_dir = str(skill_dir.absolute())
            env['PYTHONPATH'] = skills_dir + os.pathsep + env.get('PYTHONPATH', '')
            # Force UTF-8 encoding for subprocess I/O (fixes Windows GBK codec issues)
            env['PYTHONIOENCODING'] = 'utf-8'
            logger.info(f"Skill PYTHONPATH: {env['PYTHONPATH']}")

            result = subprocess.run(
                [sys.executable, str(main_script.absolute()), "--input", str(input_file), "--mode", "skill"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(main_script.parent.absolute()),  # Set working directory to script's directory
                env=env,  # Pass modified environment with PYTHONPATH
                encoding='utf-8',  # Explicitly set UTF-8 encoding
                errors='replace'  # Replace characters that can't be decoded
            )

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(f"Skill subprocess completed: returncode={result.returncode}, stdout_len={len(result.stdout)}")
            if result.stderr:
                logger.warning(f"Skill stderr: {result.stderr[:500]}")

            # Parse output
            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)
                    return SkillExecutionResult(
                        skill_name=skill_name,
                        success=True,
                        result_data=output_data,
                        execution_time=execution_time,
                    )
                except json.JSONDecodeError as e:
                    logger.warning(f"Skill output JSONDecodeError: {e}")
                    # Script returned text output, not JSON
                    return SkillExecutionResult(
                        skill_name=skill_name,
                        success=True,
                        result_data={"output": result.stdout},
                        execution_time=execution_time,
                    )
            else:
                logger.error(f"Skill execution failed: {result.stderr or 'Unknown error'}")
                return SkillExecutionResult(
                    skill_name=skill_name,
                    success=False,
                    error=result.stderr or "Script execution failed",
                    execution_time=execution_time,
                )

        finally:
            # Clean up temp file
            try:
                Path(input_file).unlink()
            except:
                pass

    except subprocess.TimeoutExpired:
        return SkillExecutionResult(
            skill_name=skill_name,
            success=False,
            error="Skill execution timed out",
        )
    except Exception as e:
        logger.debug(f"File skill execution error: {e}")
        return None


def _load_skill_knowledge(skill_name: str) -> str:
    """
    Load professional knowledge from SKILL.md for use as LLM context.

    Extracts the relevant sections (excluding execution steps and bash commands)
    to provide the LLM with domain expertise.

    Args:
        skill_name: Name of the skill directory

    Returns:
        Extracted knowledge as markdown string, or empty string if not found
    """
    try:
        from pathlib import Path

        skill_md_path = Path("skills") / skill_name / "SKILL.md"
        if not skill_md_path.exists():
            logger.debug(f"SKILL.md not found for {skill_name}")
            return ""

        content = skill_md_path.read_text(encoding='utf-8')

        # Extract sections we want to include in system prompt
        # We want: description, core functions, risk factors, interventions
        # We exclude: quick start (bash commands), operation steps, input modes with code examples

        import re

        # Remove YAML frontmatter
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

        # Remove code blocks (bash commands, JSON examples)
        content = re.sub(r'```bash\n.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'```json\n.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'```\n.*?```', '', content, flags=re.DOTALL)

        # Remove Quick Start section
        content = re.sub(r'## Quick Start.*?(?=##\s)', '', content, flags=re.DOTALL)

        # Remove 操作步骤 section (execution steps)
        content = re.sub(r'## 操作步骤.*?(?=##\s|$)', '', content, flags=re.DOTALL)

        # Remove 资源索引 section if exists
        content = re.sub(r'## 资源索引.*?$', '', content, flags=re.DOTALL)

        # Clean up extra whitespace
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:  # Skip empty lines
                cleaned_lines.append(stripped)

        knowledge = '\n'.join(cleaned_lines)

        # Add a header
        if knowledge:
            knowledge = f"""## 专业知识参考：{skill_name}

以下是该技能的专业知识和评估标准，请在回答时参考这些内容：

{knowledge}

---
"""

        return knowledge

    except Exception as e:
        logger.warning(f"Failed to load SKILL.md for {skill_name}: {e}")
        return ""


async def _generate_llm_response(
    user_input: str,
    patient_id: str,
    conversation_memory: Optional[ConversationMemory] = None,
    patient_context: Optional[PatientContext] = None,
    matched_skill: Optional[str] = None,
) -> str:
    """
    Generate a response using the configured LLM with Markdown formatting.

    Args:
        user_input: User's input message
        patient_id: Patient identifier
        conversation_memory: Optional conversation memory for context
        patient_context: Optional patient context with retrieved data
        matched_skill: Optional name of matched skill (for context)

    Returns:
        Generated response string (Markdown formatted)
    """
    try:
        from src.config.settings import get_settings
        import anthropic

        settings = get_settings()

        if not settings.anthropic_api_key:
            # Fallback to simple response when no API key
            return _get_fallback_response(user_input, patient_id, conversation_memory, patient_context)

        # Load skill knowledge if a skill was matched
        skill_knowledge = ""
        if matched_skill:
            skill_knowledge = _load_skill_knowledge(matched_skill)
            if skill_knowledge:
                logger.info(f"Loaded skill knowledge for: {matched_skill}")

        # Build conversation context
        messages = [{"role": "user", "content": user_input}]

        # Build patient context section for system prompt
        patient_context_section = ""
        if patient_context:
            context_parts = []
            if patient_context.basic_info:
                context_parts.append("### 患者基本信息")
                for key, value in patient_context.basic_info.items():
                    context_parts.append(f"- {key}: {value}")
            if patient_context.vital_signs:
                context_parts.append("### 健康指标数据")
                for key, value in patient_context.vital_signs.items():
                    context_parts.append(f"- {key}: {value}")
            if patient_context.medical_history:
                context_parts.append("### 病史记录")
                for key, value in patient_context.medical_history.items():
                    if value:
                        context_parts.append(f"- {key}: {value}")
            if context_parts:
                patient_context_section = "\n\n## 患者健康档案数据（系统已获取，请直接使用）\n\n" + "\n".join(context_parts)
                logger.info(f"Included patient context in LLM prompt: basic_info={bool(patient_context.basic_info)}, vital_signs={len(patient_context.vital_signs)} fields")

        # Build conversation context summary for the system prompt
        conversation_context = ""
        if conversation_memory and conversation_memory.messages:
            recent_messages = conversation_memory.messages[-15:]  # Last 15 messages
            context_summary = _build_conversation_summary(recent_messages)
            if context_summary:
                conversation_context = f"\n\n## 对话历史摘要\n\n{context_summary}"

        # Add conversation history for context
        if conversation_memory and conversation_memory.messages:
            history_messages = []
            for mem in conversation_memory.messages[-8:]:  # Last 8 messages for context
                role = mem.get("metadata", {}).get("role", "user")
                content = mem.get("memory", "")
                if role and content:
                    history_messages.append({"role": role, "content": content})

            messages = history_messages + messages

        # Create Anthropic client
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url if settings.anthropic_base_url != "https://api.anthropic.com" else None,
        )

        # System prompt for medical assistant with Markdown instructions
        from src.domain.shared.services.system_prompt_service import get_system_prompt_service
        prompt_service = get_system_prompt_service()
        system_prompt = await prompt_service.get_prompt_with_fallback(
            "medical_assistant_nodes",
            fallback=f"""你是一个专业的健康管理助手，帮助用户进行健康评估、风险预测和健康管理。

{{skill_knowledge}}
你的职责：
1. 回答用户的健康相关问题
2. **记住用户之前提供的信息**（姓名、年龄、症状、指标等）
3. **如果用户已经提供过基本信息，直接使用这些信息进行分析，不要再询问**
4. 提供个性化的健康建议
5. 在需要时建议用户咨询专业医生
6. 保持专业、友善的语气{{conversation_context}}

**重要：请使用 Markdown 格式组织你的回答**

回答格式建议：
- 使用 ## 标题组织内容
- 使用 - 列表列出要点
- 使用 **粗体** 强调重要信息
- 使用 > 引用块给出提醒
- 使用 ``` 代码块展示具体数据（如有）

**关于用户数据来源的优先级**：
- 系统自动从平安健康档案API获取的数据是**最权威的**，必须优先使用
- 当系统在上下文中提供了用户健康数据时，说明数据已经成功获取，**不应再当作新用户处理**
- 即使对话历史中出现过"客户号不匹配"或"新用户"的讨论，只要当前上下文中包含了用户的健康数据，就应以这些数据为准
- 不要因为对话历史中的旧信息而质疑或忽略系统提供的用户数据

请注意：
- 你不能替代专业医生的诊断
- 对于紧急医疗情况，建议用户立即就医
- 保持回答简洁明了但全面""",
        )
        # Format template variables
        try:
            system_prompt = system_prompt.format(
                skill_knowledge=skill_knowledge,
                conversation_context=conversation_context,
            )
        except (KeyError, IndexError):
            pass

        # Append patient context data to system prompt
        if patient_context_section:
            system_prompt += patient_context_section

        # Generate response
        response = client.messages.create(
            model=settings.model,
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
        )

        # Extract response text
        response_text = response.content[0].text
        logger.info(f"LLM response generated for patient {patient_id}")
        return response_text

    except Exception as e:
        logger.error(f"Failed to generate LLM response: {e}")
        return _get_fallback_response(user_input, patient_id, conversation_memory, patient_context)


def _build_conversation_summary(messages: List[Dict[str, Any]]) -> str:
    """Build a summary of conversation history focusing on key information."""
    summary_parts = []

    # Extract user information from messages
    user_info = []
    for msg in messages:
        role = msg.get("metadata", {}).get("role", "")
        content = msg.get("memory", "")
        if role == "user":
            user_info.append(f"- {content}")

    if user_info:
        summary_parts.append("### 用户之前提供的信息：\n" + "\n".join(user_info[:10]))

    return "\n".join(summary_parts)


def _get_fallback_response(user_input: str, patient_id: str, conversation_memory: Optional[ConversationMemory] = None, patient_context: Optional[PatientContext] = None) -> str:
    """Generate a fallback response when LLM is not available (with Markdown formatting)."""

    # Try to use conversation context
    context_info = ""
    if conversation_memory and conversation_memory.messages:
        recent_user_messages = [
            m.get("memory", "") for m in conversation_memory.messages[-5:]
            if m.get("metadata", {}).get("role") == "user"
        ]
        if recent_user_messages:
            context_info = "\n\n### 之前的对话记录\n\n" + "\n".join([f"- {msg}" for msg in recent_user_messages])

    return f"""## 健康评估

您的问题是：**{user_input}**{context_info}

### 初步分析

作为健康管理助手，我已收到您的问题。

> ⚠️ **重要提醒**：我是一个 AI 助手，不能替代专业医生的诊断。如果症状严重或持续，请及时就医。

### 建议

- 如果症状严重或持续，请咨询专业医生
- 如有紧急情况，请拨打急救电话 120
- 休息并观察症状变化

---

您的健康问题已被记录，我们可以继续对话以获取更多信息。"""


async def aggregate_results_node(state: AgentState) -> AgentState:
    """
    Aggregate results from all executed skills.

    Args:
        state: Current agent state

    Returns:
        Updated agent state with aggregated results
    """
    logger.info("Aggregating results")
    state.status = AgentStatus.AGGREGATING_RESULTS
    state.current_step = "aggregate_results"

    try:
        # Handle multi-skill execution results first
        if state.multi_skill_result:
            logger.info("Processing multi-skill execution result")
            multi_skill = state.multi_skill_result

            # Extract pre-aggregated response from multi-skill execution
            aggregated_response = multi_skill.get("aggregated_response", "")
            structured_output = multi_skill.get("structured_output")

            # Check for success flag (default to True if not present but we have results)
            is_successful = multi_skill.get("success", True)
            has_results = bool(aggregated_response or structured_output)

            if is_successful and has_results:
                # Set final response from aggregated response
                if aggregated_response:
                    state.final_response = aggregated_response
                    logger.info("Set final_response from multi_skill_result.aggregated_response")

                # Set structured output if available
                if structured_output:
                    state.structured_output = structured_output
                    logger.info("Set structured_output from multi_skill_result.structured_output")

                # Clear error message on successful multi-skill execution
                state.error_message = None
                logger.info("Multi-skill execution succeeded, cleared error_message")

            # Handle partial success cases (some skills failed, but we have results)
            errors = multi_skill.get("errors", [])
            if errors and has_results:
                logger.warning(f"Multi-skill had partial success with {len(errors)} errors: {errors}")
                # Append error summary to the response if partial success
                if aggregated_response:
                    error_summary = f"\n\n---\n> **注意**: 部分技能执行失败 ({len(errors)}个错误)，以上结果基于成功执行的技能。"
                    state.final_response = aggregated_response + error_summary
                # Still keep the structured output for successful skills

            # Handle complete failure (no results, only errors)
            elif errors and not has_results:
                state.error_message = f"Multi-skill execution failed: {errors}"
                logger.error(f"Multi-skill execution failed with errors: {errors}")
                return state

            logger.info(f"Multi-skill result processed: success={is_successful}, has_results={has_results}")
            return state

        # If final_response was already generated by LLM fallback, use it
        if state.final_response:
            logger.info("Using LLM-generated response")
            # Still create structured output for consistency
            state.structured_output = {
                "patient_id": state.patient_id,
                "timestamp": datetime.now().isoformat(),
                "intent": state.intent.value if state.intent else None,
                "response_type": "llm_generated",
                "confidence": state.confidence,
            }
            return state

        # Check if any skill returned incomplete status
        for skill_result in state.executed_skills:
            logger.info(f"Aggregating skill result: {skill_result.skill_name}, success={skill_result.success}")
            if skill_result.success and skill_result.result_data:
                # Handle both direct status and wrapped data status
                result_content = skill_result.result_data
                if isinstance(result_content, dict):
                    # Check if data is wrapped in a "data" field (file-based skill format)
                    data = result_content.get("data", result_content)
                    if data.get("status") == "incomplete":
                        logger.info(f"Skill {skill_result.skill_name} returned incomplete status")
                        required_fields = data.get("required_fields", [])
                        message = data.get("message", "需要补充健康数据")
                        state.final_response = _format_incomplete_data_response(message, required_fields)
                        return state

        # Gather all results
        all_results = state.get_all_results()

        # Check for file-based skill modules
        for skill_result in state.executed_skills:
            if skill_result.success and skill_result.result_data:
                result_content = skill_result.result_data

                # Extract modules data from result_content and store in health_assessment
                modules_data = None
                if "modules" in result_content:
                    modules_data = {"modules": result_content["modules"]}
                elif "final_output" in result_content and isinstance(result_content["final_output"], dict):
                    final_output = result_content["final_output"]
                    if "modules" in final_output:
                        modules_data = {"modules": final_output["modules"]}
                    elif "data" in final_output and isinstance(final_output["data"], dict):
                        final_data = final_output["data"]
                        if "modules" in final_data:
                            modules_data = {"modules": final_data["modules"]}

                if modules_data and state.intent == IntentType.HEALTH_ASSESSMENT:
                    # Update health_assessment with extracted modules
                    state.health_assessment = modules_data
                if isinstance(result_content, dict):
                    # First try to get data from "data" field (wrapper format)
                    data = result_content.get("data", result_content)

                    # Check if skill returned modules (complete assessment)
                    modules_source = None
                    if "modules" in data and isinstance(data, dict):
                        modules_source = data
                    elif "modules" in result_content:
                        modules_source = result_content
                    elif "final_output" in result_content and isinstance(result_content["final_output"], dict):
                        final_output = result_content["final_output"]
                        if "modules" in final_output:
                            modules_source = final_output
                        elif "data" in final_output and isinstance(final_output["data"], dict):
                            final_data = final_output["data"]
                            if "modules" in final_data:
                                modules_source = final_data

                    if modules_source is not None:
                        logger.info(f"Formatting complete assessment from skill {skill_result.skill_name}")
                        modules = modules_source.get("modules", {})

                        # Check if modules contain dict content (new format like cvd-risk-assessment)
                        # If so, skip processing here and let _format_modules_response handle it later
                        has_dict_content = any(isinstance(v, dict) for v in modules.values())
                        if has_dict_content:
                            logger.info(f"Modules contain dict content, delegating to _format_modules_response")
                            # Don't set final_response here, let it fall through to _format_assessment_response
                            continue

                        # Process string-based modules
                        health_score = modules_source.get("health_score", "N/A")
                        risk_grade = modules_source.get("risk_grade", "N/A")

                        # Build response from modules
                        module_sections = []
                        for section_name, section_content in modules.items():
                            # Skip empty sections
                            if not section_content or not section_content.strip():
                                continue
                            # For 'header' section, add content directly (it has its own title)
                            # For other sections, check if content already has a heading (starts with #)
                            if section_name == 'header':
                                module_sections.append(f"\n{section_content}")
                            elif section_content.strip().startswith('#'):
                                # Content already has a heading, use as-is
                                module_sections.append(f"\n{section_content}")
                            else:
                                # Add section name as heading
                                module_sections.append(f"\n## {section_name}\n\n{section_content}")

                        # Add header with retrieved data info (generic)
                        response_parts = []
                        if state.patient_context:
                            info_summary = _build_patient_info_summary(state.patient_context)
                            if info_summary:
                                response_parts.append(info_summary)

                        response_parts.append("\n".join(module_sections))
                        state.final_response = "".join(response_parts)

                        # Update structured output with modules
                        state.structured_output = {
                            "patient_id": state.patient_id,
                            "timestamp": datetime.now().isoformat(),
                            "intent": state.intent.value if state.intent else None,
                            "health_score": health_score,
                            "risk_grade": risk_grade,
                            "modules": modules,
                            "total_modules": data.get("total_modules", len(modules)),
                        }
                        return state

        # Create structured output
        state.structured_output = {
            "patient_id": state.patient_id,
            "timestamp": datetime.now().isoformat(),
            "intent": state.intent.value if state.intent else None,
            "results": {k: v for k, v in all_results.items() if v is not None},
        }

        # Generate final response from skill results
        if state.health_assessment:
            logger.info(f"Formatting health assessment response")
            state.final_response = _format_assessment_response(
                state.health_assessment,
                state.patient_context
            )
        elif state.risk_prediction:
            state.final_response = _format_risk_response(state.risk_prediction)
        elif state.health_plan:
            state.final_response = _format_plan_response(state.health_plan)
        elif state.triage_recommendation:
            state.final_response = _format_triage_response(state.triage_recommendation)
        elif state.medication_recommendation:
            state.final_response = _format_medication_response(state.medication_recommendation)
        elif state.service_recommendation:
            state.final_response = _format_service_response(state.service_recommendation)
        else:
            state.final_response = "I've processed your request. Is there anything specific you'd like to know?"

        logger.info("Results aggregated successfully")

    except Exception as e:
        logger.error(f"Failed to aggregate results: {e}")
        state.error_message = f"Failed to aggregate results: {str(e)}"

    return state


def _format_incomplete_data_response(message: str, required_fields: list) -> str:
    """
    Format a user-friendly prompt for missing vital signs data.

    Args:
        message: Message from the skill about missing data
        required_fields: List of required field names

    Returns:
        Formatted response prompting user for data
    """
    # Map field names to user-friendly descriptions
    field_descriptions = {
        "systolic_bp": "收缩压 (高压)",
        "diastolic_bp": "舒张压 (低压)",
        "fasting_glucose": "空腹血糖",
        "postprandial_glucose": "餐后血糖",
        "total_cholesterol": "总胆固醇",
        "ldl_c": "低密度脂蛋白 (LDL-C)",
        "hdl_c": "高密度脂蛋白 (HDL-C)",
        "tg": "甘油三酯",
        "uric_acid": "尿酸",
        "bmi": "BMI或身高体重数据",
        "height": "身高",
        "weight": "体重",
        "waist": "腰围"
    }

    # Create formatted list of required fields
    required_items = []
    for field in required_fields:
        desc = field_descriptions.get(field, field)
        required_items.append(f"- **{desc}**")

    required_list = "\n".join(required_items) if required_items else ""

    return f"""## 需要补充健康数据

{message}

为了给您进行准确的健康评估，请提供以下健康指标：

{required_list}

### 如何提供数据

请按以下格式提供您的数据：

**血压**: 例如 \"血压120/80\"
**血糖**: 例如 \"空腹血糖5.6\"
**血脂**: 例如 \"总胆固醇5.2，甘油三酯1.5\"
**BMI**: 例如 \"身高175cm，体重70kg\" 或 \"BMI23\"
**尿酸**: 例如 \"尿酸380\"

### 示例

您可以这样说：
- \"我最近检查的血压是130/85\"
- \"我的空腹血糖是6.1mmol/L，餐后是8.2mmol/L\"
- \"我的总胆固醇是5.5，低密度脂蛋白是3.2\"

或者一次性提供：
\"身高170cm，体重65kg，血压125/82，空腹血糖5.5，总胆固醇5.0，尿酸350\"

---

> 💡 **提示**: 这些数据可以从您的体检报告或医院检查单中获得。如果不确定具体数值，也可以提供大致范围，我会尽量帮您评估。"""



def _format_triage_response(triage: Dict[str, Any]) -> str:
    """Format triage recommendation result as natural language."""
    response = f"## 分诊导医建议\n\n"

    if "recommended_department" in triage:
        response += f"**推荐科室**: {triage['recommended_department']}\n\n"

    if "recommended_doctor" in triage:
        response += f"**推荐医生**: {triage['recommended_doctor']}\n\n"

    if "recommended_hospital" in triage:
        response += f"**推荐医院**: {triage['recommended_hospital']}\n\n"

    if "urgency" in triage:
        response += f"**紧急程度**: {triage['urgency']}\n\n"

    if "reasoning" in triage:
        response += f"### 建议\n{triage['reasoning']}\n"

    return response


def _format_medication_response(medication: Dict[str, Any]) -> str:
    """Format medication check result as natural language."""
    response = f"## 用药检查结果\n\n"

    if "adaptation_check" in medication:
        response += f"**适应症检查**: {medication['adaptation_check']}\n\n"

    if "dosage_check" in medication:
        response += f"**用量检查**: {medication['dosage_check']}\n\n"

    if "recommendations" in medication:
        response += "### 建议\n"
        for rec in medication['recommendations']:
            response += f"- {rec}\n"

    return response


def _format_service_response(service: Dict[str, Any]) -> str:
    """Format service recommendation result as natural language."""
    response = f"## 服务推荐\n\n"

    if "insurance_products" in service:
        response += "### 推荐保险产品\n"
        for product in service['insurance_products']:
            response += f"- **{product.get('name', '未知')}**: {product.get('description', '')}\n"
        response += "\n"

    if "health_services" in service:
        response += "### 推荐健康服务\n"
        for svc in service['health_services']:
            response += f"- **{svc.get('name', '未知')}**: {svc.get('description', '')}\n"
        response += "\n"

    return response


async def save_memory_node(state: AgentState) -> AgentState:
    """
    Save conversation to memory using Mem0.

    Includes skill metadata (intent, suggested_skill, confidence) for analysis.

    Args:
        state: Current agent state

    Returns:
        Updated agent state
    """
    logger.info("Saving conversation to memory")
    state.status = AgentStatus.SAVING_MEMORY
    state.current_step = "save_memory"

    # Debug: Print full state
    logger.info(f"Saving memory: intent={state.intent}, skill={state.suggested_skill}, confidence={state.confidence}")

    try:
        from src.infrastructure.memory import MemoryStore

        memory_store = MemoryStore()

        # Use session_id from state (set by API layer with consultation_id)
        # Fall back to generating a new one only if not provided
        import uuid
        session_id = state.session_id or f"session_{uuid.uuid4().hex[:12]}"

        # Prepare skill metadata for user message
        user_metadata = {
            "role": "user",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "patient_id": state.patient_id,
        }

        # Save user message
        await memory_store.add(
            user_id=state.patient_id,
            message=state.user_input,
            metadata=user_metadata,
        )

        # Save assistant response with full skill metadata
        if state.final_response:
            # Debug logging
            logger.info(
                f"save_memory_node: state.intent={state.intent}, "
                f"type={type(state.intent)}, "
                f"suggested_skill={state.suggested_skill}, "
                f"confidence={state.confidence}"
            )

            assistant_metadata = {
                "role": "assistant",
                "saved_by": "medical_agent_save_memory_node",
                "test_save_node_called": True,  # Marker to verify save_memory_node was called
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "patient_id": state.patient_id,
                # Skill classification metadata
                "intent": state.intent.value if hasattr(state.intent, 'value') else str(state.intent) if state.intent else None,
                "suggested_skill": state.suggested_skill,
                "confidence": state.confidence,
                # Additional execution info
                "executed_skills": [
                    {
                        "skill_name": s.skill_name,
                        "success": s.success,
                        "execution_time": s.execution_time,
                    }
                    for s in state.executed_skills
                ] if state.executed_skills else [],
                # Structured output
                "structured_output": state.structured_output,
                # Error if any
                "error_message": state.error_message,
            }

            await memory_store.add(
                user_id=state.patient_id,
                message=state.final_response,
                metadata=assistant_metadata,
            )

        logger.info(
            f"Conversation saved to memory with skill metadata: "
            f"intent={state.intent.value if state.intent else None}, "
            f"skill={state.suggested_skill}, "
            f"confidence={state.confidence}"
        )

    except Exception as e:
        logger.error(f"Failed to save memory: {e}")
        # Memory save failure is not critical

    # Mark as completed
    state.status = AgentStatus.COMPLETED
    state.end_time = datetime.now()

    return state


def _format_value(value: Any, indent: int = 0) -> str:
    """Recursively format a value into readable markdown."""
    prefix = "  " * indent
    if value is None or value == "N/A":
        return ""
    if isinstance(value, str):
        return f"{prefix}{value}\n"
    if isinstance(value, (int, float)):
        return f"{prefix}{value}\n"
    if isinstance(value, bool):
        return f"{prefix}{'是' if value else '否'}\n"
    if isinstance(value, list):
        lines = ""
        for item in value:
            if isinstance(item, str):
                lines += f"{prefix}- {item}\n"
            elif isinstance(item, dict):
                lines += f"{prefix}- {_format_value(item, 0).strip()}\n"
            else:
                lines += f"{prefix}- {item}\n"
        return lines
    if isinstance(value, dict):
        lines = ""
        for k, v in value.items():
            if v is None or v == "N/A" or v == "":
                continue
            if isinstance(v, (str, int, float, bool)):
                lines += f"{prefix}- **{k}**: {v}\n"
            elif isinstance(v, list):
                lines += f"{prefix}- **{k}**: {', '.join(str(i) for i in v)}\n"
            elif isinstance(v, dict):
                lines += f"{prefix}- **{k}**:\n{_format_value(v, indent + 1)}"
        return lines
    return f"{prefix}{value}\n"


def _load_field_labels() -> dict:
    """Load field label config from config/field_labels.yaml (once, cached in module)."""
    try:
        from pathlib import Path
        import yaml
        config_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "field_labels.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load field_labels.yaml: {e}, using defaults")
    # Minimal fallback defaults
    return {
        "basic_info": {"age": "年龄", "gender": "性别", "party_id": "客户号"},
        "vital_signs": {"systolic_bp": "收缩压", "diastolic_bp": "舒张压", "bmi": "BMI"},
        "medical_history": {"disease_labels": "疾病", "diagnoses": "病史", "sport_records": "运动记录"},
        "suffixes": {"age": "岁"},
        "skip_fields": ["source", "patient_id", "indicators"],
    }


# Module-level cache — loaded once
_field_labels_config = _load_field_labels_config = None


def _get_field_labels() -> dict:
    """Return cached field labels config (lazy singleton)."""
    global _field_labels_config
    if _field_labels_config is None:
        _field_labels_config = _load_field_labels()
    return _field_labels_config


def _build_patient_info_summary(patient_context) -> str:
    """Build a summary of all available patient context data.

    Generic renderer — discovers all fields in basic_info, vital_signs,
    and medical_history automatically. Label mappings are loaded from
    config/field_labels.yaml — no code changes needed to add new fields.
    Returns empty string if nothing worth showing.
    """
    basic_info = patient_context.basic_info or {}
    is_from_api = basic_info.get("source") == "ping_an_api"
    if not is_from_api:
        return ""

    cfg = _get_field_labels()
    # Merge all section labels into one lookup table
    all_labels = {}
    for section in ("basic_info", "vital_signs", "medical_history"):
        all_labels.update(cfg.get(section, {}))
    suffixes = cfg.get("suffixes", {})
    skip = set(cfg.get("skip_fields", ["source", "patient_id", "indicators"]))

    lines = ["> **已从平安健康档案系统获取您的健康数据**\n"]
    info_items = []

    # --- basic_info ---
    for k, v in basic_info.items():
        if k in skip or v is None or v == "":
            continue
        label = all_labels.get(k, k)
        suffix = suffixes.get(k, "")
        info_items.append(f"- {label}: {v}{suffix}")

    # --- vital_signs ---
    vital_signs = patient_context.vital_signs or {}
    for k, v in vital_signs.items():
        if k in skip or k.startswith("_") or v is None or v == "":
            continue
        label = all_labels.get(k, k)
        info_items.append(f"- {label}: {v}")

    # --- medical_history ---
    medical_history = patient_context.medical_history or {}
    for k, v in medical_history.items():
        if k in skip or v is None or v == "" or v == []:
            continue
        label = all_labels.get(k, k)
        if k == "disease_labels" and isinstance(v, list):
            info_items.append(f"- {label}: {', '.join(str(i) for i in v)}")
        elif k == "diagnoses" and isinstance(v, list):
            codes = [d.get("code", "") for d in v if isinstance(d, dict) and d.get("code")]
            if codes:
                info_items.append(f"- {label}: {', '.join(codes)}")
        elif k == "sport_records" and isinstance(v, (dict, list)):
            info_items.append(f"- {label}: 已获取")
        elif isinstance(v, (str, int, float)):
            info_items.append(f"- {label}: {v}")
        elif isinstance(v, list):
            info_items.append(f"- {label}: {', '.join(str(i) for i in v)}")

    if not info_items:
        return ""

    lines.append("**已获取的信息**:")
    lines.extend(info_items)
    return "\n".join(lines) + "\n"


def _format_modules_response(assessment: Dict[str, Any], patient_context: Optional[PatientContext] = None) -> str:
    """Format modules-based assessment result into user-readable markdown.

    Supports any skill that returns modules with the following value types:
    - str: pre-formatted markdown — output directly
    - dict: structured data (e.g. cvd-risk-assessment) — rendered via _format_value
    - list: bullet-point items — rendered via _format_value
    """
    import logging
    logger = logging.getLogger(__name__)

    modules = assessment.get("modules", {})
    if not isinstance(modules, dict):
        return str(modules) if modules else ""
    logger.info(f"[_format_modules_response] modules keys: {list(modules.keys())}")

    response = ""

    # Add header with retrieved data info (generic — auto-discovers all available fields)
    if patient_context:
        info_lines = _build_patient_info_summary(patient_context)
        if info_lines:
            response += info_lines + "\n"

    # Process all modules in original order
    for section_name, section_content in modules.items():
        if not section_content:
            continue

        # String — already formatted markdown, output directly
        if isinstance(section_content, str):
            response += section_content + "\n\n"
        else:
            # Structured data (dict/list) — generic recursive formatting
            formatted = _format_value(section_content)
            if formatted.strip():
                response += formatted + "\n"

    return response


def _format_assessment_response(assessment: Dict[str, Any], patient_context: Optional[PatientContext] = None) -> str:
    """Format health assessment result as natural language."""
    logger = logging.getLogger(__name__)
    print(f"[_format_assessment_response ENTRY] assessment type: {type(assessment).__name__}", flush=True)
    # Debug: use logger to ensure visibility
    logger.info(f"[_format_assessment_response] assessment type: {type(assessment).__name__}")
    logger.info(f"[_format_assessment_response] assessment keys: {list(assessment.keys()) if isinstance(assessment, dict) else 'not a dict'}")
    if isinstance(assessment, dict) and "modules" in assessment:
        print(f"[_format_assessment_response] modules in assessment: {list(assessment['modules'].keys())}", flush=True)
        logger.info(f"[_format_assessment_response] modules in assessment")
        for k, v in assessment["modules"].items():
            print(f"[_format_assessment_response]   module '{k}': {list(v.keys()) if isinstance(v, dict) else type(v).__name__}", flush=True)
            logger.info(f"[_format_assessment_response]   module '{k}': {list(v.keys()) if isinstance(v, dict) else type(v).__name__}")

    # Handle modules format (from cvd-risk-assessment and other skills)
    if "modules" in assessment:
        print(f"[_format_assessment_response] Found modules, calling _format_modules_response", flush=True)
        logger.info("[_format_assessment_response] Found modules, calling _format_modules_response")
        return _format_modules_response(assessment, patient_context)

    # Handle both direct status and wrapped data status
    # Check if assessment returned incomplete status
    assessment_data = assessment.get("data", assessment)
    if assessment_data.get("status") == "incomplete":
        required_fields = assessment_data.get("required_fields", [])
        message = assessment_data.get("message", "需要补充健康数据")
        return _format_incomplete_data_response(message, required_fields)

    status = assessment.get("health_status", {})
    overall = status.get("overall", "未知")

    response = f"## 健康评估结果\n\n"

    # Check if data was retrieved from Ping An API
    if patient_context:
        info_summary = _build_patient_info_summary(patient_context)
        if info_summary:
            response += info_summary + "\n"

    response += f"**整体健康状况**: {overall}\n\n"

    if "indicators" in status:
        response += "### 主要指标分析\n"
        for indicator, data in status["indicators"].items():
            response += f"- **{indicator}**: {data.get('value', 'N/A')} ({data.get('status', '未知')})\n"

    if "recommendations" in status:
        response += "\n### 建议\n"
        for rec in status["recommendations"]:
            response += f"- {rec}\n"

    return response


def _format_risk_response(risk: Dict[str, Any]) -> str:
    """Format risk prediction result as natural language."""
    predictions = risk.get("risk_predictions", {})

    response = f"## 风险预测结果\n\n"

    if "overall_risk" in predictions:
        overall = predictions["overall_risk"]
        response += f"**整体风险等级**: {overall.get('level', '未知')} ({overall.get('score', 0)}%)\n\n"

    if "disease_risks" in predictions:
        response += "### 疾病风险\n"
        for disease, data in predictions["disease_risks"].items():
            response += f"- **{disease}**: {data.get('probability', 0)}% 风险\n"

    if "recommendations" in predictions:
        response += "\n### 风险管理建议\n"
        for rec in predictions["recommendations"]:
            response += f"- {rec}\n"

    return response


def _format_plan_response(plan: Dict[str, Any]) -> str:
    """Format health plan result as natural language."""
    response = f"## 健康管理方案\n\n"

    if "prescriptions" in plan:
        response += "### 处方建议\n"
        for prescription in plan["prescriptions"]:
            ptype = prescription.get("type", "未知")
            response += f"\n#### {ptype}\n"
            if "details" in prescription:
                for key, value in prescription["details"].items():
                    response += f"- {key}: {value}\n"

    if "goals" in plan:
        response += "\n### 目标\n"
        for goal in plan["goals"]:
            response += f"- {goal}\n"

    return response
