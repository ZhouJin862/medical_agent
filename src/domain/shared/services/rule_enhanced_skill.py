"""
Rule-Enhanced Skill Service - Integrates skills with rule engine.

Allows skills to use rule-based evaluation to enhance their responses.
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.services.rule_engine import (
    RuleEngine,
    RuleExecutionContext,
    RuleEvaluationResult,
)
from src.infrastructure.persistence.models.skill_models import SkillModel

logger = logging.getLogger(__name__)


@dataclass
class RuleEnhancementConfig:
    """Configuration for rule enhancement in a skill."""
    enabled: bool = False
    categories: Optional[List[str]] = None
    disease_code: Optional[str] = None
    rule_ids: Optional[List[str]] = None
    use_vital_signs: bool = False
    use_risk_scoring: bool = False
    risk_diseases: Optional[List[str]] = None


@dataclass
class SkillRuleContext:
    """Context for skill execution with rule evaluation."""
    skill_id: str
    patient_id: str
    user_input: str
    extracted_data: Dict[str, Any]
    consultation_id: Optional[str] = None


@dataclass
class SkillRuleResult:
    """Result of skill execution with rule enhancement."""
    skill_response: str
    rule_results: List[RuleEvaluationResult]
    vital_signs_assessment: Optional[Dict[str, Any]] = None
    risk_scores: Optional[Dict[str, Any]] = None
    execution_summary: Optional[Dict[str, Any]] = None


class RuleEnhancedSkillService:
    """
    Service that integrates skills with rule evaluation.

    This allows skills to:
    1. Evaluate patient data against configured rules
    2. Get vital signs risk assessment
    3. Calculate disease risk scores
    4. Use rule results to enhance AI responses
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the rule-enhanced skill service.

        Args:
            session: Database session
        """
        self._session = session
        self._rule_engine = RuleEngine(session)

    async def execute_skill_with_rules(
        self,
        skill: SkillModel,
        context: SkillRuleContext,
        llm_generate_fn: callable,
    ) -> SkillRuleResult:
        """
        Execute a skill with rule evaluation.

        Args:
            skill: The skill to execute
            context: Execution context with patient data
            llm_generate_fn: Function to generate LLM response
                Signature: (prompt: str, context: dict) -> str

        Returns:
            Combined skill and rule evaluation results
        """
        # Parse rule enhancement config from skill metadata
        rule_config = self._parse_rule_config(skill)

        if not rule_config.enabled:
            # Execute skill without rules
            response = await llm_generate_fn(context.user_input, {})
            return SkillRuleResult(
                skill_response=response,
                rule_results=[],
            )

        # Step 1: Evaluate rules
        rule_results = []
        vital_signs_assessment = None
        risk_scores = None

        if rule_config.categories or rule_config.disease_code:
            rule_context = RuleExecutionContext(
                patient_id=context.patient_id,
                input_data=context.extracted_data,
                consultation_id=context.consultation_id,
                skill_id=skill.id,
            )
            rule_results = await self._rule_engine.evaluate_rules(
                rule_context,
                categories=rule_config.categories,
                disease_code=rule_config.disease_code,
            )

        # Step 2: Vital signs assessment
        if rule_config.use_vital_signs and context.extracted_data:
            vital_signs_assessment = await self._rule_engine.evaluate_vital_signs(
                patient_id=context.patient_id,
                vital_signs=context.extracted_data,
            )

        # Step 3: Risk scoring
        if rule_config.use_risk_scoring and rule_config.risk_diseases:
            risk_scores = {}
            for disease in rule_config.risk_diseases:
                score = await self._rule_engine.calculate_risk_score(
                    patient_id=context.patient_id,
                    disease_code=disease,
                    input_data=context.extracted_data,
                )
                risk_scores[disease] = score

        # Step 4: Generate enhanced prompt with rule results
        enhanced_prompt = self._build_enhanced_prompt(
            user_input=context.user_input,
            skill=skill,
            rule_results=rule_results,
            vital_signs_assessment=vital_signs_assessment,
            risk_scores=risk_scores,
        )

        # Step 5: Generate LLM response with enhanced context
        skill_response = await llm_generate_fn(
            enhanced_prompt,
            {
                "extracted_data": context.extracted_data,
                "rule_results": [asdict(r) for r in rule_results],
                "vital_signs_assessment": vital_signs_assessment,
                "risk_scores": risk_scores,
            }
        )

        # Step 6: Build execution summary
        execution_summary = self._build_execution_summary(
            rule_results, vital_signs_assessment, risk_scores
        )

        return SkillRuleResult(
            skill_response=skill_response,
            rule_results=rule_results,
            vital_signs_assessment=vital_signs_assessment,
            risk_scores=risk_scores,
            execution_summary=execution_summary,
        )

    def _parse_rule_config(self, skill: SkillModel) -> RuleEnhancementConfig:
        """Parse rule enhancement config from skill metadata."""
        if not skill.config or not isinstance(skill.config, dict):
            return RuleEnhancementConfig(enabled=False)

        rule_config_data = skill.config.get("rule_enhancement", {})
        return RuleEnhancementConfig(
            enabled=rule_config_data.get("enabled", False),
            categories=rule_config_data.get("categories"),
            disease_code=rule_config_data.get("disease_code"),
            rule_ids=rule_config_data.get("rule_ids"),
            use_vital_signs=rule_config_data.get("use_vital_signs", False),
            use_risk_scoring=rule_config_data.get("use_risk_scoring", False),
            risk_diseases=rule_config_data.get("risk_diseases"),
        )

    def _build_enhanced_prompt(
        self,
        user_input: str,
        skill: SkillModel,
        rule_results: List[RuleEvaluationResult],
        vital_signs_assessment: Optional[Dict[str, Any]],
        risk_scores: Optional[Dict[str, Any]],
    ) -> str:
        """Build enhanced prompt with rule evaluation results."""
        prompt_parts = [f"# User Input\n{user_input}\n"]

        # Add matched rules
        matched_rules = [r for r in rule_results if r.matched]
        if matched_rules:
            prompt_parts.append("# Matched Clinical Rules\n")
            for result in matched_rules:
                prompt_parts.append(f"- **{result.rule_name}** (confidence: {result.confidence:.2f})")
                if result.result:
                    details = ", ".join(f"{k}={v}" for k, v in result.result.items() if k != "matched")
                    if details:
                        prompt_parts.append(f"  - Details: {details}")
            prompt_parts.append("")

        # Add vital signs assessment
        if vital_signs_assessment:
            prompt_parts.append("# Vital Signs Assessment\n")
            for sign_name, assessment in vital_signs_assessment.items():
                risk_level = assessment.get("risk_level", "unknown")
                value = assessment.get("value", "N/A")
                unit = assessment.get("unit", "")
                emoji = self._get_risk_emoji(risk_level)
                prompt_parts.append(f"- {sign_name}: {value} {unit} {emoji} ({risk_level})")
            prompt_parts.append("")

        # Add risk scores
        if risk_scores:
            prompt_parts.append("# Risk Assessment\n")
            for disease, score_data in risk_scores.items():
                score = score_data.get("score", 0)
                level = score_data.get("risk_level", "unknown")
                emoji = self._get_risk_emoji(level)
                prompt_parts.append(f"- {disease}: Score {score:.2f} {emoji} ({level})")
            prompt_parts.append("")

        # Add system instructions
        prompt_parts.append("# Instructions\n")
        prompt_parts.append(
            "Based on the clinical rules and assessments above, "
            "provide a helpful, accurate response to the user. "
            "Consider the matched rules and risk levels when formulating your response. "
            "Be empathetic but medically accurate."
        )

        return "\n".join(prompt_parts)

    def _get_risk_emoji(self, risk_level: str) -> str:
        """Get emoji for risk level."""
        emoji_map = {
            "normal": "✅",
            "low": "🟢",
            "elevated": "🟡",
            "medium": "🟠",
            "high": "🔴",
            "very_high": "⚠️",
        }
        return emoji_map.get(risk_level.lower(), "⚪")

    def _build_execution_summary(
        self,
        rule_results: List[RuleEvaluationResult],
        vital_signs_assessment: Optional[Dict[str, Any]],
        risk_scores: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build execution summary for logging/tracking."""
        matched_rules = [r for r in rule_results if r.matched]
        abnormal_signs = []
        if vital_signs_assessment:
            abnormal_signs = [
                name for name, data in vital_signs_assessment.items()
                if data.get("risk_level") not in ["normal", "low"]
            ]

        high_risk_diseases = []
        if risk_scores:
            high_risk_diseases = [
                disease for disease, data in risk_scores.items()
                if data.get("risk_level") in ["high", "very_high"]
            ]

        return {
            "total_rules_evaluated": len(rule_results),
            "matched_rules": len(matched_rules),
            "abnormal_vital_signs": len(abnormal_signs),
            "high_risk_diseases": len(high_risk_diseases),
            "matched_rule_names": [r.rule_name for r in matched_rules],
            "abnormal_sign_names": abnormal_signs,
            "high_risk_disease_names": high_risk_diseases,
            "total_execution_time_ms": sum(r.execution_time_ms for r in rule_results),
        }


class RuleEnhancedSkillRepository:
    """Repository for rule-enhanced skill operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_rule_enhanced_skills(self) -> List[SkillModel]:
        """Get all skills that have rule enhancement enabled."""
        from sqlalchemy import select, func, cast
        from sqlalchemy.dialects.mysql import JSON

        # Query skills that have rule_enhancement enabled in their config
        # Use text() for JSON field comparison
        stmt = select(SkillModel).where(
            func.json_extract(
                SkillModel.config,
                '$.rule_enhancement.enabled'
            ) == 'true'
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_skill_rule_config(
        self,
        skill_id: str,
        rule_config: RuleEnhancementConfig,
    ) -> SkillModel:
        """Update skill's rule enhancement configuration."""
        from sqlalchemy import select

        stmt = select(SkillModel).where(SkillModel.id == skill_id)
        result = await self._session.execute(stmt)
        skill = result.scalar_one_or_none()

        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        # Update config with rule config
        from sqlalchemy.orm.attributes import flag_modified

        # Get existing config or create new
        if skill.config:
            config = dict(skill.config) if not isinstance(skill.config, dict) else skill.config.copy()
        else:
            config = {}

        # Add rule_enhancement config
        config["rule_enhancement"] = {
            "enabled": rule_config.enabled,
            "categories": rule_config.categories,
            "disease_code": rule_config.disease_code,
            "rule_ids": rule_config.rule_ids,
            "use_vital_signs": rule_config.use_vital_signs,
            "use_risk_scoring": rule_config.use_risk_scoring,
            "risk_diseases": rule_config.risk_diseases,
        }

        # Replace the entire config to ensure SQLAlchemy tracks the change
        skill.config = config

        await self._session.commit()
        await self._session.refresh(skill)
        return skill
