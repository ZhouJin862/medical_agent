"""
System prompt ORM models.

Stores versioned system prompts with activation support.
"""
import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class SystemPromptModel(BaseModel):
    """
    System prompt ORM model.

    Stores versioned system prompts. Multiple versions can exist for the same key,
    but only one can be active (is_active=True) at a time.
    """

    __tablename__ = "system_prompts"

    prompt_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Unique prompt identifier, e.g. 'medical_assistant_streaming'",
    )
    prompt_desc: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="Brief description of the prompt's purpose",
    )
    prompt_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full prompt text (may contain {variable} placeholders)",
    )
    prompt_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Version number, incremented on each update",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this version is the currently active one",
    )
    prompt_variables: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON list of template variable names, e.g. ['user_input', 'skill_knowledge']",
    )

    __table_args__ = (
        Index("ix_prompt_key_active", "prompt_key", "is_active"),
    )

    def get_variables_list(self) -> list[str]:
        """Parse variables JSON to list."""
        if self.prompt_variables:
            try:
                return json.loads(self.prompt_variables)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
