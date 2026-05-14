"""
LLM-based Prescription Generator.

Generates personalised intervention prescriptions based on the user's health
data (population classification, abnormal indicators, disease predictions,
symptoms, risk warnings).  Falls back to the script-generated template
prescriptions when LLM call fails or returns invalid output.
"""
import json
import logging
import re
from typing import Any, Dict, List

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed values for validation
# ---------------------------------------------------------------------------
_VALID_TYPES = {"diet", "exercise", "sleep", "monitoring", "medication"}
_VALID_PRIORITIES = {"high", "medium", "low"}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_prescriptions(
    structured_result: Dict[str, Any],
    patient_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate personalised prescriptions via LLM.

    Args:
        structured_result: The full structured assessment result containing
            population_classification, abnormal_indicators, disease_prediction,
            risk_warnings, and the template intervention_prescriptions.
        patient_data: Merged health data (age, gender, vital signs, etc.).

    Returns:
        A list of prescription dicts matching the existing schema, or the
        original template prescriptions on failure.
    """
    fallback = structured_result.get("intervention_prescriptions", [])
    if not isinstance(fallback, list):
        fallback = []

    # Skip if there's nothing to personalise
    if not structured_result.get("population_classification", {}).get("primary_category"):
        logger.debug("No population classification found, skipping LLM prescription generation")
        return fallback

    prompt = _build_prompt(structured_result, patient_data)
    try:
        text = await _call_llm(prompt)
        prescriptions = _parse_response(text)
        if prescriptions:
            logger.info(f"LLM generated {len(prescriptions)} personalised prescriptions")
            return prescriptions
        logger.warning("LLM returned empty prescriptions, using fallback")
    except Exception as e:
        logger.warning(f"LLM prescription generation failed: {e}")

    return fallback


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(structured_result: Dict[str, Any], patient_data: Dict[str, Any]) -> str:
    """Build the LLM prompt from structured assessment data."""

    # Population classification
    pop = structured_result.get("population_classification", {})
    category = pop.get("primary_category", "未知")

    # Abnormal indicators
    abn = structured_result.get("abnormal_indicators", [])
    if isinstance(abn, dict):
        indicators = abn.get("indicators", [])
    elif isinstance(abn, list):
        indicators = abn
    else:
        indicators = []

    # Disease prediction
    predictions = structured_result.get("disease_prediction", [])

    # Risk warnings
    warnings = structured_result.get("risk_warnings", [])

    # Template prescriptions (for reference)
    templates = structured_result.get("intervention_prescriptions", [])

    # Patient basic info
    age = patient_data.get("age", "未知")
    gender = patient_data.get("gender", "未知")
    gender_zh = "男" if gender in ("male", "男", "M") else "女" if gender in ("female", "女", "F") else str(gender)

    sections = []
    sections.append(f"## 患者基本信息\n- 年龄：{age}\n- 性别：{gender_zh}")
    sections.append(f"## 健康人群分组\n- 分组：{category}")
    grouping_basis = pop.get("grouping_basis", [])
    if grouping_basis:
        for b in grouping_basis:
            if isinstance(b, dict):
                sections.append(f"  - {b.get('disease', '')}：{b.get('note', b.get('level', ''))}")

    if indicators:
        sections.append("## 异常指标")
        for ind in indicators[:15]:
            if isinstance(ind, dict):
                name = ind.get("name", "")
                value = ind.get("value", "")
                unit = ind.get("unit", "")
                ref = ind.get("reference_range", ind.get("reference", ""))
                severity = ind.get("severity", "")
                line = f"- {name}：{value} {unit}".strip()
                if ref:
                    line += f"（参考范围：{ref}）"
                if severity:
                    line += f" [{severity}]"
                sections.append(line)

    if predictions:
        sections.append("## 疾病风险预测")
        for p in predictions[:5]:
            if isinstance(p, dict):
                name = p.get("disease_name", "")
                level = p.get("risk_level", "")
                prob = p.get("probability", "")
                line = f"- {name}：{level}"
                if prob:
                    line += f"（概率 {prob}）"
                sections.append(line)

    if warnings:
        sections.append("## 风险提示")
        for w in warnings[:5]:
            if isinstance(w, dict):
                title = w.get("title", "")
                desc = w.get("description", "")
                level = w.get("level", "")
                sections.append(f"- {title}：{desc} [{level}]")

    data_context = "\n".join(sections)

    template_str = json.dumps(templates, ensure_ascii=False, indent=2) if templates else "[]"

    prompt = f"""你是一个专业的健康管理处方生成系统。请根据以下患者的健康评估数据，生成个性化的干预处方。

{data_context}

## 要求

1. 根据患者的具体情况（人群分组、异常指标、疾病风险），生成 **具体、可执行、个性化** 的干预建议
2. 每条建议要针对患者的实际指标数值给出具体指导（如血压偏高多少、血糖控制目标等）
3. 按严重程度调整优先级：高危→high，中危→medium，低危→low
4. 确保建议之间不重复、不矛盾

## 输出格式

严格输出以下 JSON 数组（不要包含其他文字）：

```json
[
  {{
    "type": "diet",
    "title": "饮食处方",
    "content": ["具体建议1", "具体建议2", "具体建议3"],
    "priority": "high"
  }},
  {{
    "type": "exercise",
    "title": "运动处方",
    "content": ["具体建议1", "具体建议2"],
    "priority": "medium"
  }}
]
```

## 约束

- type 范围：diet / exercise / sleep / monitoring / medication
- priority 范围：high / medium / low
- 每类处方 2-4 条具体建议
- 对于 medication 类型，仅给出监测建议和就医建议，不要开具体药物
- 没有相关异常的处方类型可以省略

## 参考模板处方（仅作参考，需要个性化和增强）

{template_str}
"""
    return prompt


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

async def _call_llm(prompt: str) -> str:
    """Call the LLM and return raw text response."""
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("No API key configured for LLM prescription generation")

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url if settings.anthropic_base_url != "https://api.anthropic.com" else None,
    )

    response = client.messages.create(
        model=settings.model,
        max_tokens=2000,
        system="你是一个专业的健康管理处方生成系统。根据患者的健康数据生成个性化干预建议。严格按照要求的JSON格式输出，不要包含其他文字。",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_response(text: str) -> List[Dict[str, Any]]:
    """Parse the LLM response text into a validated list of prescription dicts."""
    # Extract JSON from markdown code block or raw text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try raw JSON array
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            json_str = json_match.group(0)
        else:
            logger.warning("No JSON found in LLM prescription response")
            return []

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM prescription JSON: {e}")
        return []

    if not isinstance(data, list):
        logger.warning("LLM prescription response is not a list")
        return []

    validated = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ptype = item.get("type", "")
        priority = item.get("priority", "medium")
        if ptype not in _VALID_TYPES:
            continue
        if priority not in _VALID_PRIORITIES:
            priority = "medium"
        content = item.get("content", [])
        if isinstance(content, str):
            content = [content]
        if not isinstance(content, list) or not content:
            continue
        validated.append({
            "type": ptype,
            "title": item.get("title", _default_title(ptype)),
            "content": content,
            "priority": priority,
        })

    return validated


def _default_title(ptype: str) -> str:
    """Default title for a prescription type."""
    return {
        "diet": "饮食处方",
        "exercise": "运动处方",
        "sleep": "睡眠处方",
        "monitoring": "监测建议",
        "medication": "药物建议",
    }.get(ptype, ptype)
