"""Application handlers module."""

from src.application.handlers.command_handlers import (
    ConsultationCommandHandlers,
    SkillCommandHandlers,
)
from src.application.handlers.query_handlers import (
    ConsultationQueryHandlers,
    SkillQueryHandlers,
)

__all__ = [
    "ConsultationCommandHandlers",
    "SkillCommandHandlers",
    "ConsultationQueryHandlers",
    "SkillQueryHandlers",
]
