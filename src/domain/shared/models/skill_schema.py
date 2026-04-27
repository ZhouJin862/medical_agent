"""
Unified SKILL.md Format Schema

Defines the standard format for Claude Skills SKILL.md files.
This schema ensures consistency across all skills in the system.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from pathlib import Path


class ExecutionType(str, Enum):
    """Skill execution type."""
    WORKFLOW = "workflow"    # Executes defined scripts/steps
    PROMPT = "prompt"        # LLM generates response from skill content
    COMPOSITE = "composite"  # Combines multiple base skills


class SkillLayer(str, Enum):
    """Progressive disclosure layer."""
    BASIC = "basic"         # Layer 1: Always available
    DOMAIN = "domain"       # Layer 2: Domain-specific
    COMPOSITE = "composite" # Layer 3: Complex workflows


class OutputFormat(str, Enum):
    """Output format type."""
    STRUCTURED = "structured"  # JSON/structured output
    TEXT = "text"             # Plain text response
    MIXED = "mixed"           # Combination of both


class RelationshipType(str, Enum):
    """Relationship type between skills."""
    INDEPENDENT = "independent"    # Can execute in parallel
    SEQUENTIAL = "sequential"      # Must execute in order
    COMPLEMENTARY = "complementary" # Enhances each other
    ALTERNATIVE = "alternative"     # Alternative option


@dataclass
class TriggerConfig:
    """Skill trigger configuration."""
    keywords: List[str] = field(default_factory=list)
    intent_patterns: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.7

    def matches(self, user_input: str) -> bool:
        """Check if user input matches triggers."""
        import re
        user_lower = user_input.lower()

        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in user_lower:
                return True

        # Check intent patterns
        for pattern in self.intent_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return True

        return False


@dataclass
class DependencySpec:
    """Skill dependency specification."""
    python: Optional[str] = None  # Python version requirement
    packages: List[str] = field(default_factory=list)  # Required packages
    mcp_servers: List[str] = field(default_factory=list)  # MCP server dependencies
    skills: List[str] = field(default_factory=list)  # Other skill dependencies


@dataclass
class OutputSpec:
    """Output specification."""
    format: OutputFormat = OutputFormat.STRUCTURED
    schema: Optional[Dict[str, Any]] = None  # JSON schema for structured output
    template: Optional[str] = None  # Template for text output


@dataclass
class SkillRelationship:
    """Relationship with another skill."""
    skill: str  # Target skill name
    relationship_type: RelationshipType
    trigger_condition: Optional[str] = None  # When to trigger this relationship
    context_transfer: List[str] = field(default_factory=list)  # Fields to pass


@dataclass
class SkillFrontmatter:
    """
    Unified SKILL.md frontmatter schema.

    This defines all possible fields in the YAML frontmatter.
    Required fields are marked with required=True in validation.
    """
    # Required fields
    name: str  # Unique skill identifier (kebab-case)
    description: str  # Human-readable description with trigger words

    # Basic metadata
    display_name: Optional[str] = None  # Display name (defaults to name)
    version: str = "1.0.0"
    author: Optional[str] = None
    license: str = "MIT"
    enabled: bool = True

    # Execution configuration
    execution_type: ExecutionType = ExecutionType.PROMPT
    layer: SkillLayer = SkillLayer.DOMAIN
    priority: int = 10  # Higher = more priority

    # Trigger configuration
    triggers: TriggerConfig = field(default_factory=TriggerConfig)

    # Dependencies
    requires: DependencySpec = field(default_factory=DependencySpec)

    # Output specification
    output: OutputSpec = field(default_factory=OutputSpec)

    # Skill relationships (for multi-skill orchestration)
    complementary_skills: List[SkillRelationship] = field(default_factory=list)
    alternative_skills: List[SkillRelationship] = field(default_factory=list)
    required_skills: List[SkillRelationship] = field(default_factory=list)
    can_combine_with: List[str] = field(default_factory=list)

    # Legacy support (deprecated)
    tags: List[str] = field(default_factory=list)
    dependency: Optional[Dict[str, Any]] = None  # Old format
    mcp_tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "license": self.license,
            "enabled": self.enabled,
        }

        # Optional fields
        if self.display_name:
            result["display_name"] = self.display_name
        if self.author:
            result["author"] = self.author

        # Execution config
        result["execution_type"] = self.execution_type.value
        result["layer"] = self.layer.value
        result["priority"] = self.priority

        # Triggers
        if self.triggers.keywords or self.triggers.intent_patterns:
            result["triggers"] = {
                "keywords": self.triggers.keywords,
                "intent_patterns": self.triggers.intent_patterns,
                "confidence_threshold": self.triggers.confidence_threshold,
            }

        # Dependencies
        if self.requires.python or self.requires.packages:
            result["requires"] = {}
            if self.requires.python:
                result["requires"]["python"] = self.requires.python
            if self.requires.packages:
                result["requires"]["packages"] = self.requires.packages
            if self.requires.mcp_servers:
                result["requires"]["mcp_servers"] = self.requires.mcp_servers
            if self.requires.skills:
                result["requires"]["skills"] = self.requires.skills

        # Output
        if self.output.format != OutputFormat.STRUCTURED or self.output.schema:
            result["output"] = {
                "format": self.output.format.value,
            }
            if self.output.schema:
                result["output"]["schema"] = self.output.schema
            if self.output.template:
                result["output"]["template"] = self.output.template

        # Relationships
        if self.complementary_skills:
            result["complementary_skills"] = [
                {
                    "skill": r.skill,
                    "relationship_type": r.relationship_type.value,
                    "trigger_condition": r.trigger_condition,
                    "context_transfer": r.context_transfer,
                }
                for r in self.complementary_skills
            ]

        if self.alternative_skills:
            result["alternative_skills"] = [
                {
                    "skill": r.skill,
                    "relationship_type": r.relationship_type.value,
                }
                for r in self.alternative_skills
            ]

        if self.required_skills:
            result["requires_skills"] = [
                {
                    "skill": r.skill,
                    "when": r.trigger_condition,
                }
                for r in self.required_skills
            ]

        if self.can_combine_with:
            result["can_combine_with"] = self.can_combine_with

        # Legacy support
        if self.tags:
            result["tags"] = self.tags
        if self.dependency:
            result["dependency"] = self.dependency
        if self.mcp_tools:
            result["mcp_tools"] = self.mcp_tools
        if self.dependencies:
            result["dependencies"] = self.dependencies

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillFrontmatter":
        """Create from dictionary (parsed YAML)."""
        # Handle legacy format conversion
        triggers_data = data.get("triggers", {})
        if not triggers_data:
            # Extract triggers from description for legacy format
            keywords = cls._extract_keywords_from_description(data.get("description", ""))
            # Use tags if available
            keywords.extend(data.get("tags", []))
            triggers_data = {
                "keywords": keywords,
                "intent_patterns": [],
                "confidence_threshold": 0.7,
            }

        # Handle legacy dependency format
        requires = DependencySpec()
        if "requires" in data:
            requires_data = data["requires"]
            if isinstance(requires_data, dict):
                requires = DependencySpec(
                    python=requires_data.get("python"),
                    packages=requires_data.get("packages", []),
                    mcp_servers=requires_data.get("mcp_servers", []),
                    skills=requires_data.get("skills", []),
                )
        elif "dependency" in data:
            # Convert old dependency format
            dep_data = data["dependency"]
            if isinstance(dep_data, dict) and "python" in dep_data:
                requires = DependencySpec(
                    packages=dep_data["python"],
                )

        # Handle output spec
        output_data = data.get("output", {})
        output = OutputSpec(
            format=OutputFormat(output_data.get("format", "structured")),
            schema=output_data.get("schema"),
            template=output_data.get("template"),
        )

        # Handle relationships
        complementary_skills = []
        for rel in data.get("complementary_skills", []):
            if isinstance(rel, dict):
                complementary_skills.append(SkillRelationship(
                    skill=rel["skill"],
                    relationship_type=RelationshipType(rel.get("relationship_type", "complementary")),
                    trigger_condition=rel.get("trigger_condition"),
                    context_transfer=rel.get("context_transfer", []),
                ))

        alternative_skills = []
        for rel in data.get("alternative_skills", []):
            if isinstance(rel, dict):
                alternative_skills.append(SkillRelationship(
                    skill=rel["skill"],
                    relationship_type=RelationshipType(rel.get("relationship_type", "alternative")),
                ))

        required_skills = []
        for rel in data.get("required_skills", []):
            if isinstance(rel, dict):
                required_skills.append(SkillRelationship(
                    skill=rel["skill"],
                    relationship_type=RelationshipType.SEQUENTIAL,
                    trigger_condition=rel.get("when"),
                ))

        return cls(
            name=data["name"],
            description=data["description"],
            display_name=data.get("display_name"),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            license=data.get("license", "MIT"),
            enabled=data.get("enabled", True),
            execution_type=ExecutionType(data.get("execution_type", "prompt")),
            layer=SkillLayer(data.get("layer", "domain")),
            priority=data.get("priority", 10),
            triggers=TriggerConfig(**triggers_data) if isinstance(triggers_data, dict) else TriggerConfig(),
            requires=requires,
            output=output,
            complementary_skills=complementary_skills,
            alternative_skills=alternative_skills,
            required_skills=required_skills,
            can_combine_with=data.get("can_combine_with", []),
            # Legacy
            tags=data.get("tags", []),
            dependency=data.get("dependency"),
            mcp_tools=data.get("mcp_tools", []),
            dependencies=data.get("dependencies", []),
        )

    @staticmethod
    def _extract_keywords_from_description(description: str) -> List[str]:
        """Extract trigger keywords from description."""
        keywords = []
        desc_lower = description.lower()

        # Check for common trigger words
        trigger_patterns = [
            r"触发词[：:]\s*([^\n。]+)",
            r"触发[条件词][：:]\s*([^\n。]+)",
            r"keywords?[：:]\s*([^\n。]+)",
        ]

        import re
        for pattern in trigger_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                keyword_str = match.group(1)
                # Split by common separators
                keywords.extend([k.strip() for k in re.split(r'[,，、\s]+', keyword_str) if k.strip()])
                break

        return keywords

    def validate(self) -> List[str]:
        """Validate frontmatter and return list of errors."""
        errors = []

        # Required fields
        if not self.name:
            errors.append("Missing required field: name")
        if not self.description:
            errors.append("Missing required field: description")

        # Name format
        if self.name and not self._is_kebab_case(self.name):
            errors.append(f"name must be kebab-case: {self.name}")

        # Version format
        if self.version and not self._is_valid_version(self.version):
            errors.append(f"Invalid version format: {self.version}")

        # Priority range
        if self.priority < 0 or self.priority > 100:
            errors.append(f"priority must be 0-100: {self.priority}")

        # Confidence threshold
        if self.triggers.confidence_threshold < 0 or self.triggers.confidence_threshold > 1:
            errors.append(f"confidence_threshold must be 0-1: {self.triggers.confidence_threshold}")

        return errors

    @staticmethod
    def _is_kebab_case(name: str) -> bool:
        """Check if name is kebab-case."""
        import re
        return bool(re.match(r'^[a-z][a-z0-9-]*$', name))

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """Check if version is valid semver."""
        import re
        return bool(re.match(r'^\d+\.\d+\.\d+', version))


# Default frontmatter template for new skills
DEFAULT_SKILL_FRONTMATTER = """---
name: {skill_name}
display_name: {display_name}
description: |
  {description}

  触发词：{trigger_keywords}

version: "1.0.0"
author: {author}
license: MIT
enabled: true

# Execution configuration
execution_type: {execution_type}  # workflow | prompt | composite
layer: domain  # basic | domain | composite
priority: 10

# Trigger configuration
triggers:
  keywords:
    - {keyword_1}
    - {keyword_2}
  intent_patterns: []
  confidence_threshold: 0.7

# Dependencies
requires:
  python: ">=3.10"
  packages: []
  mcp_servers: []
  skills: []

# Output specification
output:
  format: structured  # structured | text | mixed
  schema: null

# Skill relationships (optional)
complementary_skills: []
alternative_skills: []
required_skills: []
can_combine_with: []
---
"""


def create_skill_frontmatter_template(
    skill_name: str,
    display_name: str,
    description: str,
    trigger_keywords: List[str],
    execution_type: ExecutionType = ExecutionType.PROMPT,
    author: str = "medical-agent",
) -> str:
    """Create a SKILL.md frontmatter template."""
    return DEFAULT_SKILL_FRONTMATTER.format(
        skill_name=skill_name,
        display_name=display_name,
        description=description,
        trigger_keywords="、".join(trigger_keywords),
        keyword_1=trigger_keywords[0] if trigger_keywords else "keyword1",
        keyword_2=trigger_keywords[1] if len(trigger_keywords) > 1 else "keyword2",
        execution_type=execution_type.value,
        author=author,
    )
