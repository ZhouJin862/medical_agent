"""
LLM-based Risk Warning and Prescription Recommendation Skills.

Pure-LLM skills (no scripts) that generate risk_warnings and
intervention_prescriptions based on the patient's health data and
assessment results.  Results are injected into the final structured_result
before the API returns the JSON response.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wiki RAG context helper
# ---------------------------------------------------------------------------

def _get_wiki_context(skill_name: str, health_data: Dict, max_chars: int = 3000) -> str:
    """Load Wiki knowledge base context for prompt injection."""
    try:
        from src.infrastructure.wiki import WikiStore
        store = WikiStore(get_settings().wiki_dir)
        disease_labels = health_data.get("disease_labels", [])
        return store.get_context_for_prompt(skill_name, disease_labels, max_chars)
    except Exception as e:
        logger.warning(f"Failed to load wiki context: {e}")
        return ""


# ---------------------------------------------------------------------------
# Shared LLM call
# ---------------------------------------------------------------------------

async def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the configured LLM and return raw text."""
    import openai

    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("No API key configured for LLM skill")

    client = openai.OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = client.chat.completions.create(
        model=settings.model,
        max_tokens=2000,
        messages=messages,
    )
    return response.choices[0].message.content


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from LLM response text."""
    # Try ```json ... ``` block first
    m = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON object
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Risk Warning Skill
# ---------------------------------------------------------------------------

_RISK_WARNING_SYSTEM = (
    "你是一位专业的健康风险评估专家。根据患者的健康数据，识别当前存在的健康风险"
    "和未来可能发生的风险。严格按照要求的JSON格式输出，不要包含其他文字。"
)


def _build_risk_warning_prompt(
    structured_result: Dict[str, Any],
    health_data: Dict[str, Any],
) -> str:
    """Build the user prompt for the risk-warning skill."""
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

    # Patient info
    age = health_data.get("age", "未知")
    gender = health_data.get("gender", "未知")
    gender_zh = "男" if gender in ("male", "男", "M") else "女" if gender in ("female", "女", "F") else str(gender)

    sections = []
    sections.append(f"## 患者基本信息\n- 年龄：{age}\n- 性别：{gender_zh}")
    sections.append(f"## 健康人群分组\n- 分组：{category}")
    grouping_basis = pop.get("grouping_basis", [])
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
                severity = ind.get("severity", "")
                line = f"- {name}：{value} {unit}".strip()
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

    # Existing risk warnings from scripts (for reference)
    existing_warnings = structured_result.get("risk_warnings", [])
    if existing_warnings:
        sections.append("## 已有风险提醒（供参考）")
        for w in existing_warnings[:5]:
            if isinstance(w, dict):
                sections.append(f"- {w.get('title', '')}：{w.get('description', '')} [{w.get('level', '')}]")

    data_context = "\n".join(sections)

    prompt = f"""请根据以下患者的健康评估数据，生成风险提醒。

{data_context}

## 要求

1. 基于患者实际数据，识别当前存在的健康风险和未来可能发生的风险
2. 风险等级评估要客观：高危→high，中危→medium，低危→low
3. 每个风险都要有明确的数据支撑
4. 建议要具体可操作
5. 如果数据不足以评估某项风险，不要强行给出结论

## 输出格式

严格输出以下JSON（不要包含其他文字）：

```json
{{
  "risk_warnings": [
    {{
      "title": "疾病或异常名称（如：高血压前期、血脂异常、心血管病），不要加"风险"后缀",
      "description": "风险描述",
      "level": "high/medium/low",
      "tip": "针对该风险的简要建议",
      "evidence": "循证依据，引用权威指南或研究（如《中国高血压防治指南2024》、China-PAR模型等），说明该风险判断的权威来源",
      "confidence": 0.85,
      "worsening_risk": "恶化风险描述，说明该风险如果不干预可能如何恶化（如：高血压前期→临床高血压→靶器官损害）",
      "complication_risk": "并发症风险描述，说明该风险可能引发哪些并发症（如：长期高血压可导致冠心病、脑卒中、肾功能不全）"
    }}
  ]
}}
```

## 关于循证和置信度

- evidence：必须引用权威来源，如国家临床指南、中华医学会共识、WHO建议、大型队列研究等。不要引用非权威来源。
- confidence：0到1之间，保留两位小数。数据充分且指南明确→0.80以上；数据部分缺失→0.50-0.80；数据严重不足→0.30以下。

## 关于恶化风险和并发症风险

- worsening_risk：描述当前风险如果不进行干预，随时间推移可能如何恶化进展。需基于疾病自然史和权威指南，说明恶化路径。
- complication_risk：描述当前风险可能引发的具体并发症名称和后果。需基于权威文献，列出最可能发生的并发症。
"""

    # Inject Wiki RAG context
    wiki_ctx = _get_wiki_context("risk-warning", health_data)
    if wiki_ctx:
        prompt += f"""

## 参考指南摘要（基于权威医学指南提取）

{wiki_ctx}

请根据以上参考指南摘要，结合患者实际数据，生成循证建议。引用时请注明具体指南名称和章节。"""

    return prompt


async def generate_risk_warnings(
    structured_result: Dict[str, Any],
    health_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate risk_warnings via LLM risk-warning skill.

    Returns a list of risk_warning dicts, or the original warnings on failure.
    """
    fallback = structured_result.get("risk_warnings", [])
    if not isinstance(fallback, list):
        fallback = []

    # Skip if there's nothing to base warnings on
    if not structured_result.get("population_classification", {}).get("primary_category"):
        logger.debug("No population classification found, skipping LLM risk warning generation")
        return fallback

    prompt = _build_risk_warning_prompt(structured_result, health_data)
    try:
        text = await _call_llm(_RISK_WARNING_SYSTEM, prompt)
        parsed = _extract_json(text)
        if parsed and isinstance(parsed.get("risk_warnings"), list):
            warnings = _validate_risk_warnings(parsed["risk_warnings"])
            if warnings:
                logger.info(f"LLM generated {len(warnings)} risk warnings")
                return warnings
        logger.warning("LLM returned empty/invalid risk warnings, using fallback")
    except Exception as e:
        logger.warning(f"LLM risk warning generation failed: {e}")

    return fallback


def _validate_risk_warnings(warnings: list) -> list:
    """Validate and normalise risk_warning items."""
    valid_levels = {"high", "medium", "low"}
    result = []
    for w in warnings:
        if not isinstance(w, dict):
            continue
        level = str(w.get("level", "medium")).lower()
        if level not in valid_levels:
            level = "medium"
        # Normalise confidence to [0, 1] with 2 decimal places
        confidence = w.get("confidence", 0.70)
        try:
            confidence = round(float(confidence), 2)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.70
        result.append({
            "title": w.get("title", "风险提醒"),
            "description": w.get("description", ""),
            "level": level,
            "tip": w.get("tip", ""),
            "evidence": w.get("evidence", ""),
            "confidence": confidence,
            "worsening_risk": w.get("worsening_risk", ""),
            "complication_risk": w.get("complication_risk", ""),
        })
    return result


# ---------------------------------------------------------------------------
# Prescription Recommendation Skill
# ---------------------------------------------------------------------------

_PRESCRIPTION_SYSTEM = (
    "你是一位专业的健康管理师。根据患者的健康数据、风险评估结果和健康目标，"
    "制定个性化的干预处方，涵盖饮食、运动、睡眠三个方面。"
    "严格按照要求的JSON格式输出，不要包含其他文字。"
)


def _build_prescription_prompt(
    structured_result: Dict[str, Any],
    health_data: Dict[str, Any],
) -> str:
    """Build the user prompt for the prescription-recommendation skill."""
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

    # Risk warnings
    warnings = structured_result.get("risk_warnings", [])

    # Patient info
    age = health_data.get("age", "未知")
    gender = health_data.get("gender", "未知")
    gender_zh = "男" if gender in ("male", "男", "M") else "女" if gender in ("female", "女", "F") else str(gender)
    sport_target = health_data.get("sport_target", "")

    sections = []
    sections.append(f"## 患者基本信息\n- 年龄：{age}\n- 性别：{gender_zh}")
    if sport_target:
        sections.append(f"- 健康目标：{sport_target}")
    sections.append(f"## 健康人群分组\n- 分组：{category}")
    grouping_basis = pop.get("grouping_basis", [])
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
                severity = ind.get("severity", "")
                line = f"- {name}：{value} {unit}".strip()
                if severity:
                    line += f" [{severity}]"
                sections.append(line)

    if warnings:
        sections.append("## 风险提醒")
        for w in warnings[:5]:
            if isinstance(w, dict):
                sections.append(f"- {w.get('title', '')}：{w.get('description', '')} [{w.get('level', '')}]")

    # Template prescriptions (for reference)
    templates = structured_result.get("intervention_prescriptions", [])
    template_str = json.dumps(templates, ensure_ascii=False, indent=2) if templates else "[]"

    data_context = "\n".join(sections)

    prompt = f"""请根据以下患者的健康评估数据，制定个性化的干预处方。

{data_context}

## 要求

1. 处方必须基于患者实际健康状况，不可泛泛而谈
2. 饮食处方要考虑患者的疾病禁忌（如糖尿病患者控糖、高血压患者控盐）
3. 运动处方要考虑患者的身体承受能力，有心血管风险的患者避免剧烈运动
4. 睡眠处方要结合患者的年龄和作息习惯
5. 每个处方都要具体可操作，避免模糊建议
6. 按严重程度调整优先级：高危→high，中危→medium，低危→low
7. 没有相关异常的处方类型可以省略

## 输出格式

严格输出以下JSON（不要包含其他文字）：

```json
{{
  "intervention_prescriptions": [
    {{
      "type": "diet/exercise/sleep",
      "title": "处方标题",
      "content": ["具体建议1", "具体建议2", "具体建议3"],
      "priority": "high/medium/low",
      "evidence": "循证依据，引用权威指南或研究（如《中国2型糖尿病防治指南》、《中国居民膳食指南》等），说明该处方的权威来源",
      "confidence": 0.80
    }}
  ]
}}
```

## 约束

- type 范围：diet / exercise / sleep
- priority 范围：high / medium / low
- 每类处方 2-4 条具体建议
- 不要包含 medication 类型（药物建议由医生给出）

## 关于循证和置信度

- evidence：必须引用权威来源，如国家临床指南、中华医学会共识、WHO建议、大型队列研究等。不要引用非权威来源。
- confidence：0到1之间，保留两位小数。数据充分且指南明确→0.80以上；数据部分缺失→0.50-0.80；数据严重不足→0.30以下。

## 参考模板处方（仅作参考，需要个性化和增强）

{template_str}
"""

    # Inject Wiki RAG context
    wiki_ctx = _get_wiki_context("prescription-recommendation", health_data)
    if wiki_ctx:
        prompt += f"""

## 参考指南摘要（基于权威医学指南提取）

{wiki_ctx}

请根据以上参考指南摘要，结合患者实际数据，生成循证建议。引用时请注明具体指南名称和章节。"""

    return prompt


async def generate_intervention_prescriptions(
    structured_result: Dict[str, Any],
    health_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate intervention_prescriptions via LLM prescription-recommendation skill.

    Returns a list of prescription dicts, or the original prescriptions on failure.
    """
    fallback = structured_result.get("intervention_prescriptions", [])
    if not isinstance(fallback, list):
        fallback = []

    # Skip if there's nothing to base prescriptions on
    if not structured_result.get("population_classification", {}).get("primary_category"):
        logger.debug("No population classification found, skipping LLM prescription generation")
        return fallback

    prompt = _build_prescription_prompt(structured_result, health_data)
    try:
        text = await _call_llm(_PRESCRIPTION_SYSTEM, prompt)
        parsed = _extract_json(text)
        if parsed and isinstance(parsed.get("intervention_prescriptions"), list):
            prescriptions = _validate_prescriptions(parsed["intervention_prescriptions"])
            if prescriptions:
                logger.info(f"LLM generated {len(prescriptions)} intervention prescriptions")
                return prescriptions
        logger.warning("LLM returned empty/invalid prescriptions, using fallback")
    except Exception as e:
        logger.warning(f"LLM prescription generation failed: {e}")

    return fallback


def _validate_prescriptions(prescriptions: list) -> list:
    """Validate and normalise prescription items."""
    _VALID_TYPES = {"diet", "exercise", "sleep"}
    _VALID_PRIORITIES = {"high", "medium", "low"}
    _DEFAULT_TITLES = {
        "diet": "饮食处方",
        "exercise": "运动处方",
        "sleep": "睡眠处方",
    }

    result = []
    for p in prescriptions:
        if not isinstance(p, dict):
            continue
        ptype = p.get("type", "")
        if ptype not in _VALID_TYPES:
            continue
        priority = str(p.get("priority", "medium")).lower()
        if priority not in _VALID_PRIORITIES:
            priority = "medium"
        content = p.get("content", [])
        if isinstance(content, str):
            content = [content]
        if not isinstance(content, list) or not content:
            continue
        # Normalise confidence to [0, 1] with 2 decimal places
        confidence = p.get("confidence", 0.70)
        try:
            confidence = round(float(confidence), 2)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.70
        result.append({
            "type": ptype,
            "title": p.get("title", _DEFAULT_TITLES.get(ptype, ptype)),
            "content": content,
            "priority": priority,
            "evidence": p.get("evidence", ""),
            "confidence": confidence,
        })
    return result


# ---------------------------------------------------------------------------
# Data Recommendation Skill (Progressive)
# ---------------------------------------------------------------------------

_DATA_RECOMMENDATION_SYSTEM = (
    "你是一位专业的健康数据分析师。根据患者的人群分组、疾病史、已有异常指标和风险评估结果，"
    "对缺失的检查指标进行优先级排序，生成个性化的渐进式数据推荐。"
    "严格按照要求的JSON格式输出，不要包含其他文字。"
)


def _build_data_recommendation_prompt(
    raw_items: List[Dict[str, Any]],
    structured_result: Dict[str, Any],
    health_data: Dict[str, Any],
) -> str:
    """Build the user prompt for the data-recommendation skill."""
    pop = structured_result.get("population_classification", {})
    if isinstance(pop, str):
        try:
            pop = json.loads(pop)
        except (json.JSONDecodeError, TypeError):
            pop = {}
    if not isinstance(pop, dict):
        pop = {}
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

    # Patient info
    age = health_data.get("age", "未知")
    gender = health_data.get("gender", "未知")
    gender_zh = "男" if gender in ("male", "男", "M") else "女" if gender in ("female", "女", "F") else str(gender)
    sport_target = health_data.get("sport_target", "")
    disease_labels = health_data.get("disease_labels", [])
    if isinstance(disease_labels, str):
        disease_labels = [disease_labels]

    sections = []
    sections.append(f"## 患者基本信息\n- 年龄：{age}\n- 性别：{gender_zh}")
    if sport_target:
        sections.append(f"- 健康目标：{sport_target}")
    if disease_labels:
        sections.append(f"- 已确诊疾病：{', '.join(disease_labels)}")

    sections.append(f"## 健康人群分组\n- 分组：{category}")
    grouping_basis = pop.get("grouping_basis", [])
    for b in grouping_basis:
        if isinstance(b, dict):
            sections.append(f"  - {b.get('disease', '')}：{b.get('note', b.get('level', ''))}")

    if indicators:
        sections.append("## 已有异常指标")
        for ind in indicators[:15]:
            if isinstance(ind, dict):
                name = ind.get("name", "")
                value = ind.get("value", "")
                unit = ind.get("unit", "")
                severity = ind.get("severity", "")
                line = f"- {name}：{value} {unit}".strip()
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
        sections.append("## 风险提醒")
        for w in warnings[:5]:
            if isinstance(w, dict):
                sections.append(f"- {w.get('title', '')}：{w.get('description', '')} [{w.get('level', '')}]")

    # Raw missing items
    raw_items_str = json.dumps(
        [{"item": r.get("item", ""), "reason": r.get("reason", "")} for r in raw_items],
        ensure_ascii=False, indent=2,
    )
    sections.append(f"## 缺失指标列表（原始，需排序和个性化）\n{raw_items_str}")

    data_context = "\n".join(sections)

    prompt = f"""请根据以下患者的健康评估数据，对缺失的检查指标进行优先级排序和个性化推荐。

{data_context}

## 要求

1. 根据患者的人群分组和疾病史，判断哪些缺失指标对该患者最为关键
2. 结合已有异常指标和风险预测，评估缺失指标的临床紧迫性
3. 为每个指标分配优先级：critical（必须尽快补充）、important（建议近期补充）、optional（后续随访补充）
4. 为每个指标生成个性化的推荐理由，说明为什么这个指标对这个特定患者重要
5. 按优先级排序输出：critical → important → optional

## 优先级判定原则

- 慢病/重症患者：与已确诊疾病直接相关的指标 → critical
- 已有异常指标涉及某系统：该系统的其他关联指标 → critical
- 疾病风险预测为高危：相关风险指标 → critical
- 年龄>60岁：心血管相关指标优先级提升
- 健康人群：基础体检指标 → important，专项指标 → optional

## 输出格式

严格输出以下JSON（不要包含其他文字）：

```json
{{"recommended_data_collection": [{{"item": "指标中文名称", "reason": "个性化推荐理由", "priority": "critical/important/optional"}}]}}
```

## 注意事项

- 推荐理由必须个性化，不能是通用的"缺少X数据，建议补充检测"
- 优先级判定要基于临床逻辑，不要过度推荐
- 如果无缺失指标，返回空数组
- 不要编造患者没有的疾病或症状"""
    return prompt


async def generate_data_recommendations(
    raw_items: List[Dict[str, Any]],
    structured_result: Dict[str, Any],
    health_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate progressive data recommendations via LLM data-recommendation skill.

    Takes raw missing-item list, ranks and personalises via LLM.
    Returns ranked list, or raw_items on failure.
    """
    if not raw_items:
        return []

    # Ensure structured_result is a dict
    if isinstance(structured_result, str):
        try:
            structured_result = json.loads(structured_result)
        except (json.JSONDecodeError, TypeError):
            structured_result = {}
    if not isinstance(structured_result, dict):
        structured_result = {}

    # Skip if there's nothing to base recommendations on
    pop_class = structured_result.get("population_classification", {})
    if isinstance(pop_class, str):
        try:
            pop_class = json.loads(pop_class)
        except (json.JSONDecodeError, TypeError):
            pop_class = {}
    if not isinstance(pop_class, dict) or not pop_class.get("primary_category"):
        logger.debug("No population classification found, skipping LLM data recommendation")
        return raw_items

    prompt = _build_data_recommendation_prompt(raw_items, structured_result, health_data)
    try:
        text = await _call_llm(_DATA_RECOMMENDATION_SYSTEM, prompt)
        parsed = _extract_json(text)
        if parsed and isinstance(parsed.get("recommended_data_collection"), list):
            recommendations = _validate_data_recommendations(parsed["recommended_data_collection"])
            if recommendations:
                logger.info(f"LLM generated {len(recommendations)} data recommendations")
                return recommendations
        logger.warning("LLM returned empty/invalid data recommendations, using raw items")
    except Exception as e:
        logger.warning(f"LLM data recommendation generation failed: {e}")

    return raw_items


def _validate_data_recommendations(items: list) -> list:
    """Validate and normalise data recommendation items."""
    _VALID_PRIORITIES = {"critical", "important", "optional"}
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority", "important")).lower()
        if priority not in _VALID_PRIORITIES:
            priority = "important"
        item_name = item.get("item", "")
        if not item_name:
            continue
        reason = item.get("reason", "")
        if not reason or (reason.startswith("缺少") and reason.endswith("建议补充检测")):
            reason = f"建议补充{item_name}检测以完善健康评估"
        result.append({
            "item": item_name,
            "reason": reason,
            "priority": priority,
        })
    # Sort: critical first, then important, then optional
    _ORDER = {"critical": 0, "important": 1, "optional": 2}
    result.sort(key=lambda x: _ORDER.get(x["priority"], 1))
    return result
