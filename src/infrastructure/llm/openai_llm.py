"""
OpenAI LLM Adapter - Supports GPT models and GLM via OpenAI-compatible API.

This adapter works with:
- OpenAI GPT models (gpt-4, gpt-3.5-turbo, etc.)
- 智谱 GLM models via OpenAI-compatible API (glm-5, glm-4, etc.)
"""

import logging
from typing import Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from .llm_interface import LLMInterface, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class OpenAILLM(LLMInterface):
    """
    OpenAI API adapter for GPT and GLM models.

    Supports both OpenAI's native GPT models and
    智谱 GLM models through their OpenAI-compatible API.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize OpenAI LLM adapter.

        Args:
            config: Configuration including api_key and base_url
        """
        super().__init__(config)

        if AsyncOpenAI is None:
            raise ImportError(
                "openai package is required. "
                "Install with: pip install openai"
            )

        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
        logger.info(
            f"Initialized OpenAI LLM with model={config.model}, "
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
        Generate a response using the OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            LLMResponse with generated content
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        params = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        try:
            response = await self._client.chat.completions.create(**params)

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                tokens_used=response.usage.prompt_tokens + response.usage.completion_tokens,
                finish_reason=response.choices[0].finish_reason,
                raw_response={
                    "id": response.id,
                    "created": response.created,
                    "object": response.object,
                },
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate structured JSON output using the OpenAI API.

        OpenAI supports structured output through:
        1. JSON mode (response_format parameter)
        2. Explicit prompting for JSON format

        Args:
            prompt: User prompt
            output_schema: JSON schema for expected output
            system_prompt: Optional system prompt

        Returns:
            LLMResponse with structured JSON content
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt + " You must respond with valid JSON only."})
        else:
            messages.append({"role": "system", "content": "You must respond with valid JSON only."})

        json_instruction = (
            "\n\nPlease respond with a valid JSON object that conforms "
            f"to this schema:\n{output_schema}\n\n"
            "Return ONLY the JSON object, no other text."
        )
        messages.append({"role": "user", "content": prompt + json_instruction})

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=self.config.max_tokens,
            )

            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                tokens_used=response.usage.prompt_tokens + response.usage.completion_tokens,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(f"OpenAI structured output error: {e}")
            # Fall back to regular generation with JSON instruction
            return await self.generate(
                prompt=prompt + json_instruction,
                system_prompt=system_prompt,
                temperature=0.3,
            )

    def supports_structured_output(self) -> bool:
        """
        Check if this provider supports structured output.

        OpenAI supports structured output through:
        1. JSON mode (response_format parameter)
        2. Function calling (tools)

        Returns:
            True
        """
        return True


def create_openai_llm(
    api_key: str,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> OpenAILLM:
    """
    Convenience function to create an OpenAI LLM instance.

    Args:
        api_key: OpenAI API key
        model: GPT model name
        temperature: Temperature setting
        max_tokens: Max tokens setting

    Returns:
        OpenAILLM instance configured for OpenAI
    """
    config = LLMConfig(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return OpenAILLM(config)


def create_glm_llm_openai(
    api_key: str,
    base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    model: str = "glm-5",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> OpenAILLM:
    """
    Convenience function to create a GLM LLM instance via OpenAI-compatible API.

    Args:
        api_key: 智谱 API key
        base_url: 智谱 OpenAI-compatible API endpoint
        model: GLM model name (glm-5, glm-4, etc.)
        temperature: Temperature setting
        max_tokens: Max tokens setting

    Returns:
        OpenAILLM instance configured for GLM
    """
    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return OpenAILLM(config)
