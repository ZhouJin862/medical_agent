"""
Unified SKILL.md Frontmatter Parser

Handles parsing and validation of SKILL.md frontmatter
using the unified schema defined in skill_schema.py.
"""
import logging
import yaml
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

from src.domain.shared.models.skill_schema import (
    SkillFrontmatter,
    ExecutionType,
    SkillLayer,
    TriggerConfig,
    DependencySpec,
    OutputSpec,
    OutputFormat,
    SkillRelationship,
    RelationshipType,
)
from src.domain.shared.models.skill_models import SkillMetadata, SkillDefinition, SkillSource

logger = logging.getLogger(__name__)


class SkillFrontmatterParser:
    """
    Parser for unified SKILL.md frontmatter format.

    Handles:
    - Parsing YAML frontmatter
    - Validation using unified schema
    - Legacy format compatibility
    - Error reporting
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the parser.

        Args:
            strict_mode: If True, reject invalid skills. If False, log warnings but continue.
        """
        self.strict_mode = strict_mode
        self._parse_errors: List[str] = []

    def parse(
        self,
        skill_md_path: Path,
        load_full_definition: bool = False
    ) -> Tuple[Optional[SkillFrontmatter], Optional[SkillMetadata], Optional[SkillDefinition]]:
        """
        Parse a SKILL.md file and extract frontmatter, metadata, and definition.

        Args:
            skill_md_path: Path to SKILL.md file
            load_full_definition: Whether to load full definition (including content)

        Returns:
            Tuple of (frontmatter, metadata, definition)
            - frontmatter: Parsed SkillFrontmatter object
            - metadata: SkillMetadata for progressive disclosure
            - definition: Full SkillDefinition (only if load_full_definition=True)
        """
        self._parse_errors.clear()

        if not skill_md_path.exists():
            error = f"SKILL.md not found: {skill_md_path}"
            logger.error(error)
            self._parse_errors.append(error)
            return None, None, None

        try:
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter
            frontmatter_dict, body_start = self._parse_frontmatter_yaml(content)

            if not frontmatter_dict:
                error = f"No valid frontmatter found in: {skill_md_path}"
                logger.error(error)
                self._parse_errors.append(error)
                return None, None, None

            # Create unified frontmatter object
            frontmatter = SkillFrontmatter.from_dict(frontmatter_dict)

            # Validate frontmatter
            validation_errors = frontmatter.validate()
            self._parse_errors.extend(validation_errors)

            if validation_errors and self.strict_mode:
                logger.error(f"Validation errors in {skill_md_path}: {validation_errors}")
                return None, None, None

            # Extract skill directory from SKILL.md path
            skill_dir = skill_md_path.parent

            # Create metadata (for progressive disclosure)
            metadata = self._create_metadata(frontmatter, skill_dir)

            # Create full definition if requested
            definition = None
            if load_full_definition:
                definition = self._create_definition(
                    frontmatter,
                    metadata,
                    content[body_start:] if body_start > 0 else content
                )

            return frontmatter, metadata, definition

        except Exception as e:
            error = f"Error parsing SKILL.md {skill_md_path}: {e}"
            logger.error(error)
            self._parse_errors.append(error)
            return None, None, None

    def get_parse_errors(self) -> List[str]:
        """Get list of parse errors from last parse operation."""
        return self._parse_errors.copy()

    def _parse_frontmatter_yaml(self, content: str) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Full markdown content

        Returns:
            Tuple of (frontmatter dict, body start position)
        """
        if not content.startswith('---'):
            return None, 0

        # Find end of frontmatter
        end = content.find('---', 3)
        if end == -1:
            return None, 0

        frontmatter_str = content[3:end].strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
            # Move past second ---
            body_start = end + 3
            # Skip leading newline after ---
            if body_start < len(content) and content[body_start] == '\n':
                body_start += 1
            return frontmatter, body_start
        except yaml.YAMLError as e:
            logger.error(f"Error parsing frontmatter YAML: {e}")
            self._parse_errors.append(f"YAML parse error: {e}")
            return None, 0

    def _create_metadata(
        self,
        frontmatter: SkillFrontmatter,
        skill_dir: Path
    ) -> SkillMetadata:
        """Create SkillMetadata from unified frontmatter."""
        # Convert trigger keywords to tags for backward compatibility
        tags = frontmatter.tags.copy()
        tags.extend(frontmatter.triggers.keywords)

        # Convert dependencies to requires format
        requires = []
        if frontmatter.requires.skills:
            requires.extend(frontmatter.requires.skills)
        if frontmatter.required_skills:
            requires.extend([r.skill for r in frontmatter.required_skills])

        return SkillMetadata(
            name=frontmatter.name,
            description=frontmatter.description,
            directory=skill_dir,
            source=SkillSource.FILE,
            enabled=frontmatter.enabled,
            version=frontmatter.version,
            layer=frontmatter.layer,
            author=frontmatter.author,
            tags=tags,
            requires=requires,
        )

    def _create_definition(
        self,
        frontmatter: SkillFrontmatter,
        metadata: SkillMetadata,
        body_content: str
    ) -> SkillDefinition:
        """Create full SkillDefinition from unified frontmatter and body content."""
        # Discover reference files
        reference_dir = metadata.directory / "reference"
        reference_files = []
        if reference_dir.exists():
            reference_files = sorted([
                f.name for f in reference_dir.glob("*.md")
                if not f.name.startswith('.')
            ])

        # Discover examples files
        examples_files = []
        for examples_file in metadata.directory.glob("examples*.md"):
            examples_files.append(examples_file.name)

        # Discover scripts
        scripts_dir = metadata.directory / "scripts"
        scripts = []
        if scripts_dir.exists():
            scripts = sorted([
                f.name for f in scripts_dir.glob("*.py")
                if not f.name.startswith('.')
            ])

        # Collect dependencies
        dependencies = frontmatter.requires.packages.copy()
        if frontmatter.dependencies:
            dependencies.extend(frontmatter.dependencies)

        # Collect MCP tools
        mcp_tools = frontmatter.requires.mcp_servers.copy()
        if frontmatter.mcp_tools:
            mcp_tools.extend(frontmatter.mcp_tools)

        return SkillDefinition(
            metadata=metadata,
            content=body_content,
            reference_files=reference_files,
            examples_files=examples_files,
            scripts=scripts,
            dependencies=dependencies,
            mcp_tools=mcp_tools,
        )

    def detect_execution_type(self, skill_dir: Path) -> ExecutionType:
        """
        Detect execution type from skill directory structure.

        Args:
            skill_dir: Path to skill directory

        Returns:
            Detected execution type
        """
        import re

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return ExecutionType.PROMPT

        content = skill_md.read_text(encoding='utf-8')

        # Check for workflow steps pattern
        if re.search(r'### 步骤\d+[:：]', content):
            return ExecutionType.WORKFLOW

        # Check for scripts directory with Python files
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            python_files = list(scripts_dir.glob("*.py"))
            if python_files:
                return ExecutionType.WORKFLOW

        # Check for composite indicators
        _, metadata, _ = self.parse(skill_md)
        if metadata and (metadata.requires or "composite" in metadata.layer.value):
            return ExecutionType.COMPOSITE

        return ExecutionType.PROMPT


def migrate_legacy_frontmatter(
    old_frontmatter: Dict[str, Any],
    skill_name: str
) -> SkillFrontmatter:
    """
    Migrate legacy frontmatter format to unified format.

    Args:
        old_frontmatter: Legacy frontmatter dictionary
        skill_name: Skill name for fallback

    Returns:
        Unified SkillFrontmatter object
    """
    # Extract description for keyword parsing
    description = old_frontmatter.get("description", "")

    # Handle old dependency format
    requires = DependencySpec()
    if "dependency" in old_frontmatter:
        dep_data = old_frontmatter["dependency"]
        if isinstance(dep_data, dict):
            if "python" in dep_data:
                requires.packages = dep_data["python"]
            if "mcp_servers" in dep_data:
                requires.mcp_servers = dep_data["mcp_servers"]

    # Handle old tags/keywords
    keywords = old_frontmatter.get("tags", []).copy()
    keywords.extend(SkillFrontmatter._extract_keywords_from_description(description))

    # Determine execution type
    execution_type = ExecutionType.PROMPT
    if old_frontmatter.get("execution_type"):
        execution_type = ExecutionType(old_frontmatter["execution_type"])

    return SkillFrontmatter(
        name=old_frontmatter.get("name", skill_name),
        description=description,
        display_name=old_frontmatter.get("display_name"),
        version=old_frontmatter.get("version", "1.0.0"),
        author=old_frontmatter.get("author"),
        license=old_frontmatter.get("license", "MIT"),
        enabled=old_frontmatter.get("enabled", True),
        execution_type=execution_type,
        layer=SkillLayer(old_frontmatter.get("layer", "domain")),
        priority=old_frontmatter.get("priority", 10),
        triggers=TriggerConfig(
            keywords=keywords,
            intent_patterns=[],
            confidence_threshold=0.7,
        ),
        requires=requires,
        output=OutputSpec(),
        tags=old_frontmatter.get("tags", []),
        dependency=old_frontmatter.get("dependency"),
        mcp_tools=old_frontmatter.get("mcp_tools", []),
        dependencies=old_frontmatter.get("dependencies", []),
    )


# Utility function for quick validation
def validate_skill_frontmatter(skill_md_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate a SKILL.md file's frontmatter.

    Args:
        skill_md_path: Path to SKILL.md file

    Returns:
        Tuple of (is_valid, error_messages)
    """
    parser = SkillFrontmatterParser(strict_mode=False)
    frontmatter, _, _ = parser.parse(skill_md_path)

    if frontmatter is None:
        return False, parser.get_parse_errors()

    errors = frontmatter.validate()
    return len(errors) == 0, errors


# Utility function to generate frontmatter template
def generate_skill_template(
    name: str,
    display_name: str,
    description: str,
    keywords: List[str],
    execution_type: ExecutionType = ExecutionType.PROMPT,
    author: str = "medical-agent",
) -> str:
    """
    Generate a SKILL.md frontmatter template.

    Args:
        name: Skill identifier (kebab-case)
        display_name: Human-readable name
        description: Skill description
        keywords: Trigger keywords
        execution_type: Execution type
        author: Author name

    Returns:
        YAML frontmatter string
    """
    frontmatter = SkillFrontmatter(
        name=name,
        description=description,
        display_name=display_name,
        version="1.0.0",
        author=author,
        license="MIT",
        enabled=True,
        execution_type=execution_type,
        layer=SkillLayer.DOMAIN,
        priority=10,
        triggers=TriggerConfig(
            keywords=keywords,
            intent_patterns=[],
            confidence_threshold=0.7,
        ),
        requires=DependencySpec(
            python=">=3.10",
            packages=[],
            mcp_servers=[],
            skills=[],
        ),
        output=OutputSpec(
            format=OutputFormat.STRUCTURED,
        ),
    )

    import yaml
    frontmatter_dict = frontmatter.to_dict()
    yaml_str = yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True)

    return f"---\n{yaml_str}---\n\n# {display_name}\n\n<!-- Add skill content here -->\n"
