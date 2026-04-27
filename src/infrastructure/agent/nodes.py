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

from .state import (
    AgentState,
    AgentStatus,
    IntentType,
    SkillExecutionResult,
    PatientContext,
    ConversationMemory,
)

logger = logging.getLogger(__name__)


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

    # Mapping from Ping An indicator names to skill field names
    indicator_name_mapping = {
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
        "身高": "height",
        "体重": "weight",
        "腰围": "waist",
    }

    for item in indicator_items:
        indicator_name = item.get("indicatorName", "")
        indicator_value = item.get("indicatorValue")
        indicator_unit = item.get("indicatorUnit", "")

        # Skip if no value
        if indicator_value is None or indicator_value == "":
            continue

        # Find matching field name
        field_name = None
        for ping_an_name, skill_name in indicator_name_mapping.items():
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

    # Calculate BMI if height and weight are available
    if "height" in vital_signs and "weight" in vital_signs:
        try:
            height_m = vital_signs["height"] / 100  # Convert cm to m
            weight = vital_signs["weight"]
            bmi = weight / (height_m * height_m) if height_m > 0 else 0
            vital_signs["bmi"] = round(bmi, 1)
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    # Store original indicators for reference
    vital_signs["indicators"] = indicator_items

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

    # Calculate BMI if height and weight are available
    if 'height' in vital_signs and 'weight' in vital_signs:
        try:
            height_m = vital_signs['height'] / 100  # Convert cm to m
            weight = vital_signs['weight']
            bmi = weight / (height_m * height_m) if height_m > 0 else 0
            vital_signs['bmi'] = round(bmi, 1)
            logger.info(f"Calculated BMI: {vital_signs['bmi']}")
        except (KeyError, TypeError, ZeroDivisionError):
            pass

    if extracted_count > 0:
        logger.info(f"Extracted {extracted_count} vital signs from user input")

    return vital_signs


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

    # Debug: Check if ping_an_health_data and previous_patient_context are present
    logger.info(f"DEBUG load_patient_node: ping_an_health_data={state.ping_an_health_data is not None}, party_id={state.party_id}, previous_patient_context={state.previous_patient_context is not None}")

    patient_data = {}
    vital_signs = {}
    medical_records = {}

    # If previous_patient_context exists, start with that data
    if state.previous_patient_context:
        logger.info("Using previous patient context as base")
        logger.info(f"DEBUG: previous_patient_context keys: {list(state.previous_patient_context.keys())}")
        patient_data = state.previous_patient_context.get("basic_info", {}).copy()
        vital_signs = state.previous_patient_context.get("vital_signs", {}).copy()
        medical_records = state.previous_patient_context.get("medical_history", {}).copy()
        logger.info(f"DEBUG: Loaded from previous context - vital_signs keys: {list(vital_signs.keys())}, medical_records keys: {list(medical_records.keys())}")

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

        # Map diseaseHistory to diagnoses
        diagnoses = []
        if "diseaseHistory" in api_data:
            diagnoses = [{"code": code} for code in api_data["diseaseHistory"]]

        # Map indicatorItems to vital_signs (flatten to skill-expected format)
        vital_signs = _map_ping_an_indicators_to_vital_signs(api_data.get("indicatorItems", []))

        # Add sport records
        medical_records = {
            "diagnoses": diagnoses,
            "medications": api_data.get("medications", []),
            "allergies": api_data.get("allergies", []),
            "chronic_diseases": diagnoses,
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
        logger.info(f"  - Age: {api_data.get('age', 'N/A')}")
        logger.info(f"  - Diagnoses: {len(diagnoses)} conditions")
        logger.info(f"  - Has sport records: {bool(api_data.get('sportRecords'))}")

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

                        # Map indicatorItems to vital_signs (flatten to skill-expected format)
                        vital_signs = _map_ping_an_indicators_to_vital_signs(api_data.get("indicatorItems", []))

                        # Add sport records to medical history
                        medical_records = {
                            "diagnoses": diagnoses,
                            "medications": api_data.get("medications", []),
                            "allergies": api_data.get("allergies", []),
                            "chronic_diseases": diagnoses,
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
    logger.info(f"DEBUG: Before extraction - vital_signs has {len(vital_signs)} keys: {list(vital_signs.keys())[:5]}")
    vital_signs = _extract_vital_signs_from_user_input(state.user_input, vital_signs)
    logger.info(f"DEBUG: After extraction - vital_signs has {len(vital_signs)} keys: {list(vital_signs.keys())}")

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

        # Get conversation history
        memories = await memory_store.get_all(state.patient_id)

        # Build context summary from memories
        for mem in memories[-20:]:  # Last 20 messages
            role = mem.get("metadata", {}).get("role", "unknown")
            content = mem.get("memory", "")
            if content:
                context_parts.append(f"{role}: {content}")

        # Extract user profile information from previous conversations
        user_profile = _extract_user_profile(memories)

        # Create conversation memory
        state.conversation_memory = ConversationMemory(
            conversation_id=state.patient_id,
            messages=memories,
            context_summary="\n".join(context_parts) if context_parts else None,
            previous_assessments=[],  # Could be populated from structured outputs
        )

        # Store user profile in patient context for later use
        if state.patient_context:
            if user_profile:
                state.patient_context.basic_info.update(user_profile)
            # Update basic info with patient_id if not set
            if not state.patient_context.basic_info:
                state.patient_context.basic_info["patient_id"] = state.patient_id

        logger.info(f"Retrieved {len(memories)} memories")
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


async def classify_intent_node(state: AgentState) -> AgentState:
    """
    Classify user intent and suggest appropriate skill using model-based matching.

    This node uses LLM-powered skill discovery instead of keyword matching,
    enabling more flexible and intelligent intent classification.

    Args:
        state: Current agent state

    Returns:
        Updated agent state with classified intent
    """
    logger.info(f"Classifying intent for input: {state.user_input[:50]}...")
    state.status = AgentStatus.CLASSIFYING_INTENT
    state.current_step = "classify_intent"

    try:
        # Import model-based skill matcher
        from .skill_matcher import match_skill_with_llm, get_available_skills

        # Get available skills (auto-discovered from skills directory)
        available_skills = await get_available_skills()
        logger.debug(f"Available skills for matching: {list(available_skills.keys())}")

        # Use LLM to match user query to appropriate skill
        match_result = await match_skill_with_llm(state.user_input, available_skills)

        # Update state with match results
        state.suggested_skill = match_result.skill_name
        state.intent = match_result.intent
        state.confidence = match_result.confidence

        logger.info(
            f"Skill matched: skill={match_result.skill_name}, "
            f"intent={match_result.intent.value}, "
            f"confidence={match_result.confidence:.2f}, "
            f"reasoning={match_result.reasoning}"
        )

    except Exception as e:
        logger.error(f"Failed to classify intent: {e}")
        state.intent = IntentType.GENERAL_CHAT
        state.confidence = 0.3
        state.suggested_skill = None

    return state


async def route_skill_node(state: AgentState) -> AgentState:
    """
    Route to appropriate skill and execute, with LLM fallback.

    Supports multiple execution backends:
    1. MS-Agent ScriptExecutor (preferred, in-process execution)
    2. File-based skills from skills/ directory (subprocess fallback)
    3. DSPy-based skills from database

    Args:
        state: Current agent state

    Returns:
        Updated agent state with skill execution results
    """
    logger.info(f"Routing to skill: {state.suggested_skill or 'default'}")
    logger.info(f"DEBUG route_skill_node: patient_context exists={state.patient_context is not None}")
    if state.patient_context:
        logger.info(f"DEBUG route_skill_node: patient_context.vital_signs keys={list(state.patient_context.vital_signs.keys())}")
    state.status = AgentStatus.EXECUTING_SKILL
    state.current_step = "route_skill"

    skill_executed = False

    if state.suggested_skill:
        # Try MS-Agent ScriptExecutor first (preferred)
        try:
            from src.infrastructure.agent.ms_agent_executor import execute_skill_via_msagent, get_execution_backend

            backend = get_execution_backend()
            logger.info(f"Using {backend} backend for skill execution")

            result = await execute_skill_via_msagent(
                skill_name=state.suggested_skill,
                user_input=state.user_input,
                patient_context=state.patient_context,
                timeout=30
            )

            if result:
                logger.info(f"DEBUG route_skill_node: Got result from {backend}: success={result.success}, result_data={result.result_data is not None}, skill_name={result.skill_name}")
                state.add_skill_result(result)
                logger.info(f"DEBUG route_skill_node: After add_skill_result, executed_skills count={len(state.executed_skills)}")
                skill_executed = True

                # Update appropriate result field based on intent
                if result.success and result.result_data:
                    # Extract data from result_data (file-based skills wrap data in "data" field)
                    result_content = result.result_data.get("data", result.result_data) if isinstance(result.result_data, dict) else result.result_data

                    logger.info(f"[DEBUG route_skill] result_content type: {type(result_content).__name__}")
                    logger.info(f"[DEBUG route_skill] result_content keys: {list(result_content.keys()) if isinstance(result_content, dict) else 'not dict'}")
                    logger.info(f"[DEBUG route_skill] result_content: {result_content}")

                    if state.intent == IntentType.HEALTH_ASSESSMENT:
                        state.health_assessment = result_content
                        logger.info(f"[DEBUG route_skill] Set state.health_assessment, has 'modules': {'modules' in result_content if isinstance(result_content, dict) else 'not dict'}")
                    elif state.intent == IntentType.RISK_PREDICTION:
                        state.risk_prediction = result.result_data
                    elif state.intent == IntentType.HEALTH_PLAN:
                        state.health_plan = result.result_data
                    elif state.intent == IntentType.TRIAGE:
                        state.triage_recommendation = result.result_data
                    elif state.intent == IntentType.MEDICATION_CHECK:
                        state.medication_recommendation = result.result_data
                    elif state.intent == IntentType.SERVICE_RECOMMENDATION:
                        state.service_recommendation = result.result_data

                logger.info(f"{backend.upper()} skill execution completed: {result.skill_name} in {result.execution_time}ms")

        except Exception as e:
            logger.warning(f"{backend.upper()} skill execution failed: {e}")
            import traceback
            traceback.print_exc()

        # Fall back to DSPy skill registry if MS-Agent/file-based execution failed
        if not skill_executed:
            try:
                from src.infrastructure.dspy import SkillRegistry

                registry = SkillRegistry()
                skill = registry.get(state.suggested_skill)

                if skill and skill.config.enabled:
                    # Prepare skill inputs
                    skill_inputs = {
                        "patient_data": state.patient_context.basic_info if state.patient_context else {},
                        "vital_signs": state.patient_context.vital_signs if state.patient_context else {},
                        "medical_history": state.patient_context.medical_history if state.patient_context else {},
                        "user_query": state.user_input,
                    }

                    # Execute skill
                    start_time = time.time()
                    dspy_result = await skill.execute(**skill_inputs)
                    execution_time = int((time.time() - start_time) * 1000)

                    # Create skill result
                    skill_result = SkillExecutionResult(
                        skill_name=state.suggested_skill,
                        success=dspy_result.success,
                        result_data=dspy_result.data,
                        error=dspy_result.error,
                        execution_time=execution_time,
                    )

                    state.add_skill_result(skill_result)
                    skill_executed = True

                    # Update appropriate result field based on intent
                    if dspy_result.success and dspy_result.data:
                        if state.intent == IntentType.HEALTH_ASSESSMENT:
                            state.health_assessment = dspy_result.data
                        elif state.intent == IntentType.RISK_PREDICTION:
                            state.risk_prediction = dspy_result.data
                        elif state.intent == IntentType.HEALTH_PLAN:
                            state.health_plan = dspy_result.data
                        elif state.intent == IntentType.TRIAGE:
                            state.triage_recommendation = dspy_result.data
                        elif state.intent == IntentType.MEDICATION_CHECK:
                            state.medication_recommendation = dspy_result.data
                        elif state.intent == IntentType.SERVICE_RECOMMENDATION:
                            state.service_recommendation = dspy_result.data

                    logger.info(f"DSPy skill execution completed: {skill_result.skill_name}")

            except Exception as e:
                logger.debug(f"DSPy skill execution failed: {e}")

    # Use LLM fallback if no skill was executed or skill failed
    if not skill_executed or state.error_message:
        logger.info("Using LLM fallback for response generation")
        state.final_response = await _generate_llm_response(
            state.user_input,
            state.patient_id,
            state.conversation_memory,
            state.patient_context,
            matched_skill=state.suggested_skill,
        )

    return state


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
        logger.info(f"DEBUG _execute_file_skill: input_data keys={list(input_data.keys())}")
        logger.info(f"DEBUG _execute_file_skill: patient_data={input_data['patient_data']}")
        logger.info(f"DEBUG _execute_file_skill: vital_signs={input_data['vital_signs']}")
        logger.info(f"DEBUG _execute_file_skill: medical_history={input_data['medical_history']}")

        # For now, use subprocess to execute the script
        # TODO: Implement proper skill execution framework
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

        logger.info(f"DEBUG _execute_file_skill: Created input file: {input_file}")

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
            logger.info(f"DEBUG _execute_file_skill: Setting PYTHONPATH={env['PYTHONPATH']}")

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

            logger.info(f"DEBUG _execute_file_skill: subprocess returncode={result.returncode}, stdout_len={len(result.stdout)}, stderr_len={len(result.stderr) if result.stderr else 0}")
            if result.stderr:
                logger.info(f"DEBUG _execute_file_skill: stderr={result.stderr[:500]}")

            # Parse output
            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)
                    logger.info(f"DEBUG _execute_file_skill: parsed JSON successfully, keys={list(output_data.keys()) if isinstance(output_data, dict) else 'N/A'}")
                    return SkillExecutionResult(
                        skill_name=skill_name,
                        success=True,
                        result_data=output_data,
                        execution_time=execution_time,
                    )
                except json.JSONDecodeError as e:
                    logger.info(f"DEBUG _execute_file_skill: JSONDecodeError: {e}, stdout={result.stdout[:500]}")
                    # Script returned text output, not JSON
                    return SkillExecutionResult(
                        skill_name=skill_name,
                        success=True,
                        result_data={"output": result.stdout},
                        execution_time=execution_time,
                    )
            else:
                logger.info(f"DEBUG _execute_file_skill: returncode != 0, error={result.stderr or 'Unknown error'}")
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
        system_prompt = f"""你是一个专业的健康管理助手，帮助用户进行健康评估、风险预测和健康管理。

{skill_knowledge}
你的职责：
1. 回答用户的健康相关问题
2. **记住用户之前提供的信息**（姓名、年龄、症状、指标等）
3. **如果用户已经提供过基本信息，直接使用这些信息进行分析，不要再询问**
4. 提供个性化的健康建议
5. 在需要时建议用户咨询专业医生
6. 保持专业、友善的语气{conversation_context}

**重要：请使用 Markdown 格式组织你的回答**

回答格式建议：
- 使用 ## 标题组织内容
- 使用 - 列表列出要点
- 使用 **粗体** 强调重要信息
- 使用 > 引用块给出提醒
- 使用 ``` 代码块展示具体数据（如有）

请注意：
- 你不能替代专业医生的诊断
- 对于紧急医疗情况，建议用户立即就医
- 保持回答简洁明了但全面"""

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
            logger.info(f"DEBUG aggregate_results_node: Checking skill_result={skill_result.skill_name}, success={skill_result.success}, has_result_data={skill_result.result_data is not None}")
            if skill_result.success and skill_result.result_data:
                # Handle both direct status and wrapped data status
                result_content = skill_result.result_data
                logger.info(f"DEBUG aggregate_results_node: result_content type={type(result_content).__name__}, keys={list(result_content.keys()) if isinstance(result_content, dict) else 'N/A'}")
                if isinstance(result_content, dict):
                    # Check if data is wrapped in a "data" field (file-based skill format)
                    data = result_content.get("data", result_content)
                    logger.info(f"DEBUG aggregate_results_node: data keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}, status={data.get('status') if isinstance(data, dict) else 'N/A'}")
                    if data.get("status") == "incomplete":
                        logger.info(f"Skill {skill_result.skill_name} returned incomplete status")
                        required_fields = data.get("required_fields", [])
                        message = data.get("message", "需要补充健康数据")
                        state.final_response = _format_incomplete_data_response(message, required_fields)
                        return state

        # Gather all results
        all_results = state.get_all_results()

        # Check for file-based skill modules (e.g., chronic-disease-risk-assessment)
        for skill_result in state.executed_skills:
            logger.info(f"DEBUG aggregate: checking skill_result={skill_result.skill_name}, success={skill_result.success}, has_result_data={skill_result.result_data is not None}")
            if skill_result.success and skill_result.result_data:
                result_content = skill_result.result_data
                logger.info(f"DEBUG aggregate: result_content type={type(result_content).__name__}, keys={list(result_content.keys()) if isinstance(result_content, dict) else 'not dict'}")
                logger.info(f"DEBUG aggregate: result_content content: {result_content}")

                # Extract modules data from result_content and store in health_assessment
                modules_data = None
                print(f"[DEBUG aggregate 1] Checking for modules in result_content", flush=True)
                logger.info(f"DEBUG aggregate: Checking for modules in result_content")
                if "modules" in result_content:
                    print(f"[DEBUG aggregate 2] Found 'modules' key directly in result_content", flush=True)
                    logger.info(f"DEBUG aggregate: Found 'modules' key directly in result_content")
                    modules_data = {"modules": result_content["modules"]}
                    print(f"[DEBUG aggregate 3] Extracted modules_data: {modules_data}", flush=True)
                    logger.info(f"DEBUG aggregate: Extracted modules_data: {modules_data}")
                elif "final_output" in result_content and isinstance(result_content["final_output"], dict):
                    logger.info(f"DEBUG aggregate: Found 'final_output' key, checking nested")
                    final_output = result_content["final_output"]
                    if "modules" in final_output:
                        logger.info(f"DEBUG aggregate: Found 'modules' in final_output")
                        modules_data = {"modules": final_output["modules"]}
                    elif "data" in final_output and isinstance(final_output["data"], dict):
                        logger.info(f"DEBUG aggregate: Found 'data' in final_output, checking nested")
                        final_data = final_output["data"]
                        if "modules" in final_data:
                            logger.info(f"DEBUG aggregate: Found 'modules' in final_output.data")
                            modules_data = {"modules": final_data["modules"]}

                logger.info(f"DEBUG aggregate: modules_data={'SET' if modules_data else 'None'}, state.intent={state.intent}, HEALTH_ASSESSMENT={IntentType.HEALTH_ASSESSMENT}")
                if modules_data and state.intent == IntentType.HEALTH_ASSESSMENT:
                    # Update health_assessment with extracted modules
                    state.health_assessment = modules_data
                    logger.info(f"DEBUG aggregate: Updated health_assessment with modules data: {state.health_assessment}")
                if isinstance(result_content, dict):
                    # First try to get data from "data" field (wrapper format)
                    # Then check if modules is directly in result_content (SKILL.md workflow format)
                    data = result_content.get("data", result_content)
                    logger.info(f"DEBUG aggregate: data type={type(data).__name__}, keys={list(data.keys()) if isinstance(data, dict) else 'not dict'}")

                    # Check if skill returned modules (complete assessment)
                    # Modules can be in multiple locations:
                    # 1. data["modules"] (standard wrapper format)
                    # 2. result_content["modules"] (direct format)
                    # 3. result_content["final_output"]["data"]["modules"] (MS-Agent executor format)
                    modules_source = None
                    if "modules" in data and isinstance(data, dict):
                        modules_source = data
                        logger.info(f"DEBUG aggregate: Found modules in data (location 1)")
                    elif "modules" in result_content and isinstance(result_content, dict):
                        modules_source = result_content
                        logger.info(f"DEBUG aggregate: Found modules in result_content (location 2)")
                    elif "final_output" in result_content and isinstance(result_content["final_output"], dict):
                        final_output = result_content["final_output"]
                        logger.info(f"DEBUG aggregate: Found final_output, keys={list(final_output.keys()) if isinstance(final_output, dict) else 'not dict'}")
                        # Check for modules directly in final_output (skill return format)
                        if "modules" in final_output:
                            modules_source = final_output
                            logger.info(f"DEBUG aggregate: Found modules in final_output (location 3a)")
                        # Also check nested in final_output.data for legacy format
                        elif "data" in final_output and isinstance(final_output["data"], dict):
                            final_data = final_output["data"]
                            logger.info(f"DEBUG aggregate: Found final_output.data, keys={list(final_data.keys()) if isinstance(final_data, dict) else 'not dict'}")
                            if "modules" in final_data:
                                modules_source = final_data
                                logger.info(f"DEBUG aggregate: Found modules in final_output.data (location 3b)")

                    logger.info(f"DEBUG aggregate: modules_source={'FOUND' if modules_source else 'None'}")

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

                        # Process string-based modules (old format from chronic-disease-risk-assessment)
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

                        # Add header with retrieved data info
                        response_parts = []
                        if state.patient_context and state.party_id:
                            response_parts.append(f"> **已从平安健康档案系统获取您的健康数据**\n")
                            response_parts.append(f"**已获取的信息**:\n")
                            response_parts.append(f"- 客户号: {state.party_id}\n")
                            # Show medical history if available
                            if state.patient_context.medical_history:
                                diagnoses = state.patient_context.medical_history.get("diagnoses", [])
                                if diagnoses:
                                    diagnosis_codes = [d.get("code", "") for d in diagnoses if d.get("code")]
                                    if diagnosis_codes:
                                        response_parts.append(f"- 病史: {', '.join(diagnosis_codes)}\n")

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
            print(f"[DEBUG aggregate FINAL] state.health_assessment type: {type(state.health_assessment).__name__}", flush=True)
            print(f"[DEBUG aggregate FINAL] state.health_assessment keys: {list(state.health_assessment.keys()) if isinstance(state.health_assessment, dict) else 'not dict'}", flush=True)
            print(f"[DEBUG aggregate FINAL] state.health_assessment content: {state.health_assessment}", flush=True)
            logger.info(f"[DEBUG aggregate] state.health_assessment type: {type(state.health_assessment).__name__}")
            logger.info(f"[DEBUG aggregate] state.health_assessment keys: {list(state.health_assessment.keys()) if isinstance(state.health_assessment, dict) else 'not dict'}")
            logger.info(f"[DEBUG aggregate] state.health_assessment content: {state.health_assessment}")
            logger.info(f"DEBUG aggregate: Calling _format_assessment_response, state.health_assessment type={type(state.health_assessment).__name__}, keys={list(state.health_assessment.keys()) if isinstance(state.health_assessment, dict) else 'not dict'}")
            print(f"[DEBUG aggregate FINAL] About to call _format_assessment_response", flush=True)
            state.final_response = _format_assessment_response(
                state.health_assessment,
                state.patient_context
            )
            print(f"[DEBUG aggregate FINAL] Returned from _format_assessment_response, final_response length: {len(state.final_response) if state.final_response else 0}", flush=True)
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


async def skip_skill_node(state: AgentState) -> AgentState:
    """
    Skip skill execution and use LLM for general response.

    Args:
        state: Current agent state

    Returns:
        Updated agent state with LLM-generated response
    """
    logger.info("Skipping skill execution, using LLM fallback")
    state.status = AgentStatus.EXECUTING_SKILL
    state.current_step = "skip_skill"

    # Generate LLM response
    state.final_response = await _generate_llm_response(
        state.user_input,
        state.patient_id,
        state.conversation_memory,
        state.patient_context,
        matched_skill=state.suggested_skill,
    )

    return state


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
    logger.info(f"DEBUG save_memory_node state keys: {list(state.model_dump().keys())}")
    logger.info(f"DEBUG save_memory_node: intent={state.intent}, suggested_skill={state.suggested_skill}, confidence={state.confidence}")

    try:
        from src.infrastructure.memory import MemoryStore

        memory_store = MemoryStore()

        # Generate or use existing session_id
        # For tracking, we can use patient_id + timestamp or a UUID
        import uuid
        session_id = getattr(state, 'session_id', None) or f"session_{uuid.uuid4().hex[:12]}"

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


def _format_modules_response(assessment: Dict[str, Any], patient_context: Optional[PatientContext] = None) -> str:
    """Format modules-based assessment result (from cvd-risk-assessment and similar skills)."""
    import sys
    import logging
    logger = logging.getLogger(__name__)
    print("=" * 80, flush=True)
    print("[_format_modules_response ENTRY] CALLED!", flush=True)
    print("=" * 80, flush=True)
    sys.stdout.flush()
    try:
        msg = f"[_format_modules_response] ENTRY - assessment type: {type(assessment)}"
        print(msg, flush=True)
        logger.info(msg)
        print(f"[_format_modules_response] assessment keys: {list(assessment.keys()) if isinstance(assessment, dict) else 'N/A'}", flush=True)
        logger.info(f"[_format_modules_response] assessment keys: {list(assessment.keys()) if isinstance(assessment, dict) else 'N/A'}")
        modules = assessment.get("modules", {})
        print(f"[_format_modules_response] modules keys: {list(modules.keys()) if isinstance(modules, dict) else 'not dict'}", flush=True)
        logger.info(f"[_format_modules_response] modules: {modules}")
        sys.stdout.flush()
        response = ""
    except Exception as e:
        print(f"[_format_modules_response] ERROR: {e}", flush=True)
        logger.error(f"[_format_modules_response] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}"

    # Debug: print what modules we received
    print(f"[DEBUG _format_modules_response] modules keys: {list(modules.keys())}", flush=True)
    logger.info(f"[DEBUG _format_modules_response] modules keys: {list(modules.keys())}")
    for section_name, section_content in modules.items():
        print(f"[DEBUG _format_modules_response] section '{section_name}': {list(section_content.keys()) if isinstance(section_content, dict) else type(section_content).__name__}", flush=True)
        logger.info(f"[DEBUG _format_modules_response] section '{section_name}': {list(section_content.keys()) if isinstance(section_content, dict) else type(section_content).__name__}")

    # Add header with retrieved data info
    if patient_context and patient_context.basic_info:
        basic_info = patient_context.basic_info
        if basic_info.get("source") == "ping_an_api":
            response += "> **已从平安健康档案系统获取您的健康数据**\n\n"
            response += "**已获取的信息**:\n"
            if "age" in basic_info:
                response += f"- 年龄: {basic_info['age']}岁\n"
            if patient_context.medical_history:
                diagnoses = patient_context.medical_history.get("diagnoses", [])
                if diagnoses:
                    diagnosis_codes = [d.get("code", "") for d in diagnoses if d.get("code")]
                    if diagnosis_codes:
                        response += f"- 病史: {', '.join(diagnosis_codes)}\n"
            response += "\n"

    # Define section order and titles
    section_order = ["health_insight", "risk_assessment"]
    section_titles = {
        "risk_assessment": "## 📊 心血管风险评估结果 [NEW_FORMAT_2026]",
        "health_insight": "## 💡 健康洞察 [NEW_FORMAT_2026]"
    }

    # Format modules in defined order
    for section_name in section_order:
        if section_name not in modules:
            continue

        section_content = modules[section_name]
        print(f"[DEBUG] Processing section: {section_name}")

        # Skip empty content
        if not section_content:
            continue
        if not isinstance(section_content, (dict, str)):
            continue

        # Get section title
        title = section_titles.get(section_name, f"## {section_name}")
        response += f"{title}\n\n"

        # Format health_insight section (优先显示)
        if section_name == "health_insight":
            if isinstance(section_content, str):
                response += section_content + "\n\n"
            elif isinstance(section_content, dict):
                for key, value in section_content.items():
                    if value and isinstance(value, str):
                        response += f"{value}\n\n"

        # Format risk assessment section
        elif section_name == "risk_assessment":
            risk_level_zh = section_content.get("risk_level_zh", "未知")
            factors_count = section_content.get("risk_factors_count", 0)
            key_factors = section_content.get("key_factors", [])
            follow_up = section_content.get("follow_up", "")
            assessment_path = section_content.get("assessment_path", "")
            ten_year_risk = section_content.get("ten_year_risk")
            ten_year_risk_zh = section_content.get("ten_year_risk_zh")
            ten_year_cvd_risk_zh = section_content.get("ten_year_cvd_risk_zh")
            lifetime_risk = section_content.get("lifetime_risk")
            lifetime_risk_zh = section_content.get("lifetime_risk_zh", "")

            # Debug logging
            logger.info(f"[DEBUG RISK] level_zh={risk_level_zh}, factors={factors_count}")

            # 风险等级卡片样式
            response += f"### 🎯 风险等级\n\n"
            response += f"| 评估项目 | 风险等级 |\n"
            response += f"|---------|---------|\n"
            response += f"| 心血管病发病风险 | **{risk_level_zh}** |\n"

            if ten_year_risk_zh:
                response += f"| 10年ASCVD风险评估 | {ten_year_risk_zh} |\n"
            if ten_year_cvd_risk_zh:
                response += f"| 10年心血管病发病风险 | {ten_year_cvd_risk_zh} |\n"
            if lifetime_risk:
                lifetime_text = lifetime_risk_zh if lifetime_risk_zh else ("高危" if lifetime_risk == "high" else "低危")
                response += f"| 余生风险 | {lifetime_text} |\n"
            response += "\n"

            # 危险因素展示
            if factors_count > 0:
                response += f"### ⚠️ 识别的危险因素 ({factors_count}个)\n\n"
                for factor in key_factors:
                    response += f"- {factor}\n"
                response += "\n"

            # 随访建议
            if follow_up:
                response += f"### 📅 随访建议\n\n"
                response += f"**随访间隔**: {follow_up}\n\n"

        # Format other sections
        else:
            for key, value in section_content.items():
                if value and isinstance(value, (str, int, float)):
                    response += f"- **{key}**: {value}\n"
                elif isinstance(value, list):
                    for item in value:
                        response += f"- {item}\n"
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_value and sub_value != "N/A":
                            response += f"- **{sub_key}**: {sub_value}\n"
            response += "\n"

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
    if patient_context and patient_context.basic_info:
        basic_info = patient_context.basic_info
        if basic_info.get("source") == "ping_an_api":
            response += "> **已从平安健康档案系统获取您的健康数据**\n\n"
            # Show what data was retrieved
            retrieved_info = []
            if "age" in basic_info:
                retrieved_info.append(f"年龄: {basic_info['age']}岁")
            if "party_id" in basic_info:
                retrieved_info.append(f"客户号: {basic_info['party_id']}")
            if patient_context.medical_history:
                diagnoses = patient_context.medical_history.get("diagnoses", [])
                if diagnoses:
                    diagnosis_codes = [d.get("code", "") for d in diagnoses if d.get("code")]
                    if diagnosis_codes:
                        retrieved_info.append(f"病史: {', '.join(diagnosis_codes)}")
                sport_records = patient_context.medical_history.get("sport_records")
                if sport_records:
                    retrieved_info.append("运动记录: 已获取")

            if retrieved_info:
                response += "**已获取的信息**:\n"
                for info in retrieved_info:
                    response += f"- {info}\n"
                response += "\n"

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
