"""
Claude Skills data models.

Defines the data structures for Claude Agent Skills,
including metadata, definitions, and execution results.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum


class SkillSource(str, Enum):
    """Skill storage source."""
    FILE = "file"           # Claude Skills (file system)
    DATABASE = "database"   # Database skills (legacy)


class SkillLayer(str, Enum):
    """Progressive disclosure layer."""
    BASIC = "basic"         # Layer 1: Always available
    DOMAIN = "domain"       # Layer 2: Domain-specific
    COMPOSITE = "composite" # Layer 3: Complex workflows


@dataclass
class SkillMetadata:
    """
    Skill metadata from YAML frontmatter.

    This is the only information loaded at startup,
    enabling efficient progressive disclosure.
    """
    name: str
    description: str
    directory: Path
    source: SkillSource = SkillSource.FILE
    enabled: bool = True
    version: str = "1.0.0"
    layer: SkillLayer = SkillLayer.DOMAIN

    # Frontmatter extensions
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Ensure directory is a Path object."""
        if isinstance(self.directory, str):
            self.directory = Path(self.directory)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source.value,
            "enabled": self.enabled,
            "version": self.version,
            "layer": self.layer.value,
            "author": self.author,
            "tags": self.tags,
            "requires": self.requires,
        }


@dataclass
class SkillDefinition:
    """
    Complete skill definition with all content.

    Only loaded when the skill is actually needed.
    """
    metadata: SkillMetadata
    content: str
    reference_files: List[str] = field(default_factory=list)
    examples_files: List[str] = field(default_factory=list)
    scripts: List[str] = field(default_factory=list)

    # Parsed frontmatter extensions
    dependencies: List[str] = field(default_factory=list)
    mcp_tools: List[str] = field(default_factory=list)

    def get_reference_path(self, filename: str) -> Path:
        """Get full path to a reference file."""
        return self.metadata.directory / "reference" / filename

    def get_script_path(self, filename: str) -> Path:
        """Get full path to a script file."""
        return self.metadata.directory / "scripts" / filename

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "metadata": self.metadata.to_dict(),
            "content": self.content,
            "reference_files": self.reference_files,
            "examples_files": self.examples_files,
            "scripts": self.scripts,
            "dependencies": self.dependencies,
            "mcp_tools": self.mcp_tools,
        }


@dataclass
class SkillExecutionRequest:
    """Request to execute a skill script."""
    skill_name: str
    script_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    patient_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillExecutionResult:
    """Result of skill execution."""
    success: bool
    skill_name: str
    output: Optional[str] = None
    error: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None
    execution_time_ms: int = 0
    files_created: List[str] = field(default_factory=list)
    reference_files_loaded: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "success": self.success,
            "skill_name": self.skill_name,
            "output": self.output,
            "error": self.error,
            "structured_output": self.structured_output,
            "execution_time_ms": self.execution_time_ms,
            "files_created": self.files_created,
            "reference_files_loaded": self.reference_files_loaded,
        }


@dataclass
class SkillReferenceContent:
    """Content of a reference file."""
    filename: str
    content: str
    skill_name: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "filename": self.filename,
            "content": self.content,
            "skill_name": self.skill_name,
        }
