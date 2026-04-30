"""
Skills-Integrated Agent API routes.

Provides endpoints for the Claude Skills-integrated medical agent.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.infrastructure.agent import SkillsIntegratedAgent
from src.infrastructure.agent.state import AgentState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentRequest(BaseModel):
    """Request for agent processing."""
    patient_id: str = Field(..., description="Patient identifier")
    message: str = Field(..., description="User message to process")
    session_id: Optional[str] = Field(None, description="Session ID for memory isolation")


class AgentResponse(BaseModel):
    """Response from agent processing."""
    patient_id: str
    status: str
    intent: Optional[str] = None
    skill_used: Optional[str] = None
    confidence: float = 0.0
    response: str
    structured_output: Optional[dict] = None
    error: Optional[str] = None


class SkillSelectionRequest(BaseModel):
    """Request for skill selection only."""
    message: str = Field(..., description="User message")
    conversation_context: Optional[str] = Field(None, description="Optional conversation context")


class SkillSelectionResponse(BaseModel):
    """Response from skill selection."""
    selected_skill: Optional[str]
    confidence: float
    reasoning: str
    alternative_skills: list[str]
    should_use_skill: bool


# ============================================================================
# Agent Instances
# ============================================================================

# Global agent instance (could be moved to dependency injection)
_skills_agent: Optional[SkillsIntegratedAgent] = None


def get_skills_agent() -> SkillsIntegratedAgent:
    """Get or create the skills-integrated agent."""
    global _skills_agent
    if _skills_agent is None:
        _skills_agent = SkillsIntegratedAgent()
    return _skills_agent


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/process", response_model=AgentResponse)
async def process_with_agent(
    request: AgentRequest,
    background_tasks: BackgroundTasks,
):
    """
    Process a user message with the medical agent.

    Uses the Claude Skills-integrated agent by default,
    which provides intelligent skill selection and execution.
    """
    try:
        # Select agent
        agent = get_skills_agent()

        # Process request
        result = await agent.process(
            user_input=request.message,
            patient_id=request.patient_id,
            session_id=request.session_id,
        )

        return AgentResponse(
            patient_id=result.patient_id,
            status=result.status.value,
            intent=result.intent.value if result.intent else None,
            skill_used=result.suggested_skill,
            confidence=result.confidence,
            response=result.final_response or "",
            structured_output=result.structured_output,
            error=result.error_message,
        )

    except Exception as e:
        logger.error(f"Agent processing error: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}"
        )


@router.post("/select-skill", response_model=SkillSelectionResponse)
async def select_skill(request: SkillSelectionRequest):
    """
    Select the most appropriate skill for a user message.

    This endpoint only performs skill selection without execution,
    useful for understanding which skill would be chosen.
    """
    try:
        from src.infrastructure.database import get_db_session
        from src.domain.shared.services.llm_skill_selector import LLMSkillSelector

        async for session in get_db_session():
            selector = LLMSkillSelector(session)
            selection = await selector.select_skill(
                user_input=request.message,
                conversation_context=request.conversation_context,
            )

            return SkillSelectionResponse(
                selected_skill=selection.skill_name,
                confidence=selection.confidence,
                reasoning=selection.reasoning,
                alternative_skills=selection.alternative_skills,
                should_use_skill=selection.should_use_skill,
            )

        raise HTTPException(status_code=500, detail="Database session error")

    except Exception as e:
        logger.error(f"Skill selection error: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Skill selection failed: {str(e)}"
        )


@router.get("/skills/status")
async def get_agent_skills_status():
    """
    Get the status of available skills in the agent.

    Returns information about the SkillsRegistry and available skills.
    """
    try:
        from src.infrastructure.database import get_db_session
        from src.domain.shared.services.unified_skills_repository import UnifiedSkillsRepository

        async for session in get_db_session():
            repository = UnifiedSkillsRepository(session, skills_dir="skills")

            # Get all skills
            all_skills = await repository.list_skills(enabled_only=True)

            # Count by source
            by_source = {"file": 0, "database": 0}
            for skill in all_skills:
                by_source[skill.source.value] += 1

            # Get skills prompt
            skills_prompt = await repository.get_skills_prompt()

            return {
                "total_skills": len(all_skills),
                "by_source": by_source,
                "skills": [
                    {
                        "name": s.name,
                        "source": s.source.value,
                        "description": s.description[:100] + "..." if len(s.description) > 100 else s.description,
                    }
                    for s in all_skills
                ],
                "prompt_preview": skills_prompt[:500] + "..." if len(skills_prompt) > 500 else skills_prompt,
            }

        raise HTTPException(status_code=500, detail="Database session error")

    except Exception as e:
        logger.error(f"Skills status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get skills status: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_agent_cache(background_tasks: BackgroundTasks):
    """
    Clear the agent and skills cache.

    Useful when skills have been modified and you want to reload them.
    """
    def do_clear():
        """Background cache clear task."""
        try:
            global _skills_agent
            _skills_agent = None

            from src.domain.shared.services.unified_skills_repository import UnifiedSkillsRepository
            from src.infrastructure.database import get_db_session

            async def clear_repo_cache():
                async for session in get_db_session():
                    repository = UnifiedSkillsRepository(session, skills_dir="skills")
                    repository.invalidate_cache()
                    break

            import asyncio
            asyncio.run(clear_repo_cache())

            logger.info("Agent cache cleared successfully")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    background_tasks.add_task(do_clear)

    return {
        "message": "Cache clear started in background",
        "status": "clearing",
    }


@router.get("/test/skill-selection")
async def test_skill_selection():
    """
    Test endpoint for skill selection.

    Returns skill selection results for sample queries.
    """
    test_queries = [
        "我血压150/95，严重吗？",
        "帮我评估一下糖尿病风险",
        "我最近经常头晕，可能是什​么原因？",
        "我想了解一下如何健康饮食",
    ]

    results = []

    try:
        from src.infrastructure.database import get_db_session
        from src.domain.shared.services.llm_skill_selector import LLMSkillSelector

        async for session in get_db_session():
            selector = LLMSkillSelector(session)

            for query in test_queries:
                try:
                    selection = await selector.select_skill(query)
                    results.append({
                        "query": query,
                        "selected_skill": selection.skill_name,
                        "confidence": selection.confidence,
                        "reasoning": selection.reasoning,
                    })
                except Exception as e:
                    results.append({
                        "query": query,
                        "error": str(e),
                    })

            break

        return {
            "test_results": results,
            "total_tests": len(test_queries),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}"
        )
