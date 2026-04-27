"""
LLM Factory - Factory for creating LLM provider instances.

Supports configuration-driven model selection with automatic fallback.
"""

import logging
from typing import Optional, Dict, Type
from enum import Enum

from .llm_interface import LLMInterface, LLMConfig
from .anthropic_llm import AnthropicLLM
from .openai_llm import OpenAILLM

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available model providers."""

    ANTHROPIC = "anthropic"  # Claude models or GLM via Anthropic API
    OPENAI = "openai"  # GPT models


class LLMFactory:
    """
    Factory for creating LLM provider instances.

    Supports:
    - Configuration-driven provider selection
    - Multiple provider instances with different configs
    - Automatic fallback on errors
    - Per-skill model configuration
    """

    _providers: Dict[ModelProvider, Type[LLMInterface]] = {
        ModelProvider.ANTHROPIC: AnthropicLLM,
        ModelProvider.OPENAI: OpenAILLM,
    }

    _default_configs: Dict[ModelProvider, LLMConfig] = {}

    @classmethod
    def register_provider(
        cls, provider: ModelProvider, provider_class: Type[LLMInterface]
    ) -> None:
        """
        Register a new LLM provider.

        Args:
            provider: Provider enum value
            provider_class: Provider implementation class
        """
        cls._providers[provider] = provider_class
        logger.info(f"Registered LLM provider: {provider.value}")

    @classmethod
    def set_default_config(cls, provider: ModelProvider, config: LLMConfig) -> None:
        """
        Set default configuration for a provider.

        Args:
            provider: Provider enum value
            config: Default configuration
        """
        cls._default_configs[provider] = config
        logger.info(f"Set default config for provider: {provider.value}")

    @classmethod
    def create(
        cls,
        provider: ModelProvider,
        config: Optional[LLMConfig] = None,
    ) -> LLMInterface:
        """
        Create an LLM provider instance.

        Args:
            provider: Provider enum value
            config: Optional configuration (uses default if not provided)

        Returns:
            LLMInterface instance

        Raises:
            ValueError: If provider is not registered
        """
        if provider not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[provider]

        # Use provided config or default
        if config is None:
            config = cls._default_configs.get(provider)
            if config is None:
                raise ValueError(
                    f"No configuration provided for {provider.value} "
                    f"and no default configured"
                )

        instance = provider_class(config)
        logger.info(f"Created LLM instance: {provider.value} (model={config.model})")
        return instance

    @classmethod
    def create_from_dict(cls, config_dict: dict) -> LLMInterface:
        """
        Create an LLM provider instance from a dictionary configuration.

        Expected format:
        {
            "provider": "anthropic" | "openai",
            "api_key": "...",
            "base_url": "...",
            "model": "...",
            "temperature": 0.7,
            "max_tokens": 2000
        }

        Args:
            config_dict: Dictionary with provider configuration

        Returns:
            LLMInterface instance
        """
        provider_name = config_dict.get("provider", "anthropic")
        try:
            provider = ModelProvider(provider_name)
        except ValueError:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {[p.value for p in ModelProvider]}"
            )

        config = LLMConfig(
            api_key=config_dict["api_key"],
            base_url=config_dict.get("base_url"),
            model=config_dict.get("model", "default"),
            temperature=config_dict.get("temperature", 0.7),
            max_tokens=config_dict.get("max_tokens", 2000),
        )

        return cls.create(provider, config)

    @classmethod
    def get_fallback_chain(cls, preferred: ModelProvider) -> list[ModelProvider]:
        """
        Get fallback chain for a provider.

        Args:
            preferred: Preferred provider

        Returns:
            List of providers to try in order (preferred first)
        """
        all_providers = list(ModelProvider)
        try:
            all_providers.remove(preferred)
        except ValueError:
            pass
        return [preferred] + all_providers

    @classmethod
    async def create_with_fallback(
        cls,
        preferred: ModelProvider,
        config: Optional[LLMConfig] = None,
    ) -> Optional[LLMInterface]:
        """
        Create an LLM provider with automatic fallback.

        Tries the preferred provider first, then falls back to other
        available providers if the preferred one fails.

        Args:
            preferred: Preferred provider
            config: Configuration to use (same config for all providers)

        Returns:
            First successfully created LLMInterface instance
        """
        providers = cls.get_fallback_chain(preferred)

        for provider in providers:
            try:
                # Adjust config if needed for different providers
                provider_config = config
                if config is not None and provider in cls._default_configs:
                    provider_config = cls._default_configs[provider]

                return cls.create(provider, provider_config)
            except Exception as e:
                logger.warning(
                    f"Failed to create {provider.value} instance: {e}. "
                    f"Trying next provider..."
                )

        logger.error("Failed to create any LLM provider instance")
        return None


def create_llm(
    provider: str | ModelProvider = ModelProvider.ANTHROPIC,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> LLMInterface:
    """
    Convenience function to create an LLM instance.

    Args:
        provider: Provider name or enum
        api_key: API key for the provider
        base_url: Optional base URL override
        model: Model name
        temperature: Temperature setting
        max_tokens: Max tokens setting

    Returns:
        LLMInterface instance
    """
    if isinstance(provider, str):
        try:
            provider = ModelProvider(provider)
        except ValueError:
            raise ValueError(f"Unknown provider: {provider}")

    config = LLMConfig(
        api_key=api_key or "",
        base_url=base_url,
        model=model or "default",
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return LLMFactory.create(provider, config)
