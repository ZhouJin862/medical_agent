"""
Model-based Skill Discovery and Matching.

Uses LLM to intelligently match user queries to available skills
based on their SKILL.md name and description, replacing keyword-based matching.

This approach provides:
1. Flexible intent understanding - no rigid keyword patterns
2. Better handling of ambiguous queries
3. Automatic skill discovery from SKILL.md files
4. SKILL.md as single source of truth
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .state import IntentType

logger = logging.getLogger(__name__)


class SkillMatch(str, Enum):
    """Skill match result with confidence."""
    CVD_RISK = "cvd-risk-assessment"
    HYPERGLYCEMIA_RISK = "hyperglycemia-risk-assessment"
    HYPERLIPIDEMIA_RISK = "hyperlipidemia-risk-assessment"
    HYPERTENSION_RISK = "hypertension-risk-assessment"
    HYPERURICEMIA_RISK = "hyperuricemia-risk-assessment"
    OBESITY_RISK = "obesity-risk-assessment"


@dataclass
class SkillInfo:
    """Information about an available skill."""
    name: str
    description: str
    keywords: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class SkillMatchResult:
    """Result of skill matching."""
    skill_name: Optional[str]
    intent: IntentType
    confidence: float
    reasoning: str = ""


# Available skills registry - loaded from SKILL.md files
_AVAILABLE_SKILLS: Dict[str, SkillInfo] = {
    "cvd-risk-assessment": SkillInfo(
        name="cvd-risk-assessment",
        description="心血管病风险评估、心血管风险评估、CVD风险、心血管病一级预防、心脏病风险评估、中风风险评估、Chinese adult cardiovascular disease primary prevention risk assessment. Use when Claude needs to: (1) Assess cardiovascular risk level for Chinese adults (评估心血管风险等级), (2) Provide lifestyle and medical intervention recommendations (提供生活方式和药物干预建议), (3) Generate health insights and expert summaries (生成健康洞察和专家综述), (4) Handle both interactive Q&A and structured patient data input",
        keywords=[
            "心血管", "心脏病", "中风", "风险评估", "危险分层", "健康评估", "CVD", "心血管病", "心血管疾病",
            # English keywords
            "cardiovascular", "heart disease", "stroke", "cvd", "risk assessment", "primary prevention"
        ]
    ),
    "hyperglycemia-risk-assessment": SkillInfo(
        name="hyperglycemia-risk-assessment",
        description="高血糖风险评估；用于糖尿病前期筛查、血糖异常分析、糖耐量受损评估、糖尿病风险预测",
        keywords=[
            "高血糖", "糖尿病", "血糖", "糖耐量", "空腹血糖", "糖化血红蛋白",
            # English keywords
            "hyperglycemia", "diabetes", "blood sugar", "glucose", "hba1c", "prediabetes"
        ]
    ),
    "hyperlipidemia-risk-assessment": SkillInfo(
        name="hyperlipidemia-risk-assessment",
        description="高血脂风险评估；用于血脂异常分析、胆固醇评估、动脉粥样硬化风险预测",
        keywords=[
            "高血脂", "胆固醇", "甘油三酯", "血脂", "LDL", "HDL", "动脉粥样硬化",
            # English keywords
            "hyperlipidemia", "cholesterol", "triglycerides", "lipid", "ldl", "hdl", "atherosclerosis"
        ]
    ),
    "hypertension-risk-assessment": SkillInfo(
        name="hypertension-risk-assessment",
        description="高血压风险评估；用于血压异常分析、高血压分级、心血管风险评估",
        keywords=[
            "高血压", "血压", "收缩压", "舒张压", "心血管",
            # English keywords
            "hypertension", "blood pressure", "systolic", "diastolic", "cardiovascular"
        ]
    ),
    "hyperuricemia-risk-assessment": SkillInfo(
        name="hyperuricemia-risk-assessment",
        description="高尿酸风险评估；用于尿酸异常分析、痛风风险预测、肾脏功能评估",
        keywords=[
            "高尿酸", "尿酸", "痛风", "嘌呤", "肾脏",
            # English keywords
            "hyperuricemia", "uric acid", "gout", "purine", "kidney"
        ]
    ),
    "obesity-risk-assessment": SkillInfo(
        name="obesity-risk-assessment",
        description="肥胖风险评估；用于体重管理、BMI分析、体脂率评估、代谢综合征预测",
        keywords=[
            "肥胖", "体重", "BMI", "体脂", "超重", "代谢综合征",
            # English keywords
            "obesity", "weight", "bmi", "body fat", "overweight", "metabolic syndrome"
        ]
    ),
}


async def discover_skills_from_directory(skills_dir: str = "skills") -> Dict[str, SkillInfo]:
    """
    Auto-discover skills from the skills directory.

    Reads SKILL.md files and extracts name and description from frontmatter.

    Args:
        skills_dir: Path to skills directory

    Returns:
        Dictionary mapping skill names to SkillInfo
    """
    from pathlib import Path
    import yaml

    skills_path = Path(skills_dir)
    if not skills_path.exists():
        logger.warning(f"Skills directory not found: {skills_dir}")
        return _AVAILABLE_SKILLS  # Return fallback registry

    discovered = {}

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse YAML frontmatter
            frontmatter = None
            if content.startswith('---'):
                end = content.find('---', 3)
                if end != -1:
                    frontmatter_str = content[3:end].strip()
                    try:
                        frontmatter = yaml.safe_load(frontmatter_str)
                    except yaml.YAMLError:
                        pass

            if frontmatter and 'name' in frontmatter and 'description' in frontmatter:
                skill_name = frontmatter['name']

                # Get keywords from frontmatter tags, or use fallback from registry
                keywords = frontmatter.get('tags', [])
                if not keywords and skill_name in _AVAILABLE_SKILLS:
                    keywords = _AVAILABLE_SKILLS[skill_name].keywords

                discovered[skill_name] = SkillInfo(
                    name=skill_name,
                    description=frontmatter['description'],
                    keywords=keywords
                )
                logger.debug(f"Discovered skill: {skill_name}")

        except Exception as e:
            logger.warning(f"Failed to load skill from {skill_dir}: {e}")

    logger.info(f"Discovered {len(discovered)} skills from {skills_dir}")
    return discovered if discovered else _AVAILABLE_SKILLS


async def match_skill_with_llm(
    user_input: str,
    available_skills: Dict[str, SkillInfo],
) -> SkillMatchResult:
    """
    Use LLM to intelligently match user query to the most relevant skill.

    This replaces keyword-based matching with semantic understanding.

    Args:
        user_input: User's query or message
        available_skills: Dictionary of available skills

    Returns:
        SkillMatchResult with matched skill, intent, and confidence
    """
    # Check for @skill_name syntax for direct invocation
    if user_input.strip().startswith("@"):
        parts = user_input.strip().split(maxsplit=1)
        skill_name = parts[0][1:]  # Remove @
        if skill_name in available_skills:
            logger.info(f"Direct skill invocation: @{skill_name}")
            return SkillMatchResult(
                skill_name=skill_name,
                intent=IntentType.HEALTH_ASSESSMENT,
                confidence=1.0,
                reasoning=f"Direct invocation via @{skill_name}"
            )

    # Build skills list for LLM
    skills_list = []
    for name, skill in available_skills.items():
        skills_list.append(f"- **{name}**: {skill.description}")

    skills_prompt = "\n".join(skills_list)

    # Create classification prompt (load from DB with fallback)
    from src.domain.shared.services.system_prompt_service import get_system_prompt_service
    prompt_service = get_system_prompt_service()
    system_prompt_template = await prompt_service.get_prompt_with_fallback(
        "skill_matcher_system",
        fallback="""你是一个技能路由专家，负责将用户查询匹配到最合适的健康评估技能。

## 可用技能

{{skills_prompt}}

## 任务

分析用户查询，返回最匹配的技能名称。

## 规则

1. **心血管相关优先**: 如果查询提到"心血管"、"心脏病"、"中风"、"CVD"、"cardiovascular"、"heart disease"、"stroke"等心血管相关术语，**必须**选择 "cvd-risk-assessment"（即使同时包含其他健康指标）
2. 如果查询明确提到某个具体的健康问题（如"高血压"、"糖尿病"、"血脂"等），选择对应的风险评估技能
3. 如果查询不属于任何健康评估范围，返回 "none"
4. 只返回技能名称或 "none"，不要有其他内容

## 示例

用户输入: "心血管风险评估"
输出: cvd-risk-assessment

用户输入: "我有高血压，想评估风险"
输出: hypertension-risk-assessment

用户输入: "今天天气怎么样"
输出: none""",
    )
    # Format template with skills_prompt
    try:
        system_prompt = system_prompt_template.format(skills_prompt=skills_prompt)
    except (KeyError, IndexError):
        system_prompt = system_prompt_template

    try:
        from src.config.settings import get_settings
        import anthropic

        settings = get_settings()
        if not settings.anthropic_api_key:
            logger.warning("No Anthropic API key, using keyword fallback")
            return _match_with_keywords(user_input, available_skills)

        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url if settings.anthropic_base_url != "https://api.anthropic.com" else None,
        )

        response = client.messages.create(
            model=settings.model,
            max_tokens=100,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
        )

        llm_output = response.content[0].text.strip().lower()
        logger.info(f"LLM skill match output: {llm_output}")

        # Parse LLM response
        if llm_output == "none" or llm_output == "general_chat":
            return SkillMatchResult(
                skill_name=None,
                intent=IntentType.GENERAL_CHAT,
                confidence=0.7,
                reasoning="LLM determined query is not health-related"
            )

        # Find matching skill
        matched_skill = None
        for skill_name in available_skills.keys():
            if skill_name in llm_output or llm_output in skill_name:
                matched_skill = skill_name
                break

        if matched_skill:
            # Determine intent based on skill
            intent = _skill_to_intent(matched_skill)
            return SkillMatchResult(
                skill_name=matched_skill,
                intent=intent,
                confidence=0.9,
                reasoning=f"LLM matched to {matched_skill}"
            )

        # LLM output didn't match any skill, use fallback
        logger.warning(f"LLM output didn't match any skill: {llm_output}")
        return _match_with_keywords(user_input, available_skills)

    except Exception as e:
        logger.error(f"LLM skill matching failed: {e}, using keyword fallback")
        return _match_with_keywords(user_input, available_skills)


def _match_with_keywords(
    user_input: str,
    available_skills: Dict[str, SkillInfo],
) -> SkillMatchResult:
    """
    Fallback keyword-based matching.

    Args:
        user_input: User's query
        available_skills: Available skills

    Returns:
        SkillMatchResult with best match
    """
    user_input_lower = user_input.lower()

    # Score each skill based on keyword matches
    best_skill = None
    best_score = 0

    for skill_name, skill_info in available_skills.items():
        score = 0

        # Check if skill name appears in input
        if skill_name.replace("-", "") in user_input_lower.replace("-", ""):
            score += 10

        # Check keywords
        for keyword in skill_info.keywords:
            if keyword.lower() in user_input_lower:
                score += 3

        if score > best_score:
            best_score = score
            best_skill = skill_name

    if best_skill and best_score > 0:
        intent = _skill_to_intent(best_skill)
        return SkillMatchResult(
            skill_name=best_skill,
            intent=intent,
            confidence=min(0.8, best_score / 10),
            reasoning=f"Keyword match (score: {best_score})"
        )

    # No match found
    return SkillMatchResult(
        skill_name=None,
        intent=IntentType.GENERAL_CHAT,
        confidence=0.3,
        reasoning="No keywords matched"
    )


def _skill_to_intent(skill_name: str) -> IntentType:
    """
    Map skill name to intent type.

    Args:
        skill_name: Name of the skill

    Returns:
        Corresponding IntentType
    """
    if "assessment" in skill_name or "risk" in skill_name:
        return IntentType.HEALTH_ASSESSMENT
    elif "prescription" in skill_name or "plan" in skill_name:
        return IntentType.HEALTH_PLAN
    elif "triage" in skill_name:
        return IntentType.TRIAGE
    elif "medication" in skill_name:
        return IntentType.MEDICATION_CHECK
    elif "service" in skill_name:
        return IntentType.SERVICE_RECOMMENDATION
    else:
        return IntentType.HEALTH_ASSESSMENT


# Global skills cache
_skills_cache: Dict[str, SkillInfo] = None


async def get_available_skills(refresh: bool = False) -> Dict[str, SkillInfo]:
    """
    Get available skills, with optional refresh.

    Args:
        refresh: Force refresh from disk

    Returns:
        Dictionary of available skills
    """
    global _skills_cache

    if _skills_cache is None or refresh:
        _skills_cache = await discover_skills_from_directory("skills")

    return _skills_cache
