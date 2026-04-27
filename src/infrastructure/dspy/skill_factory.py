"""
Skill Factory - Creates skill instances from definitions.

The SkillFactory is responsible for:
- Creating skill instances from definitions
- Instantiating the correct signature class
- Configuring model providers
- Wiring up knowledge bases
"""

import logging
from typing import Optional, Dict, Type

from .base_skill import BaseSkill, SkillConfig, SimpleSkill
from .skill_registry import SkillDefinition
from .signatures.base import BaseSignature, SignatureRegistry
from ..llm import LLMFactory, ModelProvider

logger = logging.getLogger(__name__)


class SkillFactory:
    """
    Factory for creating skill instances.

    Supports:
    - Creating from database definitions
    - Creating from configuration dictionaries
    - Creating with custom signatures
    """

    # Pre-registered signature classes
    _signature_classes: Dict[str, Type[BaseSignature]] = {}

    @classmethod
    def register_signature(cls, name: str, signature_class: Type[BaseSignature]) -> None:
        """
        Register a signature class.

        Args:
            name: Unique name for the signature
            signature_class: Signature class to register
        """
        cls._signature_classes[name] = signature_class
        SignatureRegistry.register(name, signature_class)
        logger.info(f"Registered signature: {name}")

    @classmethod
    def create_from_definition(cls, definition: SkillDefinition) -> Optional[BaseSkill]:
        """
        Create a skill instance from a definition.

        Args:
            definition: Skill definition

        Returns:
            Skill instance or None if creation failed
        """
        try:
            # Get signature class
            signature_class = cls._get_signature_class(definition.signature_name)

            # Apply custom prompt if provided
            if definition.prompt_template or definition.system_prompt:
                signature_class = cls._create_custom_signature(
                    base_class=signature_class,
                    prompt_template=definition.prompt_template,
                    system_prompt=definition.system_prompt,
                )

            # Get model provider
            model_provider = ModelProvider(definition.model_provider)

            # Create skill config
            config = SkillConfig(
                name=definition.name,
                description=definition.description,
                signature_class=signature_class,
                model_provider=model_provider,
                model_config=definition.model_config,
                enabled=definition.enabled,
                intent_keywords=definition.intent_keywords,
                knowledge_base_ids=definition.knowledge_base_ids,
            )

            # Create LLM instance with custom config
            llm = cls._create_llm(model_provider, definition.model_config)

            # Create skill instance
            skill = cls._create_skill_instance(config, llm)

            logger.info(f"Created skill: {definition.name}")
            return skill

        except Exception as e:
            logger.error(f"Failed to create skill '{definition.name}': {e}")
            return None

    @classmethod
    def create_from_config(cls, config: dict) -> Optional[BaseSkill]:
        """
        Create a skill instance from a configuration dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            Skill instance or None
        """
        definition = SkillDefinition(
            id=config.get("id", config["name"]),
            name=config["name"],
            description=config.get("description", ""),
            signature_name=config.get("signature_name", "default"),
            model_provider=config.get("model_provider", "anthropic"),
            model_config=config.get("model_config", {}),
            enabled=config.get("enabled", True),
            intent_keywords=config.get("intent_keywords", []),
            knowledge_base_ids=config.get("knowledge_base_ids", []),
            prompt_template=config.get("prompt_template"),
            system_prompt=config.get("system_prompt"),
        )

        return cls.create_from_definition(definition)

    @classmethod
    def create_simple_skill(
        cls,
        name: str,
        description: str,
        system_prompt: str,
        model_provider: str = "anthropic",
        enabled: bool = True,
    ) -> SimpleSkill:
        """
        Create a simple skill with minimal configuration.

        Args:
            name: Skill name
            description: Skill description
            system_prompt: System prompt for the LLM
            model_provider: Model provider name
            enabled: Whether the skill is enabled

        Returns:
            SimpleSkill instance
        """
        return SimpleSkill(
            name=name,
            description=description,
            system_prompt=system_prompt,
            model_provider=ModelProvider(model_provider),
            enabled=enabled,
        )

    @classmethod
    def _get_signature_class(cls, signature_name: str) -> Type[BaseSignature]:
        """
        Get a signature class by name.

        Args:
            signature_name: Name of the signature

        Returns:
            Signature class

        Raises:
            ValueError: If signature not found
        """
        if signature_name in cls._signature_classes:
            return cls._signature_classes[signature_name]

        # Try to get from SignatureRegistry
        signature_class = SignatureRegistry.get(signature_name)
        if signature_class:
            return signature_class

        raise ValueError(f"Unknown signature: {signature_name}")

    @classmethod
    def _create_custom_signature(
        cls,
        base_class: Type[BaseSignature],
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Type[BaseSignature]:
        """
        Create a custom signature class with overrides.

        Args:
            base_class: Base signature class
            prompt_template: Custom prompt template
            system_prompt: Custom system prompt

        Returns:
            New signature class
        """
        class_dict = {}

        if system_prompt:
            class_dict["system_prompt"] = system_prompt

        if prompt_template:
            class_dict["prompt_template"] = prompt_template

        # Create new class inheriting from base
        class_name = f"Custom{base_class.__name__}"
        return type(class_name, (base_class,), class_dict)

    @classmethod
    def _create_llm(cls, provider: ModelProvider, config: dict):
        """
        Create an LLM instance with the given configuration.

        Args:
            provider: Model provider
            config: Model configuration dictionary

        Returns:
            LLMInterface instance
        """
        from ..llm import LLMConfig

        llm_config = LLMConfig(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url"),
            model=config.get("model", "default"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2000),
        )

        return LLMFactory.create(provider, llm_config)

    @classmethod
    def _create_skill_instance(cls, config: SkillConfig, llm) -> BaseSkill:
        """
        Create a skill instance.

        Args:
            config: Skill configuration
            llm: LLM instance to use

        Returns:
            BaseSkill instance
        """
        return BaseSkill(config=config, llm=llm)


# Register default signatures
def _register_default_signatures() -> None:
    """Register the built-in signature classes."""
    from .signatures.four_highs import (
        HealthAssessmentSignature,
        RiskPredictionSignature,
        HypertensionAssessmentSignature,
        DiabetesAssessmentSignature,
        DyslipidemiaAssessmentSignature,
        GoutAssessmentSignature,
        ObesityAssessmentSignature,
    )
    from .signatures.prescription import (
        DietPrescriptionSignature,
        ExercisePrescriptionSignature,
        SleepPrescriptionSignature,
        MedicationPrescriptionSignature,
    )

    signatures = [
        ("health_assessment", HealthAssessmentSignature),
        ("risk_prediction", RiskPredictionSignature),
        ("hypertension_assessment", HypertensionAssessmentSignature),
        ("diabetes_assessment", DiabetesAssessmentSignature),
        ("dyslipidemia_assessment", DyslipidemiaAssessmentSignature),
        ("gout_assessment", GoutAssessmentSignature),
        ("obesity_assessment", ObesityAssessmentSignature),
        ("diet_prescription", DietPrescriptionSignature),
        ("exercise_prescription", ExercisePrescriptionSignature),
        ("sleep_prescription", SleepPrescriptionSignature),
        ("medication_prescription", MedicationPrescriptionSignature),
    ]

    for name, sig_class in signatures:
        SkillFactory.register_signature(name, sig_class)


# Auto-register on import
_register_default_signatures()
