"""
Rule Management API routes.

Provides endpoints for rule CRUD operations and execution.
"""
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.domain.shared.services.rule_engine import (
    RuleEngine,
    RuleRepository,
    RuleExecutionContext,
)
from src.infrastructure.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rules", tags=["rules"])


# Request/Response Schemas
class RuleConfigSchema(BaseModel):
    """Schema for rule configuration."""
    field: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    conditions: Optional[List[dict]] = None
    logic: Optional[str] = "AND"
    factors: Optional[List[dict]] = None
    score_threshold: Optional[float] = None
    confidence: Optional[float] = None


class RuleCreateRequest(BaseModel):
    """Request schema for creating a rule."""
    name: str = Field(..., description="Unique rule name")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Rule description")
    rule_type: str = Field(..., description="Rule type: threshold, range, score, condition")
    category: str = Field(..., description="Rule category")
    target_type: str = Field(default="vital_sign", description="Target type")
    disease_code: Optional[str] = Field(None, description="Associated disease code")
    priority: int = Field(default=0, description="Evaluation priority")
    enabled: bool = Field(default=True, description="Enable rule")
    rule_config: RuleConfigSchema = Field(..., description="Rule configuration")


class RuleUpdateRequest(BaseModel):
    """Request schema for updating a rule."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    rule_config: Optional[RuleConfigSchema] = None


class RuleEvaluateRequest(BaseModel):
    """Request schema for evaluating rules."""
    patient_id: str = Field(..., description="Patient ID")
    input_data: dict = Field(..., description="Input data for rule evaluation")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    disease_code: Optional[str] = Field(None, description="Filter by disease code")


class VitalSignEvaluateRequest(BaseModel):
    """Request schema for vital sign evaluation."""
    patient_id: str = Field(..., description="Patient ID")
    vital_signs: dict = Field(..., description="Vital sign values")
    gender: Optional[str] = Field("male", description="Patient gender")
    age: Optional[int] = Field(None, description="Patient age")


class RiskScoreRequest(BaseModel):
    """Request schema for risk score calculation."""
    patient_id: str = Field(..., description="Patient ID")
    disease_code: str = Field(..., description="Disease code")
    input_data: dict = Field(..., description="Risk factor values")


class RuleResponse(BaseModel):
    """Response schema for rule data."""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    rule_type: str
    category: str
    target_type: str
    disease_code: Optional[str]
    priority: int
    enabled: bool
    version: str
    rule_config: dict
    created_at: str
    updated_at: str


class PaginatedResponse(BaseModel):
    """Schema for paginated response."""
    items: List[RuleResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class RuleListResponse(BaseModel):
    """Response schema for rule list (deprecated, use PaginatedResponse)."""
    rules: List[RuleResponse]
    total_count: int


# Dependencies
async def get_rule_repository(
    db: AsyncSession = Depends(get_db_session),
) -> RuleRepository:
    """Get rule repository."""
    return RuleRepository(db)


@router.get("")
async def list_rules(
    category: Optional[str] = None,
    disease_code: Optional[str] = None,
    enabled_only: bool = True,
    page: int = 1,
    page_size: int = 10,
    repo: RuleRepository = Depends(get_rule_repository),
):
    """
    List rules with optional filtering and pagination.

    Args:
        category: Filter by category
        disease_code: Filter by disease code
        enabled_only: Only return enabled rules
        page: Page number (1-indexed)
        page_size: Number of items per page
        repo: Rule repository

    Returns:
        Paginated list of rules
    """
    # Validate page parameters
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 100"
        )

    rules, total_count = await repo.list_rules(
        category=category,
        disease_code=disease_code,
        enabled_only=enabled_only,
        page=page,
        page_size=page_size,
    )

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    return {
        "items": [rule.to_dict() for rule in rules],
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    repo: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Get a rule by ID.

    Args:
        rule_id: Rule identifier
        repo: Rule repository

    Returns:
        Rule data
    """
    rule = await repo.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )

    return RuleResponse(**rule.to_dict())


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: RuleCreateRequest,
    repo: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Create a new rule.

    Args:
        request: Rule creation request
        repo: Rule repository

    Returns:
        Created rule data
    """
    rule_data = request.model_dump()
    rule_data["rule_config"] = request.rule_config.model_dump()

    try:
        rule = await repo.create_rule(rule_data)
        return RuleResponse(**rule.to_dict())
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rule with name '{request.name}' already exists"
            )
        raise


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    request: RuleUpdateRequest,
    repo: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Update an existing rule.

    Args:
        rule_id: Rule identifier
        request: Rule update request
        repo: Rule repository

    Returns:
        Updated rule data
    """
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if request.rule_config:
        updates["rule_config"] = request.rule_config.model_dump()

    rule = await repo.update_rule(rule_id, updates)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )

    return RuleResponse(**rule.to_dict())


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    repo: RuleRepository = Depends(get_rule_repository),
) -> None:
    """
    Delete a rule.

    Args:
        rule_id: Rule identifier
        repo: Rule repository
    """
    success = await repo.delete_rule(rule_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )


@router.post("/{rule_id}/enable", response_model=RuleResponse)
async def enable_rule(
    rule_id: str,
    repo: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Enable a rule.

    Args:
        rule_id: Rule identifier
        repo: Rule repository

    Returns:
        Updated rule data
    """
    rule = await repo.update_rule(rule_id, {"is_enabled": True})
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )

    return RuleResponse(**rule.to_dict())


@router.post("/{rule_id}/disable", response_model=RuleResponse)
async def disable_rule(
    rule_id: str,
    repo: RuleRepository = Depends(get_rule_repository),
) -> RuleResponse:
    """
    Disable a rule.

    Args:
        rule_id: Rule identifier
        repo: Rule repository

    Returns:
        Updated rule data
    """
    rule = await repo.update_rule(rule_id, {"is_enabled": False})
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )

    return RuleResponse(**rule.to_dict())


@router.post("/evaluate", response_model=dict)
async def evaluate_rules(
    request: RuleEvaluateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Evaluate rules for given input data.

    Args:
        request: Evaluation request
        db: Database session

    Returns:
        Evaluation results
    """
    context = RuleExecutionContext(
        patient_id=request.patient_id,
        input_data=request.input_data,
    )

    engine = RuleEngine(db)
    results = await engine.evaluate_rules(
        context,
        categories=request.categories,
        disease_code=request.disease_code,
    )

    return {
        "patient_id": request.patient_id,
        "matched_count": sum(1 for r in results if r.matched),
        "total_evaluated": len(results),
        "results": [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "matched": r.matched,
                "confidence": r.confidence,
                "result": r.result,
                "execution_time_ms": r.execution_time_ms,
            }
            for r in results
        ],
    }


@router.post("/evaluate/vital-signs", response_model=dict)
async def evaluate_vital_signs(
    request: VitalSignEvaluateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Evaluate vital signs against reference standards.

    Args:
        request: Vital sign evaluation request
        db: Database session

    Returns:
        Risk assessment for each vital sign
    """
    # Add gender and age to vital signs
    vital_signs = request.vital_signs.copy()
    vital_signs["gender"] = request.gender
    if request.age:
        vital_signs["age"] = request.age

    engine = RuleEngine(db)
    results = await engine.evaluate_vital_signs(
        patient_id=request.patient_id,
        vital_signs=vital_signs,
    )

    # Calculate overall risk profile
    high_risk_signs = [
        name for name, data in results.items()
        if data.get("risk_level") in ["high", "very_high"]
    ]

    return {
        "patient_id": request.patient_id,
        "vital_signs": results,
        "summary": {
            "total_signs": len(results),
            "normal_count": sum(
                1 for v in results.values()
                if v.get("risk_level") == "normal"
            ),
            "abnormal_count": len(results) - sum(
                1 for v in results.values()
                if v.get("risk_level") == "normal"
            ),
            "high_risk_signs": high_risk_signs,
            "overall_risk": "high" if len(high_risk_signs) > 0 else "normal",
        },
    }


@router.post("/evaluate/risk-score", response_model=dict)
async def calculate_risk_score(
    request: RiskScoreRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Calculate disease risk score.

    Args:
        request: Risk score calculation request
        db: Database session

    Returns:
        Risk score and level
    """
    engine = RuleEngine(db)
    result = await engine.calculate_risk_score(
        patient_id=request.patient_id,
        disease_code=request.disease_code,
        input_data=request.input_data,
    )

    return {
        "patient_id": request.patient_id,
        "disease_code": request.disease_code,
        **result,
    }


@router.get("/standards/vital-signs", response_model=list)
async def list_vital_sign_standards(
    db: AsyncSession = Depends(get_db_session),
) -> list:
    """
    List all vital sign reference standards.

    Args:
        db: Database session

    Returns:
        List of vital sign standards
    """
    from sqlalchemy import select
    from src.infrastructure.persistence.models.rule_models import VitalSignStandardModel

    stmt = select(VitalSignStandardModel).where(
        VitalSignStandardModel.is_enabled == True
    ).order_by(VitalSignStandardModel.standard_name)

    result = await db.execute(stmt)
    standards = result.scalars().all()

    return [s.to_dict() for s in standards]


@router.get("/diseases", response_model=dict)
async def list_diseases(db: AsyncSession = Depends(get_db_session)) -> dict:
    """
    List supported diseases with their rule counts.

    Args:
        db: Database session

    Returns:
        Disease list with rule counts
    """
    from sqlalchemy import func, select
    from src.infrastructure.persistence.models.rule_models import RuleModel

    stmt = select(
        RuleModel.disease_code,
        func.count(RuleModel.id).label("rule_count")
    ).where(
        RuleModel.disease_code.isnot(None)
    ).group_by(RuleModel.disease_code)

    result = await db.execute(stmt)

    disease_info = {
        "hypertension": {"name": "高血压", "code": "hypertension"},
        "diabetes": {"name": "糖尿病", "code": "diabetes"},
        "dyslipidemia": {"name": "血脂异常", "code": "dyslipidemia"},
        "gout": {"name": "痛风", "code": "gout"},
        "obesity": {"name": "肥胖", "code": "obesity"},
        "metabolic_syndrome": {"name": "代谢综合征", "code": "metabolic_syndrome"},
    }

    output = {}
    for disease_code, count in result.all():
        if disease_code in disease_info:
            output[disease_code] = {
                **disease_info[disease_code],
                "rule_count": count,
            }

    return output
