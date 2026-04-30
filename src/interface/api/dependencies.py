"""
Dependency injection for API routes.

Provides factory functions for all application services.
"""
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.application.services.skill_management_service import (
    SkillManagementApplicationService,
)
from src.application.services.chat_service import ChatApplicationService
from src.application.services.consultation_service import ConsultationApplicationService
from src.application.services.health_assessment_service import (
    HealthAssessmentApplicationService,
)
from src.application.services.health_plan_service import HealthPlanApplicationService
from src.infrastructure.persistence.repositories.consultation_repository_impl import (
    ConsultationRepositoryImpl,
)
from src.infrastructure.persistence.repositories.health_plan_repository_impl import (
    HealthPlanRepositoryImpl,
)
from src.infrastructure.session.session_manager import SessionManager
from src.infrastructure.memory.memory_store import MemoryStore
from src.infrastructure.agent.skills_integration import SkillsIntegratedAgent
from src.domain.consultation.repositories.consultation_repository import (
    IConsultationRepository,
)
from src.domain.health_plan.repositories.health_plan_repository import (
    IHealthPlanRepository,
)


# Database session dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_db_session():
        yield session


# Session manager dependency
async def get_session_manager() -> AsyncGenerator[SessionManager, None]:
    """Get session manager for conversation state."""
    yield SessionManager()


# Memory store dependency
async def get_memory_store() -> AsyncGenerator[MemoryStore, None]:
    """Get memory store for long-term conversation persistence."""
    store = MemoryStore()
    yield store


# Medical agent dependency
def get_medical_agent() -> SkillsIntegratedAgent:
    """Get medical agent instance with multi-skill support."""
    return SkillsIntegratedAgent()


# Consultation repository dependency
async def get_consultation_repository(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[IConsultationRepository, None]:
    """Get consultation repository."""
    repo = ConsultationRepositoryImpl(session=db)
    yield repo


# Health plan repository dependency
async def get_health_plan_repository(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[IHealthPlanRepository, None]:
    """Get health plan repository."""
    repo = HealthPlanRepositoryImpl(session=db)
    yield repo


# Skill management service dependency
async def get_skill_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SkillManagementApplicationService, None]:
    """Get skill management service."""
    service = SkillManagementApplicationService(session=db)
    yield service


# Chat application service dependency
def get_chat_service(
    consultation_repo: IConsultationRepository = Depends(get_consultation_repository),
    agent: SkillsIntegratedAgent = Depends(get_medical_agent),
) -> ChatApplicationService:
    """Get chat application service."""
    from src.infrastructure.mcp.client_factory import MCPClientFactory
    service = ChatApplicationService(
        consultation_repository=consultation_repo,
        mcp_client_factory=MCPClientFactory(),
        agent=agent,
    )
    return service


# Consultation application service dependency
async def get_consultation_service(
    consultation_repo: IConsultationRepository = Depends(get_consultation_repository),
) -> AsyncGenerator[ConsultationApplicationService, None]:
    """Get consultation application service."""
    from src.infrastructure.mcp.client_factory import MCPClientFactory
    service = ConsultationApplicationService(
        consultation_repository=consultation_repo,
        mcp_client_factory=MCPClientFactory(),
    )
    yield service


# Health assessment service dependency
async def get_health_assessment_service(
) -> AsyncGenerator[HealthAssessmentApplicationService, None]:
    """Get health assessment service."""
    from src.application.services.health_assessment_service import HealthAssessmentApplicationService
    from src.infrastructure.mcp.client_factory import MCPClientFactory
    service = HealthAssessmentApplicationService(
        mcp_client_factory=MCPClientFactory(),
    )
    yield service


# Health plan service dependency
async def get_health_plan_service(
    health_plan_repo: IHealthPlanRepository = Depends(get_health_plan_repository),
) -> AsyncGenerator[HealthPlanApplicationService, None]:
    """Get health plan service."""
    from src.application.services.health_plan_service import HealthPlanApplicationService
    from src.infrastructure.mcp.client_factory import MCPClientFactory
    service = HealthPlanApplicationService(
        health_plan_repository=health_plan_repo,
        mcp_client_factory=MCPClientFactory(),
    )
    yield service
