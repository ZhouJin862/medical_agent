"""
Questionnaire persistence model.

Stores questionnaire definitions as JSON documents (flat array of questions).
"""
from typing import Any, Dict, Optional, List

from sqlalchemy import String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import BaseModel


class QuestionnaireModel(BaseModel):
    """
    Questionnaire definition.

    Stores the full question list as a JSON document matching
    the frontend's data structure (flat array with linked-list navigation).
    """

    __tablename__ = "questionnaires"

    questionnaire_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    questions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = super().to_dict()
        return result
