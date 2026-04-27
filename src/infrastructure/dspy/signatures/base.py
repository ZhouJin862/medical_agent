"""
Base DSPy Signature for health assessment skills.

Provides the foundation for all skill signatures in the system.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Type, get_type_hints
from enum import Enum


class FieldType(Enum):
    """Types of signature fields."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    ARRAY = "array"


@dataclass
class InputField:
    """
    Defines an input field for a DSPy signature.

    Attributes:
        name: Field name
        description: Human-readable description
        field_type: Data type of the field
        required: Whether the field is required
        default: Default value if not provided
    """

    name: str
    description: str
    field_type: FieldType = FieldType.STRING
    required: bool = True
    default: Any = None


@dataclass
class OutputField:
    """
    Defines an output field for a DSPy signature.

    Attributes:
        name: Field name
        description: Human-readable description
        field_type: Data type of the field
        required: Whether the field is required
    """

    name: str
    description: str
    field_type: FieldType = FieldType.JSON
    required: bool = True


class BaseSignature:
    """
    Base class for all DSPy signatures.

    A signature defines:
    - What inputs a skill accepts
    - What outputs a skill produces
    - The prompt template for the skill
    """

    # Subclasses should define these
    input_fields: list[InputField] = field(default_factory=list)
    output_fields: list[OutputField] = field(default_factory=list)
    system_prompt: str = ""
    prompt_template: str = ""

    @classmethod
    def get_input_fields(cls) -> list[InputField]:
        """Get all input fields for this signature."""
        if hasattr(cls, "input_fields"):
            return cls.input_fields
        return []

    @classmethod
    def get_output_fields(cls) -> list[OutputField]:
        """Get all output fields for this signature."""
        if hasattr(cls, "output_fields"):
            return cls.output_fields
        return []

    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for this signature."""
        return getattr(cls, "system_prompt", "")

    @classmethod
    def get_prompt_template(cls) -> str:
        """Get the prompt template for this signature."""
        return getattr(cls, "prompt_template", "")

    @classmethod
    def format_prompt(cls, **kwargs) -> str:
        """
        Format the prompt template with provided values.

        Args:
            **kwargs: Values to substitute in the template

        Returns:
            Formatted prompt string
        """
        prompt = cls.get_prompt_template()

        # Add input descriptions to prompt
        input_desc = "\n".join(
            f"- {field.name}: {field.description}"
            for field in cls.get_input_fields()
        )

        # Add output descriptions to prompt
        output_desc = "\n".join(
            f"- {field.name}: {field.description}"
            for field in cls.get_output_fields()
        )

        full_prompt = f"""{cls.get_system_prompt()}

输入信息:
{input_desc}

输出要求:
{output_desc}

{prompt}"""

        # Substitute values
        try:
            return full_prompt.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required input value: {e}")

    @classmethod
    def validate_inputs(cls, **kwargs) -> bool:
        """
        Validate that all required inputs are provided.

        Args:
            **kwargs: Input values to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        for field in cls.get_input_fields():
            if field.required and field.name not in kwargs:
                raise ValueError(f"Missing required input: {field.name}")

            if field.name in kwargs:
                value = kwargs[field.name]
                if value is None:
                    raise ValueError(f"Input '{field.name}' cannot be None")

        return True

    @classmethod
    def get_output_schema(cls) -> dict:
        """
        Generate JSON schema for the expected output.

        Returns:
            JSON schema dictionary
        """
        properties = {}
        required = []

        for field in cls.get_output_fields():
            prop = {
                "description": field.description,
            }

            # Map field types to JSON schema types
            type_mapping = {
                FieldType.STRING: "string",
                FieldType.INTEGER: "integer",
                FieldType.FLOAT: "number",
                FieldType.BOOLEAN: "boolean",
                FieldType.JSON: "object",
                FieldType.ARRAY: "array",
            }

            prop["type"] = type_mapping.get(field.field_type, "object")

            properties[field.name] = prop

            if field.required:
                required.append(field.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class SignatureRegistry:
    """
    Registry for all DSPy signatures.

    Allows dynamic lookup and instantiation of signatures by name.
    """

    _signatures: dict[str, Type[BaseSignature]] = {}

    @classmethod
    def register(cls, name: str, signature_class: Type[BaseSignature]) -> None:
        """
        Register a signature class.

        Args:
            name: Unique name for the signature
            signature_class: Signature class to register
        """
        cls._signatures[name] = signature_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseSignature]]:
        """
        Get a signature class by name.

        Args:
            name: Signature name

        Returns:
            Signature class or None if not found
        """
        return cls._signatures.get(name)

    @classmethod
    def list_all(cls) -> list[str]:
        """Get list of all registered signature names."""
        return list(cls._signatures.keys())

    @classmethod
    def create_signature(
        cls, name: str, custom_fields: Optional[dict] = None
    ) -> Type[BaseSignature]:
        """
        Dynamically create a signature class.

        Args:
            name: Name for the new signature
            custom_fields: Optional dict with 'inputs', 'outputs', 'system_prompt', 'prompt_template'

        Returns:
            New signature class
        """
        if custom_fields is None:
            custom_fields = {}

        # Create a new class dynamically
        class_dict = {
            "input_fields": custom_fields.get("inputs", []),
            "output_fields": custom_fields.get("outputs", []),
            "system_prompt": custom_fields.get("system_prompt", ""),
            "prompt_template": custom_fields.get("prompt_template", ""),
        }

        new_class = type(f"{name}Signature", (BaseSignature,), class_dict)
        cls.register(name, new_class)

        return new_class
