"""
Composite Skills API Endpoints.

Provides CRUD operations for composite skills - skills that combine
multiple base skills with custom configuration.
"""
import logging
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models.skill_models import (
    SkillModel,
    SkillType,
)
from src.infrastructure.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/skills/composite",
    tags=["composite-skills"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class ExecutionMode(str, Enum):
    """Skill execution mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class ResponseStyle(str, Enum):
    """Response style for aggregation."""
    STANDARD = "standard"
    VIP_DETAILED = "vip_detailed"
    DETAILED = "detailed"


class CompositeSkillCreate(BaseModel):
    """Request to create a composite skill."""
    name: str = Field(..., description="Unique skill identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Skill description")
    base_skills: List[str] = Field(
        ...,
        description="List of base skill names to combine",
        min_items=1,
    )
    override_settings: Optional[dict] = Field(
        default_factory=dict,
        description="Custom settings to apply",
    )
    business_rules: Optional[dict] = Field(
        default_factory=dict,
        description="Business rules for the skill",
    )
    workflow_config: Optional[dict] = Field(
        default_factory=dict,
        description="Workflow configuration",
    )
    response_style: ResponseStyle = Field(
        default=ResponseStyle.STANDARD,
        description="Response aggregation style",
    )
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.SEQUENTIAL,
        description="Skill execution mode",
    )


class CompositeSkillUpdate(BaseModel):
    """Request to update a composite skill."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    base_skills: Optional[List[str]] = None
    override_settings: Optional[dict] = None
    business_rules: Optional[dict] = None
    workflow_config: Optional[dict] = None
    response_style: Optional[ResponseStyle] = None
    execution_mode: Optional[ExecutionMode] = None
    enabled: Optional[bool] = None


class CompositeSkillResponse(BaseModel):
    """Response with composite skill details."""
    id: str
    name: str
    display_name: str
    description: str
    enabled: bool
    version: str
    config: dict


class CompositeSkillListResponse(BaseModel):
    """Response listing composite skills."""
    skills: List[CompositeSkillResponse]
    total: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("", response_model=CompositeSkillResponse, status_code=status.HTTP_201_CREATED)
async def create_composite_skill(request: CompositeSkillCreate):
    """
    Create a new composite skill.

    A composite skill combines multiple base skills with custom configuration.
    """
    async for session in get_db_session():
        try:
            # Check if skill already exists
            existing_stmt = select(SkillModel).where(SkillModel.skill_name == request.name)
            existing_result = await session.execute(existing_stmt)
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Skill '{request.name}' already exists",
                )

            # Validate base skills exist
            base_skill_stmt = select(SkillModel).where(
                SkillModel.skill_name.in_(request.base_skills),
                SkillModel.is_enabled == True,
            )
            base_result = await session.execute(base_skill_stmt)
            found_skills = {s.skill_name for s in base_result.scalars().all()}

            missing_skills = set(request.base_skills) - found_skills
            if missing_skills:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Base skills not found: {', '.join(missing_skills)}",
                )

            # Build composite config
            config = {
                "base_skills": request.base_skills,
                "override_settings": request.override_settings or {},
                "business_rules": request.business_rules or {},
                "workflow_config": request.workflow_config or {},
                "display_name": request.display_name,
                "response_style": request.response_style.value,
                "execution_mode": request.execution_mode.value,
            }

            # Create skill
            skill = SkillModel(
                skill_name=request.name,
                display_name=request.display_name,
                skill_desc=request.description,
                skill_type=SkillType.GENERIC,
                is_enabled=True,
                skill_version="1.0.0",
                skill_config=config,
            )

            session.add(skill)
            await session.commit()
            await session.refresh(skill)

            logger.info(f"Created composite skill: {request.name}")

            return CompositeSkillResponse(
                id=skill.id,
                name=skill.skill_name,
                display_name=skill.display_name,
                description=skill.skill_desc,
                enabled=skill.is_enabled,
                version=skill.skill_version,
                config=skill.skill_config or {},
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create composite skill: {e}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create skill: {str(e)}",
            )


@router.get("", response_model=CompositeSkillListResponse)
async def list_composite_skills():
    """
    List all composite skills.

    Returns skills that have base_skills configuration.
    """
    async for session in get_db_session():
        try:
            # Get all skills
            stmt = select(SkillModel).where(SkillModel.is_enabled == True)
            result = await session.execute(stmt)
            all_skills = result.scalars().all()

            # Filter for composite skills (have base_skills in config)
            composite_skills = []
            for skill in all_skills:
                if skill.skill_config and isinstance(skill.skill_config, dict):
                    if "base_skills" in skill.skill_config:
                        composite_skills.append(
                            CompositeSkillResponse(
                                id=skill.id,
                                name=skill.skill_name,
                                display_name=skill.display_name,
                                description=skill.skill_desc or "",
                                enabled=skill.is_enabled,
                                version=skill.skill_version,
                                config=skill.skill_config,
                            )
                        )

            return CompositeSkillListResponse(
                skills=composite_skills,
                total=len(composite_skills),
            )

        except Exception as e:
            logger.error(f"Failed to list composite skills: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list skills: {str(e)}",
            )


@router.get("/{skill_name}", response_model=CompositeSkillResponse)
async def get_composite_skill(skill_name: str):
    """Get details of a specific composite skill."""
    async for session in get_db_session():
        try:
            stmt = select(SkillModel).where(
                SkillModel.skill_name == skill_name,
                SkillModel.is_enabled == True,
            )
            result = await session.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Skill '{skill_name}' not found",
                )

            # Verify it's a composite skill
            if not skill.skill_config or "base_skills" not in skill.skill_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Skill '{skill_name}' is not a composite skill",
                )

            return CompositeSkillResponse(
                id=skill.id,
                name=skill.skill_name,
                display_name=skill.display_name,
                description=skill.skill_desc or "",
                enabled=skill.is_enabled,
                version=skill.skill_version,
                config=skill.skill_config,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get composite skill: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get skill: {str(e)}",
            )


@router.put("/{skill_name}", response_model=CompositeSkillResponse)
async def update_composite_skill(skill_name: str, request: CompositeSkillUpdate):
    """Update an existing composite skill."""
    async for session in get_db_session():
        try:
            stmt = select(SkillModel).where(
                SkillModel.skill_name == skill_name,
                SkillModel.is_enabled == True,
            )
            result = await session.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Skill '{skill_name}' not found",
                )

            # Verify it's a composite skill
            if not skill.skill_config or "base_skills" not in skill.skill_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Skill '{skill_name}' is not a composite skill",
                )

            # Update fields
            if request.display_name is not None:
                skill.display_name = request.display_name
            if request.description is not None:
                skill.skill_desc = request.description
            if request.enabled is not None:
                skill.is_enabled = request.enabled

            # Update config
            config = skill.skill_config or {}

            if request.base_skills is not None:
                # Validate base skills exist
                base_skill_stmt = select(SkillModel).where(
                    SkillModel.skill_name.in_(request.base_skills),
                    SkillModel.is_enabled == True,
                )
                base_result = await session.execute(base_skill_stmt)
                found_skills = {s.skill_name for s in base_result.scalars().all()}

                missing_skills = set(request.base_skills) - found_skills
                if missing_skills:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Base skills not found: {', '.join(missing_skills)}",
                    )

                config["base_skills"] = request.base_skills

            if request.override_settings is not None:
                config["override_settings"] = request.override_settings
            if request.business_rules is not None:
                config["business_rules"] = request.business_rules
            if request.workflow_config is not None:
                config["workflow_config"] = request.workflow_config
            if request.response_style is not None:
                config["response_style"] = request.response_style.value
            if request.execution_mode is not None:
                config["execution_mode"] = request.execution_mode.value

            skill.skill_config = config

            await session.commit()
            await session.refresh(skill)

            logger.info(f"Updated composite skill: {skill_name}")

            return CompositeSkillResponse(
                id=skill.id,
                name=skill.skill_name,
                display_name=skill.display_name,
                description=skill.skill_desc or "",
                enabled=skill.is_enabled,
                version=skill.skill_version,
                config=skill.skill_config,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update composite skill: {e}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update skill: {str(e)}",
            )


@router.delete("/{skill_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_composite_skill(skill_name: str):
    """Delete (disable) a composite skill."""
    async for session in get_db_session():
        try:
            stmt = select(SkillModel).where(
                SkillModel.skill_name == skill_name,
            )
            result = await session.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Skill '{skill_name}' not found",
                )

            # Soft delete - disable the skill
            skill.is_enabled = False
            await session.commit()

            logger.info(f"Deleted composite skill: {skill_name}")

            return None

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete composite skill: {e}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete skill: {str(e)}",
            )


@router.post("/test", response_model=dict)
async def test_composite_skill_execution(
    skill_name: str,
    user_input: str = "帮我做综合评估",
):
    """
    Test execution of a composite skill.

    Useful for validating composite skill configuration.
    """
    from src.domain.shared.services.composite_skill_executor import (
        CompositeSkillExecutor,
    )
    from src.domain.shared.services.unified_skills_repository import (
        UnifiedSkillsRepository,
    )

    async for session in get_db_session():
        try:
            # Check skill exists and is composite
            stmt = select(SkillModel).where(
                SkillModel.skill_name == skill_name,
                SkillModel.is_enabled == True,
            )
            result = await session.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Skill '{skill_name}' not found",
                )

            if not skill.skill_config or "base_skills" not in skill.skill_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Skill '{skill_name}' is not a composite skill",
                )

            # Create executor
            repository = UnifiedSkillsRepository(session)
            executor = CompositeSkillExecutor(repository)

            # Load composite config
            config = await executor.load_composite_config_from_database(skill_name)
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to load composite configuration",
                )

            # Execute
            result = await executor.execute_composite_skill(
                config=config,
                user_input=user_input,
                patient_context=None,
                conversation_context=None,
            )

            return {
                "success": result.success,
                "response": result.response,
                "execution_time_ms": result.execution_time_ms,
                "base_skills_used": result.metadata.get("loaded_skills", []),
                "error": result.error,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to test composite skill: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to test skill: {str(e)}",
            )
