"""
Base Skill class for all health assessment skills.

All concrete skills should inherit from BaseSkill and implement
the execute method.
"""

import logging
from typing import Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..llm import LLMInterface, LLMFactory, ModelProvider
from .signatures.base import BaseSignature

logger = logging.getLogger(__name__)


@dataclass
class SkillConfig:
    """
    Configuration for a skill instance.

    Attributes:
        name: Unique skill name
        description: Human-readable description
        signature_class: DSPy signature class to use
        model_provider: LLM provider to use
        model_config: Additional model configuration
        enabled: Whether the skill is enabled
        intent_keywords: Keywords that trigger this skill
        knowledge_base_ids: Associated knowledge base IDs
    """

    name: str
    description: str
    signature_class: type[BaseSignature]
    model_provider: ModelProvider = ModelProvider.ANTHROPIC
    model_config: dict = field(default_factory=dict)
    enabled: bool = True
    intent_keywords: list[str] = field(default_factory=list)
    knowledge_base_ids: list[str] = field(default_factory=list)


@dataclass
class SkillResult:
    """
    Result from executing a skill.

    Attributes:
        success: Whether execution was successful
        data: Result data (structured output)
        error: Error message if failed
        metadata: Additional metadata about the execution
    """

    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class BaseSkill(ABC):
    """
    Base class for all health assessment skills.

    Provides common functionality for:
    - LLM integration
    - Prompt formatting
    - Input validation
    - Output parsing
    - Error handling
    """

    def __init__(self, config: SkillConfig, llm: Optional[LLMInterface] = None):
        """
        Initialize the skill.

        Args:
            config: Skill configuration
            llm: Optional LLM instance (creates default if not provided)
        """
        self.config = config
        self._llm = llm

        if not config.enabled:
            logger.warning(f"Skill '{config.name}' is disabled")

    @property
    def llm(self) -> LLMInterface:
        """Get or create LLM instance."""
        if self._llm is None:
            self._llm = LLMFactory.create(self.config.model_provider)
        return self._llm

    @property
    def signature(self) -> BaseSignature:
        """Get the signature class for this skill."""
        return self.config.signature_class

    def can_handle(self, user_input: str) -> bool:
        """
        Check if this skill can handle the given input.

        Args:
            user_input: User's input text

        Returns:
            True if this skill should handle the input
        """
        if not self.config.enabled:
            return False

        # Check for @skill_name syntax
        if f"@{self.config.name}" in user_input:
            return True

        # Check for intent keywords
        for keyword in self.config.intent_keywords:
            if keyword in user_input:
                return True

        return False

    async def execute(self, **kwargs) -> SkillResult:
        """
        Execute the skill with given inputs.

        Args:
            **kwargs: Input parameters for the skill

        Returns:
            SkillResult with execution outcome
        """
        if not self.config.enabled:
            return SkillResult(
                success=False,
                error=f"Skill '{self.config.name}' is disabled"
            )

        try:
            # Validate inputs using signature
            self.signature.validate_inputs(**kwargs)

            # Format prompt
            prompt = self._format_prompt(**kwargs)

            # Generate response
            response = await self._generate_response(prompt)

            # Parse result
            result_data = self._parse_result(response)

            return SkillResult(
                success=True,
                data=result_data,
                metadata={
                    "model": response.model,
                    "tokens_used": response.tokens_used,
                    "skill": self.config.name,
                }
            )

        except Exception as e:
            logger.error(f"Skill '{self.config.name}' execution failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                metadata={"skill": self.config.name}
            )

    def _format_prompt(self, **kwargs) -> str:
        """
        Format the prompt using signature template.

        Args:
            **kwargs: Input values

        Returns:
            Formatted prompt string
        """
        return self.signature.format_prompt(**kwargs)

    async def _generate_response(self, prompt: str):
        """
        Generate LLM response.

        Args:
            prompt: Formatted prompt

        Returns:
            LLM response
        """
        system_prompt = self.signature.get_system_prompt()

        # Use structured output if supported
        if self.llm.supports_structured_output():
            output_schema = self.signature.get_output_schema()
            return await self.llm.generate_structured(
                prompt=prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

        # Fall back to regular generation
        return await self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

    def _parse_result(self, response) -> dict:
        """
        Parse LLM response into structured result.

        Args:
            response: LLM response

        Returns:
            Parsed result dictionary
        """
        import json

        content = response.content

        # Try to parse as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Not JSON, return as-is
            return {"response": content}

    def get_info(self) -> dict:
        """
        Get skill information.

        Returns:
            Dictionary with skill metadata
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "enabled": self.config.enabled,
            "model_provider": self.config.model_provider.value,
            "intent_keywords": self.config.intent_keywords,
            "input_fields": [
                {
                    "name": f.name,
                    "description": f.description,
                    "required": f.required,
                }
                for f in self.signature.get_input_fields()
            ],
            "output_fields": [
                {
                    "name": f.name,
                    "description": f.description,
                }
                for f in self.signature.get_output_fields()
            ],
        }

    def __repr__(self) -> str:
        return f"BaseSkill(name={self.config.name}, enabled={self.config.enabled})"


class SimpleSkill(BaseSkill):
    """
    Simple skill implementation for basic use cases.

    Uses a straightforward prompt-response pattern without
    complex input/output processing.
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        model_provider: ModelProvider = ModelProvider.ANTHROPIC,
        enabled: bool = True,
    ):
        """
        Initialize a simple skill.

        Args:
            name: Skill name
            description: Skill description
            system_prompt: System prompt for the LLM
            model_provider: LLM provider to use
            enabled: Whether the skill is enabled
        """
        # Create a simple signature
        from .signatures.base import BaseSignature, InputField, OutputField

        class SimpleSignature(BaseSignature):
            system_prompt = system_prompt
            input_fields = [
                InputField(
                    name="user_input",
                    description="User input text",
                    required=True,
                )
            ]
            output_fields = [
                OutputField(
                    name="response",
                    description="Assistant response",
                )
            ]
            prompt_template = "{user_input}"

        config = SkillConfig(
            name=name,
            description=description,
            signature_class=SimpleSignature,
            model_provider=model_provider,
            enabled=enabled,
        )

        super().__init__(config)
