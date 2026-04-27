"""
Skill commands.

Defines commands for skill management operations.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateSkillCommand:
    """Command to create a new skill."""

    name: str
    display_name: str
    skill_type: str
    category: str | None = None
    description: str | None = None
    intent_keywords: list[str] | None = None
    config: dict[str, Any] | None = None
    model_config: dict[str, Any] | None = None
    prompts: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.name:
            raise ValueError("name is required")
        if not self.display_name:
            raise ValueError("display_name is required")
        if not self.skill_type:
            raise ValueError("skill_type is required")

        valid_types = ["generic", "disease_specific", "prescription", "mcp_tool"]
        if self.skill_type not in valid_types:
            raise ValueError(f"skill_type must be one of {valid_types}")

        valid_categories = [
            "health_assessment",
            "risk_prediction",
            "health_promotion",
            "prescription_generation",
            "triage_guidance",
            "medication_check",
            "service_recommendation",
        ]
        if self.category and self.category not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}")


@dataclass(frozen=True)
class UpdateSkillCommand:
    """Command to update an existing skill."""

    skill_id: str
    display_name: str | None = None
    description: str | None = None
    intent_keywords: list[str] | None = None
    config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class EnableSkillCommand:
    """Command to enable a skill."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class DisableSkillCommand:
    """Command to disable a skill."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class ReloadSkillCommand:
    """Command to reload a skill from database."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class DeleteSkillCommand:
    """Command to delete a skill."""

    skill_id: str

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class UpdateSkillPromptCommand:
    """Command to update a skill prompt."""

    skill_id: str
    prompt_type: str
    content: str

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")
        if not self.prompt_type:
            raise ValueError("prompt_type is required")
        if not self.content:
            raise ValueError("content is required")


@dataclass(frozen=True)
class UpdateSkillModelConfigCommand:
    """Command to update skill model configuration."""

    skill_id: str
    model_config: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate command data."""
        if not self.skill_id:
            raise ValueError("skill_id is required")
        if not self.model_config:
            raise ValueError("model_config is required")
