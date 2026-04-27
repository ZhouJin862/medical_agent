"""
Anthropic LLM Adapter - Supports Claude models and GLM via Anthropic API.

This adapter works with:
- Anthropic Claude models (claude-3-opus, claude-3-sonnet, etc.)
- 智谱 GLM models via Anthropic-compatible API (glm-5, glm-4, etc.)
"""

import logging
from typing import Optional

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

from .llm_interface import LLMInterface, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicLLM(LLMInterface):
    """
    Anthropic API adapter for Claude and GLM models.

    Supports both Anthropic's native Claude models and
    智谱 GLM models through their Anthropic-compatible API.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize Anthropic LLM adapter.

        Args:
            config: Configuration including api_key and base_url
        """
        super().__init__(config)

        if AsyncAnthropic is None:
            raise ImportError(
                "anthropic package is required. "
                "Install with: pip install anthropic"
            )

        self._client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
        logger.info(
            f"Initialized Anthropic LLM with model={config.model}, "
            f"base_url={config.base_url}"
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a response using the Anthropic API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            LLMResponse with generated content
        """
        messages = [{"role": "user", "content": prompt}]

        params = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        if system_prompt:
            params["system"] = system_prompt

        try:
            response = await self._client.messages.create(**params)

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                raw_response={
                    "id": response.id,
                    "type": response.type,
                    "role": response.role,
                },
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate structured JSON output using the Anthropic API.

        Anthropic supports structured output through tool use or
        by explicitly requesting JSON format in the prompt.

        Args:
            prompt: User prompt
            output_schema: JSON schema for expected output
            system_prompt: Optional system prompt

        Returns:
            LLMResponse with structured JSON content
        """
        # Add JSON formatting instructions to the prompt
        json_instruction = (
            "\n\nPlease respond with a valid JSON object that conforms "
            f"to this schema:\n{output_schema}\n\n"
            "Return ONLY the JSON object, no other text."
        )

        enhanced_prompt = prompt + json_instruction

        if system_prompt:
            enhanced_system = system_prompt + " You must respond with valid JSON only."
        else:
            enhanced_system = "You must respond with valid JSON only."

        response = await self.generate(
            prompt=enhanced_prompt,
            system_prompt=enhanced_system,
            temperature=0.3,  # Lower temperature for structured output
        )

        return response

    def supports_structured_output(self) -> bool:
        """
        Check if this provider supports structured output.

        Anthropic supports structured output through:
        1. Tool use (function calling)
        2. JSON mode (explicit prompting)

        Returns:
            True
        """
        return True


def create_claude_llm(
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> AnthropicLLM:
    """
    Convenience function to create a Claude LLM instance.

    Args:
        api_key: Anthropic API key
        model: Claude model name
        temperature: Temperature setting
        max_tokens: Max tokens setting

    Returns:
        AnthropicLLM instance configured for Claude
    """
    config = LLMConfig(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return AnthropicLLM(config)


def create_glm_llm(
    api_key: str,
    base_url: str = "https://open.bigmodel.cn/api/anthropic",
    model: str = "glm-5",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> AnthropicLLM:
    """
    Convenience function to create a GLM LLM instance.

    Args:
        api_key: 智谱 API key
        base_url: 智谱 Anthropic-compatible API endpoint
        model: GLM model name (glm-5, glm-4, etc.)
        temperature: Temperature setting
        max_tokens: Max tokens setting

    Returns:
        AnthropicLLM instance configured for GLM
    """
    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return AnthropicLLM(config)
