"""
LLM Interface - Protocol for LLM providers.

Defines the contract that all LLM adapters must implement.
"""

from dataclasses import dataclass
from typing import Optional, Protocol
from abc import ABC, abstractmethod


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    api_key: str
    base_url: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    tokens_used: int = 0
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None


class LLMInterface(ABC):
    """
    Abstract base class for LLM providers.

    All LLM adapters must implement this interface to ensure
    compatibility with the rest of the system.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider.

        Args:
            config: Configuration for this LLM provider
        """
        self.config = config
        self._client = None

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: User prompt to send
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            LLMResponse with generated content and metadata
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate structured JSON output from the LLM.

        Args:
            prompt: User prompt to send
            output_schema: JSON schema for expected output
            system_prompt: Optional system prompt

        Returns:
            LLMResponse with structured JSON content
        """
        pass

    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Check if this provider supports structured output."""
        pass

    @property
    def model_name(self) -> str:
        """Get the model name being used."""
        return self.config.model

    def get_config(self) -> LLMConfig:
        """Get the current configuration."""
        return self.config
