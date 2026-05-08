"""
Assessment insight persistence model.

Stores structured assessment results for later retrieval by party_id.
"""
from typing import Any, Dict, Optional

from sqlalchemy import String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import BaseModel


class AssessmentInsightModel(BaseModel):
    """
    Persisted assessment insight record.

    Each successful assessment writes a row here so the frontend
    can query the latest insight by party_id.
    """

    __tablename__ = "assessment_insights"

    party_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    population_classification: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    abnormal_indicators: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    recommended_data_collection: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    disease_prediction: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    intervention_prescriptions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    full_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = super().to_dict()
        return result
