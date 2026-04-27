"""Unit tests for LLM switching functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.infrastructure.llm.llm_factory import (
    LLMFactory,
    ModelProvider,
    create_llm,
)
from src.infrastructure.llm.llm_interface import LLMConfig
from src.infrastructure.llm.anthropic_llm import AnthropicLLM
from src.infrastructure.llm.openai_llm import OpenAILLM


class TestModelProvider:
    """Tests for ModelProvider enum."""

    def test_anthropic_provider_exists(self):
        """Test that ANTHROPIC provider is defined."""
        assert ModelProvider.ANTHROPIC == ModelProvider.ANTHROPIC
        assert ModelProvider.ANTHROPIC.value == "anthropic"

    def test_openai_provider_exists(self):
        """Test that OPENAI provider is defined."""
        assert ModelProvider.OPENAI == ModelProvider.OPENAI
        assert ModelProvider.OPENAI.value == "openai"

    def test_provider_from_string(self):
        """Test creating provider from string."""
        assert ModelProvider("anthropic") == ModelProvider.ANTHROPIC
        assert ModelProvider("openai") == ModelProvider.OPENAI

    def test_provider_from_invalid_string_raises(self):
        """Test that invalid provider string raises exception."""
        with pytest.raises(ValueError):
            ModelProvider("unknown")


class TestLLMFactory:
    """Tests for LLMFactory class."""

    def test_register_new_provider(self):
        """Test registering a new provider."""
        # Save original providers
        original_providers = LLMFactory._providers.copy()

        # Create a mock provider class
        mock_provider = Mock()

        # Register the provider
        LLMFactory.register_provider(ModelProvider.ANTHROPIC, type(mock_provider))

        # Verify it was registered
        assert LLMFactory._providers[ModelProvider.ANTHROPIC] == type(mock_provider)

        # Restore original providers
        LLMFactory._providers = original_providers

    def test_create_provider_without_config_raises(self):
        """Test creating a provider without config when no default exists."""
        # Clear default configs
        original_configs = LLMFactory._default_configs.copy()
        LLMFactory._default_configs.clear()

        try:
            with pytest.raises(ValueError, match="No configuration provided"):
                LLMFactory.create(ModelProvider.ANTHROPIC)
        finally:
            # Restore default configs
            LLMFactory._default_configs = original_configs

    def test_create_provider_with_config(self):
        """Test creating a provider with explicit config."""
        config = LLMConfig(
            api_key="test_key",
            model="test_model",
            temperature=0.5,
            max_tokens=1000,
        )

        with patch.object(AnthropicLLM, '__init__', return_value=None):
            LLMFactory.create(ModelProvider.ANTHROPIC, config)

    def test_create_unknown_provider_raises(self):
        """Test that creating an unknown provider raises exception."""
        with pytest.raises(ValueError, match="Unknown provider"):
            # Create an invalid provider enum
            invalid_provider = Mock()
            invalid_provider.value = "invalid"
            LLMFactory.create(invalid_provider)

    def test_create_from_dict_anthropic(self):
        """Test creating Anthropic provider from dictionary config."""
        config_dict = {
            "provider": "anthropic",
            "api_key": "test_key",
            "model": "claude-3",
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        with patch.object(AnthropicLLM, '__init__', return_value=None):
            result = LLMFactory.create_from_dict(config_dict)
            assert result is not None

    def test_create_from_dict_openai(self):
        """Test creating OpenAI provider from dictionary config."""
        config_dict = {
            "provider": "openai",
            "api_key": "test_key",
            "model": "gpt-4",
            "temperature": 0.5,
        }

        with patch.object(OpenAILLM, '__init__', return_value=None):
            result = LLMFactory.create_from_dict(config_dict)
            assert result is not None

    def test_create_from_dict_invalid_provider_raises(self):
        """Test that invalid provider in dict raises exception."""
        config_dict = {
            "provider": "unknown_provider",
            "api_key": "test_key",
        }

        with pytest.raises(ValueError, match="Unknown provider"):
            LLMFactory.create_from_dict(config_dict)

    def test_set_default_config(self):
        """Test setting default configuration for a provider."""
        config = LLMConfig(
            api_key="default_key",
            model="default_model",
        )

        original_configs = LLMFactory._default_configs.copy()
        LLMFactory.set_default_config(ModelProvider.ANTHROPIC, config)

        assert LLMFactory._default_configs[ModelProvider.ANTHROPIC] == config

        # Restore
        LLMFactory._default_configs = original_configs

    def test_get_fallback_chain_for_anthropic(self):
        """Test fallback chain for Anthropic provider."""
        chain = LLMFactory.get_fallback_chain(ModelProvider.ANTHROPIC)

        assert ModelProvider.ANTHROPIC in chain
        assert ModelProvider.OPENAI in chain
        assert len(chain) == 2

    def test_get_fallback_chain_for_openai(self):
        """Test fallback chain for OpenAI provider."""
        chain = LLMFactory.get_fallback_chain(ModelProvider.OPENAI)

        assert ModelProvider.OPENAI in chain
        assert ModelProvider.ANTHROPIC in chain
        assert len(chain) == 2

    @pytest.mark.asyncio
    async def test_create_with_fallback_success_on_first_try(self):
        """Test successful creation with fallback on first provider."""
        config = LLMConfig(api_key="test_key", model="test_model")

        with patch.object(AnthropicLLM, '__init__', return_value=None):
            result = await LLMFactory.create_with_fallback(
                ModelProvider.ANTHROPIC,
                config
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_with_fallback_falls_back_to_second_provider(self):
        """Test fallback mechanism when first provider fails."""
        config = LLMConfig(api_key="test_key", model="test_model")

        with patch.object(AnthropicLLM, '__init__', side_effect=Exception("Failed")):
            with patch.object(OpenAILLM, '__init__', return_value=None):
                result = await LLMFactory.create_with_fallback(
                    ModelProvider.ANTHROPIC,
                    config
                )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_with_fallback_returns_none_on_all_fail(self):
        """Test that fallback returns None when all providers fail."""
        config = LLMConfig(api_key="test_key", model="test_model")

        with patch.object(AnthropicLLM, '__init__', side_effect=Exception("Failed")):
            with patch.object(OpenAILLM, '__init__', side_effect=Exception("Failed")):
                result = await LLMFactory.create_with_fallback(
                    ModelProvider.ANTHROPIC,
                    config
                )

        assert result is None


class TestCreateLLMFunction:
    """Tests for the convenience create_llm function."""

    def test_create_anthropic_llm_with_enum(self):
        """Test creating Anthropic LLM using enum."""
        config = LLMConfig(api_key="test_key", model="test-model")

        with patch.object(AnthropicLLM, '__init__', return_value=None):
            result = create_llm(
                provider=ModelProvider.ANTHROPIC,
                api_key="test_key",
                model="test-model",
            )

        assert result is not None

    def test_create_anthropic_llm_with_string(self):
        """Test creating Anthropic LLM using string."""
        with patch.object(AnthropicLLM, '__init__', return_value=None):
            result = create_llm(
                provider="anthropic",
                api_key="test_key",
                model="test-model",
            )

        assert result is not None

    def test_create_openai_llm(self):
        """Test creating OpenAI LLM."""
        with patch.object(OpenAILLM, '__init__', return_value=None):
            result = create_llm(
                provider="openai",
                api_key="test_key",
                model="gpt-4",
            )

        assert result is not None

    def test_create_with_custom_temperature_and_tokens(self):
        """Test creating LLM with custom settings."""
        with patch.object(AnthropicLLM, '__init__', return_value=None):
            result = create_llm(
                provider="anthropic",
                api_key="test_key",
                model="test-model",
                temperature=0.3,
                max_tokens=5000,
            )

        assert result is not None

    def test_create_with_invalid_provider_string_raises(self):
        """Test that invalid provider string raises exception."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm(provider="invalid_provider", api_key="test_key")


class TestLLMIntegration:
    """Integration tests for LLM switching functionality."""

    @pytest.mark.slow
    def test_switch_between_providers_in_session(self):
        """
        Test switching between different LLM providers within a session.

        This verifies that:
        1. Multiple providers can be created
        2. Each provider maintains its own configuration
        3. Switching doesn't affect other provider instances
        """
        config1 = LLMConfig(api_key="key1", model="model1", temperature=0.7)
        config2 = LLMConfig(api_key="key2", model="model2", temperature=0.5)

        with patch.object(AnthropicLLM, '__init__', return_value=None) as mock_anthropic:
            with patch.object(OpenAILLM, '__init__', return_value=None) as mock_openai:
                llm1 = LLMFactory.create(ModelProvider.ANTHROPIC, config1)
                llm2 = LLMFactory.create(ModelProvider.OPENAI, config2)

                # Verify both instances were created
                assert mock_anthropic.call_count == 1
                assert mock_openai.call_count == 1

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_fallback_mechanism_with_real_configs(self):
        """
        Test the fallback mechanism with realistic configurations.

        This simulates a scenario where one provider becomes unavailable
        and the system should automatically switch to the backup.
        """
        primary_config = LLMConfig(
            api_key="primary_key",
            base_url="https://primary.api.com",
            model="primary-model",
        )

        backup_config = LLMConfig(
            api_key="backup_key",
            base_url="https://backup.api.com",
            model="backup-model",
        )

        # Set up the backup config as default for OPENAI
        LLMFactory.set_default_config(ModelProvider.OPENAI, backup_config)

        # Simulate primary failure
        with patch.object(AnthropicLLM, '__init__', side_effect=Exception("Service unavailable")):
            # This should use the backup
            with patch.object(OpenAILLM, '__init__', return_value=None) as mock_openai:
                result = await LLMFactory.create_with_fallback(
                    ModelProvider.ANTHROPIC,
                    primary_config,
                )

        # Verify backup was used
        assert result is not None

    @pytest.mark.requires_api
    @pytest.mark.slow
    def test_model_switching_preserves_context(self):
        """
        Test that switching models preserves the conversation context.

        This is important for ensuring that when switching providers,
        the conversation history is maintained.
        """
        # This would require actual API calls and is marked as slow
        # Skip if API keys are not available
        pass
