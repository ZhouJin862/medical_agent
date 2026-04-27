"""Query handlers module."""

from src.application.handlers.query_handlers.consultation_query_handlers import (
    ConsultationQueryHandlers,
)
from src.application.handlers.query_handlers.skill_query_handlers import (
    SkillQueryHandlers,
)

__all__ = [
    "ConsultationQueryHandlers",
    "SkillQueryHandlers",
]
