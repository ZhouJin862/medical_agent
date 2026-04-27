"""
Skill queries.

Defines queries for skill-related read operations.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GetSkillListQuery:
    """Query to list skills with optional filtering."""

    skill_type: str | None = None
    category: str | None = None
    enabled_only: bool = False

    def __post_init__(self) -> None:
        """Validate query data."""
        if self.skill_type:
            valid_types = ["generic", "disease_specific", "prescription", "mcp_tool"]
            if self.skill_type not in valid_types:
                raise ValueError(f"skill_type must be one of {valid_types}")

        if self.category:
            valid_categories = [
                "health_assessment",
                "risk_prediction",
                "health_promotion",
                "prescription_generation",
                "triage_guidance",
                "medication_check",
                "service_recommendation",
            ]
            if self.category not in valid_categories:
                raise ValueError(f"category must be one of {valid_categories}")


@dataclass(frozen=True)
class GetSkillByIdQuery:
    """Query to get skill by ID."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class GetSkillPromptsQuery:
    """Query to get prompts for a skill."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class GetSkillModelConfigQuery:
    """Query to get model configuration for a skill."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate query data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")
