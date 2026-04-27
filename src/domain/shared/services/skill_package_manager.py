"""
Skill Package Manager - Import/Export skills as ZIP packages.

Skill Package Format (ZIP):
    skill-package.zip
    ├── manifest.json          # Package metadata
    ├── skills/                # Claude Skills (file-based)
    │   ├── skill-name-1/
    │   │   ├── SKILL.md
    │   │   ├── reference/
    │   │   └── scripts/
    │   └── skill-name-2/
    │       └── SKILL.md
    └── database/              # Database skills (optional)
        └── skills.json        # Database skill definitions

Manifest Format:
{
    "name": "package-name",
    "version": "1.0.0",
    "description": "Package description",
    "author": "Author name",
    "created_at": "2024-01-01T00:00:00Z",
    "skills": {
        "file": ["skill-name-1", "skill-name-2"],
        "database": ["db-skill-1"]
    }
}
"""
import json
import logging
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.models.skill_models import (
    SkillMetadata,
    SkillDefinition,
    SkillSource,
)
from src.domain.shared.services.skills_registry import SkillsRegistry
from src.infrastructure.persistence.models.skill_models import (
    SkillModel,
    SkillType,
)

logger = logging.getLogger(__name__)


@dataclass
class PackageManifest:
    """Skill package manifest."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    skills: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "skills": self.skills,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageManifest":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            skills=data.get("skills", {}),
        )


@dataclass
class ExportOptions:
    """Options for skill export."""
    include_reference_files: bool = True
    include_scripts: bool = True
    include_database_skills: bool = True
    overwrite_existing: bool = False
    skills: Optional[List[str]] = None  # None = all skills


@dataclass
class ImportOptions:
    """Options for skill import."""
    overwrite_existing: bool = False
    skip_existing: bool = False
    import_file_skills: bool = True
    import_database_skills: bool = True
    validate_only: bool = False  # Just validate, don't import


@dataclass
class ImportError:
    """An error that occurred during import."""
    skill_name: str
    error_type: str  # "validation", "conflict", "other"
    message: str


@dataclass
class ImportResult:
    """Result of skill package import."""
    success: bool
    total_skills: int = 0
    imported_skills: List[str] = field(default_factory=list)
    skipped_skills: List[str] = field(default_factory=list)
    failed_skills: List[str] = field(default_factory=list)
    errors: List[ImportError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manifest: Optional[PackageManifest] = None


@dataclass
class ExportResult:
    """Result of skill package export."""
    success: bool
    package_bytes: Optional[bytes] = None
    filename: str = ""
    total_skills: int = 0
    file_skills: List[str] = field(default_factory=list)
    database_skills: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SkillPackageManager:
    """
    Manager for skill package import/export operations.
    """

    def __init__(self, skills_dir: str = "skills"):
        """
        Initialize the package manager.

        Args:
            skills_dir: Directory containing Claude Skills
        """
        self._skills_dir = Path(skills_dir)
        self._registry = SkillsRegistry(skills_dir)

    async def export_package(
        self,
        session: AsyncSession,
        package_name: str,
        options: Optional[ExportOptions] = None,
    ) -> ExportResult:
        """
        Export skills to a ZIP package.

        Args:
            session: Database session
            package_name: Name for the package
            options: Export options

        Returns:
            Export result with package bytes
        """
        options = options or ExportOptions()
        result = ExportResult(success=False, filename=f"{package_name}.zip")

        try:
            # Create in-memory ZIP
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Collect skills to export
                file_skills, db_skills = await self._collect_skills(
                    session, options
                )

                result.file_skills = file_skills
                result.database_skills = db_skills
                result.total_skills = len(file_skills) + len(db_skills)

                if result.total_skills == 0:
                    result.warnings.append("No skills found to export")
                    result.success = True
                    return result

                # Create manifest
                manifest = PackageManifest(
                    name=package_name,
                    description=f"Skill package exported on {datetime.utcnow().isoformat()}",
                    skills={
                        "file": file_skills,
                        "database": db_skills,
                    }
                )

                # Write manifest
                zip_file.writestr(
                    "manifest.json",
                    json.dumps(manifest.to_dict(), indent=2)
                )

                # Export file skills
                for skill_name in file_skills:
                    await self._export_file_skill(
                        zip_file, skill_name, options
                    )

                # Export database skills
                if options.include_database_skills and db_skills:
                    await self._export_database_skills(
                        zip_file, db_skills, session
                    )

            # Get bytes
            result.package_bytes = zip_buffer.getvalue()
            result.success = True

            logger.info(
                f"Exported package '{package_name}': "
                f"{len(file_skills)} file skills, {len(db_skills)} database skills"
            )

            return result

        except Exception as e:
            logger.error(f"Export failed: {e}")
            import traceback
            traceback.print_exc()
            return result

    async def import_package(
        self,
        session: AsyncSession,
        package_bytes: bytes,
        options: Optional[ImportOptions] = None,
    ) -> ImportResult:
        """
        Import skills from a ZIP package.

        Args:
            session: Database session
            package_bytes: ZIP package bytes
            options: Import options

        Returns:
            Import result with details
        """
        options = options or ImportOptions()
        result = ImportResult(success=False)

        try:
            # Open ZIP
            with zipfile.ZipFile(BytesIO(package_bytes), 'r') as zip_file:
                # Try to read manifest (optional)
                manifest_data = self._read_manifest(zip_file)

                if manifest_data:
                    # Use manifest if available
                    result.manifest = PackageManifest.from_dict(manifest_data)
                    result.total_skills = (
                        len(result.manifest.skills.get("file", [])) +
                        len(result.manifest.skills.get("database", []))
                    )
                else:
                    # Auto-discover skills from ZIP structure
                    result.manifest = self._discover_skills_from_zip(zip_file)
                    result.total_skills = (
                        len(result.manifest.skills.get("file", [])) +
                        len(result.manifest.skills.get("database", []))
                    )
                    result.warnings.append(
                        "No manifest.json found - skills auto-discovered from ZIP structure"
                    )

                # Validate mode - just check, don't import
                if options.validate_only:
                    return await self._validate_package(
                        zip_file, result, options
                    )

                # Import file skills
                if options.import_file_skills:
                    await self._import_file_skills(
                        zip_file, session, result, options
                    )

                # Import database skills
                if options.import_database_skills:
                    await self._import_database_skills(
                        zip_file, session, result, options
                    )

            # Check if any imports succeeded
            result.success = len(result.imported_skills) > 0 or options.validate_only

            logger.info(
                f"Import complete: {len(result.imported_skills)} imported, "
                f"{len(result.skipped_skills)} skipped, "
                f"{len(result.failed_skills)} failed"
            )

            return result

        except Exception as e:
            logger.error(f"Import failed: {e}")
            import traceback
            traceback.print_exc()
            result.errors.append(ImportError(
                skill_name="",
                error_type="other",
                message=str(e)
            ))
            return result

    async def _collect_skills(
        self,
        session: AsyncSession,
        options: ExportOptions,
    ) -> tuple[List[str], List[str]]:
        """Collect skills to export."""
        file_skills = []
        db_skills = []

        # Collect file skills
        if options.skills is None:
            # Export all file skills
            for metadata in self._registry.scan_skills():
                if metadata.enabled:
                    file_skills.append(metadata.name)
        else:
            # Filter by specified skills
            for skill_name in options.skills:
                metadata = self._registry.get_skill_metadata(skill_name)
                if metadata and metadata.enabled:
                    file_skills.append(skill_name)

        # Collect database skills
        if options.include_database_skills:
            stmt = select(SkillModel).where(SkillModel.enabled == True)
            db_result = await session.execute(stmt)
            for skill in db_result.scalars().all():
                # Check if in filter (if filter specified)
                if options.skills is None or skill.name in options.skills:
                    db_skills.append(skill.name)

        return file_skills, db_skills

    async def _export_file_skill(
        self,
        zip_file: zipfile.ZipFile,
        skill_name: str,
        options: ExportOptions,
    ):
        """Export a file-based skill to ZIP."""
        skill_dir = self._skills_dir / skill_name

        if not skill_dir.exists():
            logger.warning(f"Skill directory not found: {skill_name}")
            return

        # Always use forward slashes for ZIP paths (cross-platform)
        def to_zip_path(*parts):
            return "/".join(str(p) for p in parts if p)

        # Always include SKILL.md
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            zip_path = to_zip_path("skills", skill_name, "SKILL.md")
            zip_file.write(skill_file, zip_path)
            logger.debug(f"Added to ZIP: {zip_path}")

        # Include reference files
        if options.include_reference_files:
            ref_dir = skill_dir / "reference"
            if ref_dir.exists():
                for ref_file in ref_dir.glob("**/*"):
                    if ref_file.is_file():
                        rel_path = ref_file.relative_to(ref_dir)
                        zip_path = to_zip_path("skills", skill_name, "reference", rel_path)
                        zip_file.write(ref_file, zip_path)

        # Include scripts
        if options.include_scripts:
            script_dir = skill_dir / "scripts"
            if script_dir.exists():
                for script_file in script_dir.glob("**/*"):
                    if script_file.is_file():
                        rel_path = script_file.relative_to(script_dir)
                        zip_path = to_zip_path("skills", skill_name, "scripts", rel_path)
                        zip_file.write(script_file, zip_path)

    async def _export_database_skills(
        self,
        zip_file: zipfile.ZipFile,
        skill_names: List[str],
        session: AsyncSession,
    ):
        """Export database skills to JSON."""
        db_skills_data = []

        for skill_name in skill_names:
            stmt = select(SkillModel).where(
                SkillModel.name == skill_name,
                SkillModel.enabled == True,
            )
            result = await session.execute(stmt)
            skill = result.scalar_one_or_none()

            if skill:
                db_skills_data.append({
                    "id": str(skill.id),
                    "name": skill.name,
                    "display_name": skill.display_name,
                    "description": skill.description,
                    "type": skill.type.value,
                    "category": skill.category.value if skill.category else None,
                    "enabled": skill.enabled,
                    "version": skill.version,
                    "intent_keywords": skill.intent_keywords,
                    "config": skill.config,
                })

        # Write to file
        zip_file.writestr(
            "database/skills.json",
            json.dumps(db_skills_data, indent=2, default=str)
        )

    def _read_manifest(self, zip_file: zipfile.ZipFile) -> Optional[Dict[str, Any]]:
        """Read and parse manifest from ZIP."""
        try:
            # Try different path formats (Windows/Unix)
            name_list = zip_file.namelist()
            logger.debug(f"Files in ZIP: {name_list[:5]}...")

            # Find manifest.json (handle different path formats)
            manifest_path = None
            for path in name_list:
                normalized = path.replace("\\", "/")
                if normalized == "manifest.json" or normalized.endswith("/manifest.json"):
                    manifest_path = path
                    break

            if not manifest_path:
                logger.info("No manifest.json in package - will auto-discover skills")
                return None

            manifest_bytes = zip_file.read(manifest_path)
            manifest_data = json.loads(manifest_bytes.decode('utf-8'))
            logger.info(f"Loaded manifest: {manifest_data.get('name', 'unknown')}")
            return manifest_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid manifest.json: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading manifest: {e}")
            return None

    def _discover_skills_from_zip(self, zip_file: zipfile.ZipFile) -> PackageManifest:
        """Auto-discover skills from ZIP structure without manifest."""
        file_skills = set()
        db_skills = []
        name_list = zip_file.namelist()

        # First, detect the directory structure
        # Find all directories that contain SKILL.md files
        skill_dirs = set()
        for path in name_list:
            normalized = path.replace("\\", "/")
            if "/SKILL.md" in normalized:
                # Extract the directory containing SKILL.md
                parts = normalized.split("/")
                for i, part in enumerate(parts):
                    if part.upper() == "SKILL.MD" and i > 0:
                        skill_dir = parts[i - 1]
                        parent_dir = parts[i - 2] if i >= 2 else None
                        skill_dirs.add((parent_dir, skill_dir))
                        break

        logger.info(f"Found skill directories: {skill_dirs}")

        # Determine the structure pattern
        # If all skills share the same parent directory, treat it as the root
        parent_dirs = set(pd for pd, _ in skill_dirs if pd)
        root_prefix = None

        if len(parent_dirs) == 1:
            # All skills are under the same parent directory (e.g., "projects/", "skills/")
            root_prefix = list(parent_dirs)[0]
            logger.info(f"Detected root prefix: {root_prefix}")
        elif "" in parent_dirs:
            # Some skills are at root level
            root_prefix = None

        # Collect skill names based on detected structure
        for parent_dir, skill_name in skill_dirs:
            # Accept skills if:
            # 1. No root prefix detected and parent is acceptable (None, "skills", empty)
            # 2. Root prefix matches the detected parent directory
            if root_prefix is None:
                # Accept if parent is None (root), "skills", or another valid top-level dir
                if parent_dir in [None, "", "skills"]:
                    file_skills.add(skill_name)
                else:
                    # Parent is something like "projects" - treat it as a container
                    # and accept skills under it
                    file_skills.add(skill_name)
            else:
                # Only accept if parent matches the detected root prefix
                if parent_dir == root_prefix:
                    file_skills.add(skill_name)
                else:
                    # Different structure - still accept the skill
                    file_skills.add(skill_name)

        # Check for database/skills.json
        has_db_file = any(
            f.replace("\\", "/") == "database/skills.json" or
            f.replace("\\", "/").endswith("/database/skills.json")
            for f in name_list
        )
        if has_db_file:
            try:
                db_skills_json = zip_file.read("database/skills.json")
                db_data = json.loads(db_skills_json.decode('utf-8'))
                db_skills = [s.get("name", "") for s in db_data if s.get("name")]
            except:
                logger.warning("Found database/skills.json but failed to read it")

        logger.info(f"Auto-discovered {len(file_skills)} file skills: {sorted(file_skills)}")

        # Create manifest from discovered skills
        return PackageManifest(
            name=f"auto-discovered-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            version="1.0.0",
            description="Auto-discovered from ZIP structure",
            skills={
                "file": sorted(list(file_skills)),
                "database": db_skills,
            }
        )

    async def _validate_package(
        self,
        zip_file: zipfile.ZipFile,
        result: ImportResult,
        options: ImportOptions,
    ) -> ImportResult:
        """Validate package without importing."""
        manifest = result.manifest
        file_list = zip_file.namelist()

        logger.info(f"Validating package: {manifest.name}")
        logger.info(f"Files in package: {file_list[:10]}...")  # Log first 10 files

        # Check if package has any skills
        file_skills = manifest.skills.get("file", [])
        db_skills = manifest.skills.get("database", [])

        if not file_skills and not db_skills:
            result.errors.append(ImportError(
                skill_name="",
                error_type="validation",
                message="Package contains no skills (manifest.skills is empty)"
            ))
            result.success = False
            return result

        # Normalize file paths for comparison (handle Windows/Unix differences)
        normalized_files = [f.replace("\\", "/") for f in file_list]

        # Validate file skills - check if each skill has files in the package
        for skill_name in file_skills:
            # More flexible check: look for skill name in any path segment
            # Handles: skills/name/, projects/name/, name/, etc.
            found = False
            for path in normalized_files:
                path_parts = path.split("/")
                if skill_name in path_parts:
                    skill_idx = path_parts.index(skill_name)
                    # Check if this is a SKILL.md file for this skill
                    if "SKILL.md" in path:
                        # Make sure SKILL.md is directly under the skill name
                        if skill_idx + 1 < len(path_parts) and path_parts[skill_idx + 1] == "SKILL.md":
                            found = True
                            break
                    # Or check if there are any files under this skill directory
                    elif skill_idx + 1 < len(path_parts):
                        found = True
                        break

            if not found:
                result.errors.append(ImportError(
                    skill_name=skill_name,
                    error_type="validation",
                    message=f"No files found for skill '{skill_name}' in package"
                ))

        # Validate database skills (just check if skills.json exists)
        if db_skills:
            has_db_file = any(
                f.replace("\\", "/") == "database/skills.json" or
                f.replace("\\", "/").endswith("/database/skills.json")
                for f in file_list
            )
            if not has_db_file:
                result.warnings.append(
                    "Package lists database skills but database/skills.json not found"
                )

        # Check for conflicts
        if not options.overwrite_existing:
            for skill_name in file_skills:
                skill_dir = self._skills_dir / skill_name
                if skill_dir.exists() and (skill_dir / "SKILL.md").exists():
                    result.warnings.append(
                        f"File skill '{skill_name}' already exists (will skip if skip_existing=true)"
                    )

        result.success = len(result.errors) == 0

        logger.info(
            f"Validation result: success={result.success}, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}"
        )

        return result

    async def _import_file_skills(
        self,
        zip_file: zipfile.ZipFile,
        session: AsyncSession,
        result: ImportResult,
        options: ImportOptions,
    ):
        """Import file-based skills from ZIP."""
        manifest = result.manifest
        file_list = zip_file.namelist()

        for skill_name in manifest.skills.get("file", []):
            try:
                # Check if already exists
                skill_dir = self._skills_dir / skill_name

                if skill_dir.exists():
                    if options.skip_existing:
                        result.skipped_skills.append(skill_name)
                        continue
                    if not options.overwrite_existing:
                        result.errors.append(ImportError(
                            skill_name=skill_name,
                            error_type="conflict",
                            message="Skill already exists and overwrite is disabled"
                        ))
                        continue

                # Create skill directory
                skill_dir.mkdir(parents=True, exist_ok=True)

                # First, find the actual path prefix for this skill in the ZIP
                # Look for the SKILL.md file to determine the correct prefix
                skill_prefix = None
                for file_path in file_list:
                    normalized = file_path.replace("\\", "/")
                    # Check if this file is the SKILL.md for this skill
                    if normalized.endswith(f"/{skill_name}/SKILL.md") or normalized == f"{skill_name}/SKILL.md":
                        # Found it! Extract the prefix
                        # Path could be: "projects/skill-name/SKILL.md" or "skill-name/SKILL.md"
                        parts = normalized.split("/")
                        skill_idx = parts.index(skill_name)
                        skill_prefix = "/".join(parts[:skill_idx + 1]) + "/"
                        logger.info(f"Found prefix for {skill_name}: {skill_prefix}")
                        break

                if not skill_prefix:
                    # Try fallback patterns
                    skill_prefixes = [
                        f"skills/{skill_name}/",
                        f"skills\\{skill_name}\\",
                        f"projects/{skill_name}/",
                        f"projects\\{skill_name}\\",
                        f"{skill_name}/",
                        f"{skill_name}\\",
                    ]
                    for file_path in file_list:
                        normalized = file_path.replace("\\", "/")
                        for prefix in skill_prefixes:
                            prefix_normalized = prefix.replace("\\", "/")
                            if normalized.startswith(prefix_normalized):
                                skill_prefix = prefix_normalized
                                break
                        if skill_prefix:
                            break

                if not skill_prefix:
                    result.warnings.append(f"Could not find files for skill '{skill_name}'")
                    continue

                # Extract all files under the detected prefix
                extracted = False
                for file_path in file_list:
                    normalized = file_path.replace("\\", "/")
                    prefix_normalized = skill_prefix.replace("\\", "/")
                    if normalized.startswith(prefix_normalized):
                        try:
                            # Skip directory entries (paths ending with /)
                            if normalized.endswith('/'):
                                # Create the directory
                                relative_path = normalized[len(prefix_normalized):]
                                if relative_path:
                                    dest_path = self._skills_dir / skill_name / relative_path.rstrip('/')
                                    dest_path.mkdir(parents=True, exist_ok=True)
                                extracted = True
                                continue

                            # Extract file
                            content = zip_file.read(file_path)
                            # Calculate destination path (remove prefix, add to skills_dir)
                            relative_path = normalized[len(prefix_normalized):]
                            dest_path = self._skills_dir / skill_name / relative_path
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            dest_path.write_bytes(content)
                            extracted = True
                        except Exception as e:
                            logger.warning(f"Failed to extract {file_path}: {e}")

                if extracted:
                    result.imported_skills.append(skill_name)
                    # Invalidate cache
                    self._registry.invalidate_cache(skill_name)
                else:
                    result.warnings.append(f"No files found for skill '{skill_name}'")

            except Exception as e:
                logger.error(f"Failed to import file skill {skill_name}: {e}")
                result.failed_skills.append(skill_name)
                result.errors.append(ImportError(
                    skill_name=skill_name,
                    error_type="other",
                    message=str(e)
                ))

    async def _import_database_skills(
        self,
        zip_file: zipfile.ZipFile,
        session: AsyncSession,
        result: ImportResult,
        options: ImportOptions,
    ):
        """Import database skills from ZIP."""
        try:
            # Read database skills file
            db_skills_json = zip_file.read("database/skills.json")
            db_skills = json.loads(db_skills_json.decode('utf-8'))

            for skill_data in db_skills:
                skill_name = skill_data["name"]

                try:
                    # Check if already exists
                    existing_stmt = select(SkillModel).where(
                        SkillModel.name == skill_name
                    )
                    existing_result = await session.execute(existing_stmt)
                    existing = existing_result.scalar_one_or_none()

                    if existing:
                        if options.skip_existing:
                            result.skipped_skills.append(skill_name)
                            continue
                        if not options.overwrite_existing:
                            result.errors.append(ImportError(
                                skill_name=skill_name,
                                error_type="conflict",
                                message="Database skill already exists"
                            ))
                            continue

                        # Update existing
                        existing.display_name = skill_data["display_name"]
                        existing.description = skill_data["description"]
                        existing.type = SkillType(skill_data["type"])
                        existing.enabled = skill_data["enabled"]
                        existing.version = skill_data["version"]
                        existing.intent_keywords = skill_data["intent_keywords"]
                        existing.config = skill_data["config"]
                    else:
                        # Create new
                        import uuid
                        skill = SkillModel(
                            id=skill_data.get("id") or str(uuid.uuid4()),
                            name=skill_data["name"],
                            display_name=skill_data["display_name"],
                            description=skill_data["description"],
                            type=SkillType(skill_data["type"]),
                            enabled=skill_data["enabled"],
                            version=skill_data["version"],
                            intent_keywords=skill_data["intent_keywords"],
                            config=skill_data["config"],
                        )
                        session.add(skill)

                    result.imported_skills.append(skill_name)

                except Exception as e:
                    logger.error(f"Failed to import database skill {skill_name}: {e}")
                    result.failed_skills.append(skill_name)
                    result.errors.append(ImportError(
                        skill_name=skill_name,
                        error_type="other",
                        message=str(e)
                    ))

            await session.commit()

        except KeyError:
            result.warnings.append("No database skills in package")
        except Exception as e:
            logger.error(f"Failed to import database skills: {e}")
            result.warnings.append(f"Database skills import failed: {str(e)}")


async def get_available_skills_for_export(
    session: AsyncSession,
    skills_dir: str = "skills",
) -> Dict[str, List[Dict[str, str]]]:
    """
    Get list of available skills that can be exported.

    Returns:
        Dict with "file" and "database" skill lists
    """
    registry = SkillsRegistry(skills_dir)

    # Get file skills
    file_skills = []
    for metadata in registry.scan_skills():
        file_skills.append({
            "name": metadata.name,
            "description": metadata.description,
            "source": "file",
            "layer": metadata.layer.value,
        })

    # Get database skills
    db_skills = []
    stmt = select(SkillModel).where(SkillModel.enabled == True)
    result = await session.execute(stmt)
    for skill in result.scalars().all():
        db_skills.append({
            "name": skill.name,
            "description": skill.description or skill.display_name,
            "source": "database",
            "type": skill.type.value,
        })

    return {
        "file": file_skills,
        "database": db_skills,
    }
