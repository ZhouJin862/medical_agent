"""
LLM-based Health Data Extractor.

Uses LLM to extract all health-related data from user messages into a
structured JSON format. This replaces the fragile regex-based extraction
in `_extract_vital_signs_from_user_input` with a more robust approach
that handles natural language, ambiguous formats, and context-dependent
fields like sport_target, symptoms, disease severity, etc.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一个健康数据提取助手。从用户的自然语言输入中提取所有与健康评估相关的数据。

严格按照以下JSON格式输出，只包含能从用户输入中明确提取到的字段，未提及的字段不要输出：

{
  "basic_info": {
    "age": 数字(整数),
    "gender": "male"或"female",
    "sport_target": "运动目标文字(如:改善体型、减脂减重、改善饮食、改善睡眠等)",
    "smoke": true或false,
    "drink": true或false
  },
  "vital_signs": {
    "height": 数字(cm),
    "weight": 数字(kg),
    "bmi": 数字(自动计算),
    "waist": 数字(cm),
    "systolic_bp": 数字(收缩压mmHg),
    "diastolic_bp": 数字(舒张压mmHg),
    "fasting_glucose": 数字(空腹血糖mmol/L),
    "postprandial_glucose": 数字(餐后血糖mmol/L),
    "hba1c": 数字(糖化血红蛋白%),
    "total_cholesterol": 数字(总胆固醇mmol/L),
    "tg": 数字(甘油三酯mmol/L),
    "ldl_c": 数字(低密度脂蛋白mmol/L),
    "hdl_c": 数字(高密度脂蛋白mmol/L),
    "uric_acid": 数字(尿酸μmol/L)
  },
  "medical_history": {
    "disease_labels": ["疾病名称列表(如:hypertension,diabetes,hyperlipidemia,hyperuricemia,heart_disease)"],
    "disease_severity": {"疾病名称": "严重程度(轻度/中度/重度)"},
    "symptoms": ["症状列表(如:头晕,胸闷,乏力等)"]
  }
}

重要规则：
1. 只提取用户明确提到的数据，不要猜测或推断
2. 血压格式"145/90"中，145是收缩压(systolic_bp)，90是舒张压(diastolic_bp)
3. 疾病名称统一用英文: 高血压→hypertension, 糖尿病→diabetes, 高血脂→hyperlipidemia, 高尿酸/痛风→hyperuricemia, 心脏病/冠心病→heart_disease
4. 如果用户提到运动目标(如"改善体型"、"减脂减重"等)，放入basic_info.sport_target
5. 如果有身高和体重，自动计算BMI
6. 只输出JSON，不要输出任何其他文字"""

_EXTRACT_JSON_PATTERN = re.compile(r'\{[\s\S]*\}', re.DOTALL)


async def extract_health_data_from_message(user_input: str) -> Dict[str, Any]:
    """Extract structured health data from a user's natural language message using LLM.

    Args:
        user_input: The user's message text.

    Returns:
        Dict with keys: basic_info, vital_signs, medical_history.
        Each sub-dict only contains fields that were successfully extracted.
    """
    settings = get_settings()
    if not settings.llm_api_key:
        logger.warning("No API key for LLM health data extraction, returning empty dict")
        return {}

    import openai

    client = openai.OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    try:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]
        response = client.chat.completions.create(
            model=settings.model,
            max_tokens=1000,
            messages=messages,
        )
        raw_text = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"LLM health data extraction failed: {e}")
        return {}

    # Extract JSON from response
    m = _EXTRACT_JSON_PATTERN.search(raw_text)
    if not m:
        logger.warning(f"No JSON found in LLM extraction response: {raw_text[:200]}")
        return {}

    try:
        extracted = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error in LLM extraction: {e}")
        return {}

    # Validate and normalize the extracted data
    result = {}
    for section in ("basic_info", "vital_signs", "medical_history"):
        section_data = extracted.get(section)
        if section_data and isinstance(section_data, dict):
            # Remove None/empty values
            cleaned = {}
            for k, v in section_data.items():
                if v is not None and v != "" and v != []:
                    cleaned[k] = v
            if cleaned:
                result[section] = cleaned

    # Auto-calculate BMI if height and weight present but BMI missing
    vs = result.get("vital_signs", {})
    if "bmi" not in vs and "height" in vs and "weight" in vs:
        try:
            h = float(vs["height"])
            height_m = h / 100.0 if h > 2.5 else h
            w = float(vs["weight"])
            if height_m > 0:
                vs["bmi"] = round(w / (height_m * height_m), 1)
        except (TypeError, ZeroDivisionError):
            pass

    logger.info(f"LLM extracted health data: {list(result.keys())}, "
                f"basic_info={list(result.get('basic_info', {}).keys())}, "
                f"vital_signs={list(result.get('vital_signs', {}).keys())}, "
                f"medical_history={list(result.get('medical_history', {}).keys())}")

    return result


def merge_extracted_into_health_data(
    extracted: Dict[str, Any],
    health_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge LLM-extracted health data into the health_data dict that
    load_patient_node consumes.

    Maps the LLM output format (basic_info, vital_signs, medical_history)
    to the flat format expected by health_data / ping_an_health_data.

    Args:
        extracted: LLM extraction result with basic_info/vital_signs/medical_history.
        health_data: Target dict to merge into (modified in-place and returned).

    Returns:
        Updated health_data dict.
    """
    if not extracted:
        return health_data

    # basic_info fields → top-level health_data keys
    basic_info = extracted.get("basic_info", {})
    _BASIC_INFO_MAP = {
        "age": "age",
        "gender": "gender",
        "sport_target": "sport_target",
        "smoke": "smoke",
        "drink": "drink",
    }
    for llm_key, hd_key in _BASIC_INFO_MAP.items():
        if llm_key in basic_info:
            val = basic_info[llm_key]
            # User-provided data takes precedence over Ping An data
            health_data[hd_key] = val

    # vital_signs fields → top-level health_data keys (same names)
    vital_signs = extracted.get("vital_signs", {})
    for k, v in vital_signs.items():
        # User-provided data takes precedence over Ping An data
        health_data[k] = v

    # medical_history fields
    mh = extracted.get("medical_history", {})
    if "disease_labels" in mh and mh["disease_labels"]:
        existing = health_data.get("diseaseLabels", [])
        if not isinstance(existing, list):
            existing = []
        merged = list(set(existing + mh["disease_labels"]))
        health_data["diseaseLabels"] = merged
    if "disease_severity" in mh:
        health_data["disease_severity"] = mh["disease_severity"]
    if "symptoms" in mh:
        health_data["symptoms"] = mh["symptoms"]

    return health_data