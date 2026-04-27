"""
Claude Skills Registry Service.

Scans the skills directory, parses SKILL.md files,
and provides progressive disclosure access to skill content.
"""
import logging
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.domain.shared.models.skill_models import (
    SkillMetadata,
    SkillDefinition,
    SkillSource,
    SkillLayer,
)

logger = logging.getLogger(__name__)


class SkillsRegistry:
    """
    Claude Skills Registry.

    Implements progressive disclosure:
    1. Startup: Scan and cache only metadata (name + description)
    2. On-demand: Load full SKILL.md when skill is triggered
    3. As-needed: Load reference files only when referenced
    """

    def __init__(self, skills_dir: str = "skills"):
        """
        Initialize the skills registry.

        Args:
            skills_dir: Root directory containing skill subdirectories
        """
        self._skills_dir = Path(skills_dir)
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._definition_cache: Dict[str, SkillDefinition] = {}
        self._last_scan: Optional[datetime] = None

        # Validate directory
        if not self._skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self._skills_dir}")
            self._skills_dir.mkdir(parents=True, exist_ok=True)

    def scan_skills(self, force_refresh: bool = False) -> List[SkillMetadata]:
        """
        Scan all skill directories and extract metadata.

        Only reads YAML frontmatter from SKILL.md files.
        Full content is NOT loaded - this enables efficient startup.

        Args:
            force_refresh: Force rescan even if cache exists

        Returns:
            List of skill metadata
        """
        if self._metadata_cache and not force_refresh:
            return list(self._metadata_cache.values())

        logger.info(f"Scanning skills directory: {self._skills_dir}")
        self._metadata_cache.clear()

        if not self._skills_dir.exists():
            logger.warning(f"Skills directory not found: {self._skills_dir}")
            return []

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            # Skip hidden directories
            if skill_dir.name.startswith('.'):
                continue

            skill_metadata = self._load_skill_metadata(skill_dir)
            if skill_metadata:
                self._metadata_cache[skill_metadata.name] = skill_metadata
                logger.debug(f"Loaded skill metadata: {skill_metadata.name}")

        self._last_scan = datetime.now()
        logger.info(f"Scanned {len(self._metadata_cache)} skills")

        return list(self._metadata_cache.values())

    def get_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """
        Get skill metadata from cache.

        Does not load full content.

        Args:
            skill_name: Name of the skill

        Returns:
            Skill metadata or None if not found
        """
        # Ensure cache is populated
        if not self._metadata_cache:
            self.scan_skills()

        return self._metadata_cache.get(skill_name)

    def load_skill(self, skill_name: str, use_cache: bool = True) -> Optional[SkillDefinition]:
        """
        Load full skill definition on-demand.

        This implements the second layer of progressive disclosure:
        SKILL.md is only loaded when the skill is actually used.

        Args:
            skill_name: Name of the skill
            use_cache: Use cached definition if available

        Returns:
            Complete skill definition or None if not found
        """
        # Check cache first
        if use_cache and skill_name in self._definition_cache:
            return self._definition_cache[skill_name]

        # Get metadata
        metadata = self.get_skill_metadata(skill_name)
        if not metadata:
            logger.warning(f"Skill not found: {skill_name}")
            return None

        # Load full definition
        try:
            definition = self._load_skill_definition(metadata)
            if definition:
                self._definition_cache[skill_name] = definition
                logger.info(f"Loaded skill definition: {skill_name}")
                return definition
        except Exception as e:
            logger.error(f"Error loading skill {skill_name}: {e}")

        return None

    def load_reference_file(
        self,
        skill_name: str,
        filename: str,
    ) -> Optional[str]:
        """
        Load a reference file on-demand.

        This implements the third layer of progressive disclosure:
        Reference files are only loaded when explicitly referenced.

        Args:
            skill_name: Name of the skill
            filename: Name of the reference file (e.g., "hypertension_grades.md")

        Returns:
            File content or None if not found
        """
        metadata = self.get_skill_metadata(skill_name)
        if not metadata:
            return None

        reference_path = metadata.directory / "reference" / filename

        if not reference_path.exists():
            logger.warning(f"Reference file not found: {reference_path}")
            return None

        try:
            with open(reference_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"Loaded reference file: {skill_name}/reference/{filename}")
            return content
        except Exception as e:
            logger.error(f"Error loading reference file {filename}: {e}")
            return None

    def list_reference_files(self, skill_name: str) -> List[str]:
        """
        List available reference files for a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            List of reference filenames
        """
        definition = self.load_skill(skill_name)
        if not definition:
            return []

        return definition.reference_files

    def find_skills_by_tag(self, tag: str) -> List[SkillMetadata]:
        """
        Find skills that have a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching skills
        """
        skills = self.scan_skills()
        return [s for s in skills if tag in s.tags]

    def find_skills_by_layer(self, layer: SkillLayer) -> List[SkillMetadata]:
        """
        Find skills in a specific disclosure layer.

        Args:
            layer: Layer to filter by

        Returns:
            List of skills in the layer
        """
        skills = self.scan_skills()
        return [s for s in skills if s.layer == layer]

    def invalidate_cache(self, skill_name: Optional[str] = None):
        """
        Invalidate cached skill data.

        Args:
            skill_name: Specific skill to invalidate, or None for all
        """
        if skill_name:
            self._metadata_cache.pop(skill_name, None)
            self._definition_cache.pop(skill_name, None)
        else:
            self._metadata_cache.clear()
            self._definition_cache.clear()

        logger.info(f"Cache invalidated: {skill_name or 'all'}")

    def _load_skill_metadata(self, skill_dir: Path) -> Optional[SkillMetadata]:
        """
        Load skill metadata from SKILL.md frontmatter.

        Args:
            skill_dir: Path to skill directory

        Returns:
            Skill metadata or None if invalid
        """
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            logger.debug(f"No SKILL.md found in: {skill_dir}")
            return None

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter, body_start = self._parse_frontmatter(content)
            if not frontmatter:
                logger.warning(f"No frontmatter in: {skill_md}")
                return None

            # Validate required fields
            if 'name' not in frontmatter:
                logger.error(f"Missing 'name' in frontmatter: {skill_md}")
                return None

            if 'description' not in frontmatter:
                logger.error(f"Missing 'description' in frontmatter: {skill_md}")
                return None

            # Determine layer from directory structure or frontmatter
            layer = self._determine_layer(skill_dir, frontmatter)

            return SkillMetadata(
                name=frontmatter['name'],
                description=frontmatter['description'],
                directory=skill_dir,
                source=SkillSource.FILE,
                enabled=frontmatter.get('enabled', True),
                version=frontmatter.get('version', '1.0.0'),
                layer=layer,
                author=frontmatter.get('author'),
                tags=frontmatter.get('tags', []),
                requires=frontmatter.get('requires', []),
            )

        except Exception as e:
            logger.error(f"Error loading skill metadata from {skill_dir}: {e}")
            return None

    def _load_skill_definition(self, metadata: SkillMetadata) -> Optional[SkillDefinition]:
        """
        Load complete skill definition.

        Args:
            metadata: Skill metadata

        Returns:
            Complete skill definition
        """
        skill_md = metadata.directory / "SKILL.md"

        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter and content
        frontmatter, body_start = self._parse_frontmatter(content)
        body_content = content[body_start:] if body_start > 0 else content

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

        # Parse additional frontmatter fields
        dependencies = frontmatter.get('dependencies', [])
        mcp_tools = frontmatter.get('mcp_tools', [])

        return SkillDefinition(
            metadata=metadata,
            content=body_content,
            reference_files=reference_files,
            examples_files=examples_files,
            scripts=scripts,
            dependencies=dependencies,
            mcp_tools=mcp_tools,
        )

    def _parse_frontmatter(self, content: str) -> Tuple[Optional[dict], int]:
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
            logger.error(f"Error parsing frontmatter: {e}")
            return None, 0

    def _determine_layer(
        self,
        skill_dir: Path,
        frontmatter: dict,
    ) -> SkillLayer:
        """
        Determine the skill's disclosure layer.

        Args:
            skill_dir: Path to skill directory
            frontmatter: Parsed frontmatter

        Returns:
            Skill layer
        """
        # Check frontmatter first
        layer_value = frontmatter.get('layer')
        if layer_value:
            try:
                return SkillLayer(layer_value)
            except ValueError:
                logger.warning(f"Invalid layer in frontmatter: {layer_value}")

        # Determine from directory structure
        parent_name = skill_dir.parent.name if skill_dir.parent else None

        if parent_name == "basic" or skill_dir.name == "basic":
            return SkillLayer.BASIC
        elif parent_name == "composite" or skill_dir.name == "composite":
            return SkillLayer.COMPOSITE
        else:
            return SkillLayer.DOMAIN


class SkillFileWatcher:
    """
    Watch for changes to skill files and invalidate cache.

    Useful for development when skills are frequently updated.
    """

    def __init__(self, registry: SkillsRegistry):
        self._registry = registry
        self._file_mtimes: Dict[Path, float] = {}
        self._check_interval = 5  # seconds

    def check_for_changes(self) -> List[str]:
        """
        Check for file modifications and invalidate cache.

        Returns:
            List of skill names that were modified
        """
        modified = []

        for skill_name, metadata in self._registry.scan_skills():
            skill_md = metadata.directory / "SKILL.md"

            if not skill_md.exists():
                continue

            current_mtime = skill_md.stat().st_mtime
            last_mtime = self._file_mtimes.get(skill_md, 0)

            if current_mtime > last_mtime:
                self._registry.invalidate_cache(skill_name)
                modified.append(skill_name)
                logger.info(f"Skill modified, cache invalidated: {skill_name}")

            self._file_mtimes[skill_md] = current_mtime

        return modified
