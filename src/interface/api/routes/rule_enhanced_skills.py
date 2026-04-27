"""
Rule-Enhanced Skills API routes.

Provides endpoints for managing skills with rule evaluation integration.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.domain.shared.services.rule_enhanced_skill import (
    RuleEnhancedSkillService,
    RuleEnhancedSkillRepository,
    RuleEnhancementConfig,
)
from src.infrastructure.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["rule-enhanced-skills"])


# Request/Response Schemas
class RuleEnhancementConfigSchema(BaseModel):
    """Schema for rule enhancement configuration."""
    enabled: bool = Field(default=False, description="Enable rule evaluation for this skill")
    categories: Optional[List[str]] = Field(None, description="Rule categories to evaluate")
    disease_code: Optional[str] = Field(None, description="Filter by disease code")
    rule_ids: Optional[List[str]] = Field(None, description="Specific rule IDs to evaluate")
    use_vital_signs: bool = Field(default=False, description="Evaluate vital signs")
    use_risk_scoring: bool = Field(default=False, description="Calculate risk scores")
    risk_diseases: Optional[List[str]] = Field(None, description="Diseases for risk scoring")


class SkillRuleConfigUpdateRequest(BaseModel):
    """Request schema for updating skill rule config."""
    rule_enhancement: RuleEnhancementConfigSchema


class SkillEvaluationRequest(BaseModel):
    """Request schema for evaluating a skill with rules."""
    patient_id: str = Field(..., description="Patient ID")
    user_input: str = Field(..., description="User input text")
    extracted_data: Dict[str, Any] = Field(default={}, description="Extracted clinical data")
    consultation_id: Optional[str] = Field(None, description="Consultation ID")


class SkillEvaluationResponse(BaseModel):
    """Response schema for skill evaluation with rules."""
    skill_response: str
    rule_results: List[Dict[str, Any]]
    vital_signs_assessment: Optional[Dict[str, Any]] = None
    risk_scores: Optional[Dict[str, Any]] = None
    execution_summary: Optional[Dict[str, Any]] = None


# Dependencies
async def get_rule_enhanced_skill_service(
    db: AsyncSession = Depends(get_db_session),
) -> RuleEnhancedSkillService:
    """Get rule-enhanced skill service."""
    return RuleEnhancedSkillService(db)


async def get_rule_enhanced_skill_repository(
    db: AsyncSession = Depends(get_db_session),
) -> RuleEnhancedSkillRepository:
    """Get rule-enhanced skill repository."""
    return RuleEnhancedSkillRepository(db)


@router.get("/rule-enhanced", response_model=List[Dict])
async def list_rule_enhanced_skills(
    repo: RuleEnhancedSkillRepository = Depends(get_rule_enhanced_skill_repository),
) -> List[Dict]:
    """
    List all skills with rule enhancement enabled.

    Returns skills that have been configured to use rule evaluation.
    """
    skills = await repo.get_rule_enhanced_skills()

    return [
        {
            "id": skill.id,
            "name": skill.name,
            "display_name": skill.display_name,
            "description": skill.description,
            "skill_type": skill.skill_type,
            "rule_enhancement": dict(skill.config).get("rule_enhancement", {}) if skill.config else {},
        }
        for skill in skills
    ]


@router.put("/{skill_id}/rule-config", response_model=Dict)
async def update_skill_rule_config(
    skill_id: str,
    request: SkillRuleConfigUpdateRequest,
    repo: RuleEnhancedSkillRepository = Depends(get_rule_enhanced_skill_repository),
) -> Dict:
    """
    Update rule enhancement configuration for a skill.

    Enables or disables rule evaluation for the specified skill.
    """
    config = RuleEnhancementConfig(
        enabled=request.rule_enhancement.enabled,
        categories=request.rule_enhancement.categories,
        disease_code=request.rule_enhancement.disease_code,
        rule_ids=request.rule_enhancement.rule_ids,
        use_vital_signs=request.rule_enhancement.use_vital_signs,
        use_risk_scoring=request.rule_enhancement.use_risk_scoring,
        risk_diseases=request.rule_enhancement.risk_diseases,
    )

    skill = await repo.update_skill_rule_config(skill_id, config)

    # Debug logging
    logger.info(f"Updated skill {skill_id}, config type: {type(skill.config)}, config: {skill.config}")

    # Get the rule_enhancement config safely
    rule_enhancement = {}
    if skill.config:
        if isinstance(skill.config, dict):
            rule_enhancement = skill.config.get("rule_enhancement", {})
        else:
            # If it's a JSON object from the database, convert to dict
            rule_enhancement = dict(skill.config).get("rule_enhancement", {})

    logger.info(f"Returning rule_enhancement: {rule_enhancement}")

    return {
        "id": skill.id,
        "name": skill.name,
        "display_name": skill.display_name,
        "rule_enhancement": rule_enhancement,
    }


@router.post("/{skill_id}/evaluate-with-rules", response_model=SkillEvaluationResponse)
async def evaluate_skill_with_rules(
    skill_id: str,
    request: SkillEvaluationRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SkillEvaluationResponse:
    """
    Evaluate a skill with rule enhancement.

    This endpoint processes user input through the skill while
    also evaluating relevant clinical rules.

    Note: This is a simplified version. In production, integrate
    with the actual LLM service for response generation.
    """
    from sqlalchemy import select
    from src.infrastructure.persistence.models.skill_models import SkillModel

    # Load the skill
    stmt = select(SkillModel).where(SkillModel.id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill not found: {skill_id}"
        )

    # Create service
    service = RuleEnhancedSkillService(db)

    # Import a simple LLM generator for demonstration
    # In production, this would use the actual LLM service
    async def mock_llm_generator(prompt: str, context: Dict) -> str:
        """Mock LLM generator for demonstration."""
        # This would be replaced with actual LLM call
        return f"Based on the clinical assessment, here's my response to: {request.user_input}"

    # Execute skill with rules
    from src.domain.shared.services.rule_enhanced_skill import SkillRuleContext, SkillRuleResult

    context = SkillRuleContext(
        skill_id=skill_id,
        patient_id=request.patient_id,
        user_input=request.user_input,
        extracted_data=request.extracted_data,
        consultation_id=request.consultation_id,
    )

    result: SkillRuleResult = await service.execute_skill_with_rules(
        skill=skill,
        context=context,
        llm_generate_fn=mock_llm_generator,
    )

    return SkillEvaluationResponse(
        skill_response=result.skill_response,
        rule_results=[r.__dict__ for r in result.rule_results],
        vital_signs_assessment=result.vital_signs_assessment,
        risk_scores=result.risk_scores,
        execution_summary=result.execution_summary,
    )


@router.get("/rule-enhancement/categories", response_model=List[str])
async def list_rule_categories() -> List[str]:
    """List available rule categories for skill configuration."""
    return [
        "diagnosis",
        "risk_assessment",
        "prescription",
        "reference_value",
    ]


@router.get("/rule-enhancement/diseases", response_model=Dict[str, str])
async def list_supported_diseases() -> Dict[str, str]:
    """List supported diseases for risk scoring."""
    return {
        "hypertension": "高血压",
        "diabetes": "糖尿病",
        "dyslipidemia": "血脂异常",
        "gout": "痛风",
        "obesity": "肥胖",
        "metabolic_syndrome": "代谢综合征",
    }
