#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goal Recommender - LLM-based health goal recommendation.

Reads population classification, abnormal indicators, symptoms, and a goal pool,
then uses LLM to recommend 3-4 most suitable goals.
Falls back to rule-based recommendation if LLM fails.
"""
import argparse
import json
import logging
import sys
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback recommendations by population category
_FALLBACK_MAP = {
    "重症": ["improveDiet", "exercise", "improveSleep", "relax"],
    "慢病": ["improveDiet", "exercise", "improveSleep"],
    "亚健康": ["exercise", "improvePhysique", "relax"],
    "健康": ["exercise", "strengthTraining", "improvePhysique"],
}

# High-intensity goals not recommended for severe patients
_HIGH_INTENSITY_GOALS = {"strengthTraining"}


def _build_prompt(
    population: Dict[str, Any],
    abnormal_indicators: Dict[str, Any],
    disease_prediction: List[Dict],
    symptoms: List,
    goal_pool: List[Dict],
) -> str:
    """Build LLM prompt for goal recommendation."""
    category = population.get("primary_category", "健康")
    grouping = population.get("grouping_basis", [])

    indicators = abnormal_indicators.get("indicators", []) if isinstance(abnormal_indicators, dict) else []
    indicator_summary = []
    for ind in indicators[:10]:
        if isinstance(ind, dict):
            name = ind.get("name") or ind.get("indicator", "")
            value = ind.get("value", "")
            indicator_summary.append(f"{name}: {value}")

    disease_summary = []
    for d in (disease_prediction or [])[:8]:
        if isinstance(d, dict):
            disease_summary.append(f"{d.get('disease', '')}({d.get('risk', '')})")

    goal_list_str = "\n".join(
        f"  - {g['value']}: {g['label']}" for g in goal_pool
    )

    symptom_str = ", ".join(symptoms) if symptoms else "无"

    return f"""你是一个健康管理目标推荐助手。

## 用户健康数据
- 人群分类: {category}
- 分组依据: {json.dumps(grouping, ensure_ascii=False)}
- 异常指标: {', '.join(indicator_summary)}
- 疾病风险: {', '.join(disease_summary)}
- 症状: {symptom_str}

## 可选目标列表
{goal_list_str}

## 任务
从上述目标列表中选择 3-4 个最适合该用户的健康目标。

## 约束
1. 只能从可选目标列表中选择，使用 value 字段值
2. 必须返回 3 到 4 个目标，不能多也不能少
3. 重症/高危人群不要推荐高强度运动目标（如力量训练）
4. 每个目标需要给出简短推荐理由（一句话）
5. 按推荐优先级排序，最需要的排在前面

## 输出格式（严格 JSON，不要输出其他内容）
{{"goals": [{{"value": "xxx", "reason": "推荐理由"}}]}}"""


def _call_llm(prompt: str) -> str:
    """Call LLM with prompt and return response text."""
    try:
        from src.config.settings import get_settings
        import anthropic

        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model=settings.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return ""


def _parse_llm_response(text: str, goal_pool: List[Dict]) -> List[Dict]:
    """Parse LLM JSON response and validate against goal pool."""
    # Extract JSON from response
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse LLM response as JSON: {text[:200]}")
        return []

    goals_raw = data.get("goals", [])
    if not isinstance(goals_raw, list):
        return []

    # Validate: each goal value must exist in goal_pool
    pool_by_value = {g["value"]: g for g in goal_pool}
    validated = []
    for g in goals_raw:
        if not isinstance(g, dict):
            continue
        value = g.get("value", "")
        if value in pool_by_value:
            entry = dict(pool_by_value[value])
            entry["reason"] = g.get("reason", "")
            validated.append(entry)

    # Check count constraint (3-4)
    if len(validated) < 3 or len(validated) > 4:
        logger.warning(f"LLM returned {len(validated)} goals (need 3-4), using fallback")
        return []

    return validated


def _fallback_recommend(
    population: Dict[str, Any],
    goal_pool: List[Dict],
) -> List[Dict]:
    """Rule-based fallback recommendation."""
    category = population.get("primary_category", "健康")
    pool_by_value = {g["value"]: g for g in goal_pool}

    # Get fallback values for category
    fallback_values = _FALLBACK_MAP.get(category, _FALLBACK_MAP["健康"])

    # For severe patients, filter out high-intensity goals
    if category == "重症":
        fallback_values = [v for v in fallback_values if v not in _HIGH_INTENSITY_GOALS]

    result = []
    for value in fallback_values[:4]:
        if value in pool_by_value:
            entry = dict(pool_by_value[value])
            entry["reason"] = f"根据{category}人群推荐"
            result.append(entry)

    # Pad if less than 3
    if len(result) < 3:
        for g in goal_pool:
            if g["value"] not in {r["value"] for r in result}:
                entry = dict(g)
                entry["reason"] = f"根据{category}人群推荐"
                result.append(entry)
                if len(result) >= 3:
                    break

    return result[:4]


def recommend_goals(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry: recommend 3-4 goals from goal pool using LLM + fallback."""
    population = input_data.get("population_classification", {})
    abnormal_indicators = input_data.get("abnormal_indicators", {})
    disease_prediction = input_data.get("disease_prediction", [])
    symptoms = input_data.get("symptoms", [])
    goal_pool = input_data.get("goal_pool", [])

    if not goal_pool:
        return {
            "success": False,
            "error": "No goal pool provided",
            "recommended_goals": [],
        }

    # Try LLM first
    prompt = _build_prompt(population, abnormal_indicators, disease_prediction, symptoms, goal_pool)
    llm_response = _call_llm(prompt)

    if llm_response:
        goals = _parse_llm_response(llm_response, goal_pool)
        if goals:
            logger.info(f"LLM recommended {len(goals)} goals: {[g['value'] for g in goals]}")
            return {
                "success": True,
                "recommended_goals": goals,
            }

    # Fallback
    logger.info("Using fallback goal recommendation")
    goals = _fallback_recommend(population, goal_pool)
    return {
        "success": True,
        "recommended_goals": goals,
        "fallback": True,
    }


def main():
    parser = argparse.ArgumentParser(description="Goal Recommender")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--mode", default="skill", help="Execution mode")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    result = recommend_goals(input_data)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
