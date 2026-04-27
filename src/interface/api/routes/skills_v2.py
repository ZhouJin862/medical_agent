"""
Skills API v2 - Claude Skills integration.

Provides endpoints for managing and using Claude Skills
alongside legacy database skills.
"""
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.domain.shared.services.unified_skills_repository import (
    UnifiedSkillsRepository,
    SkillInfo,
)
from src.domain.shared.models.skill_models import (
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillReferenceContent,
    SkillSource,
)
from src.domain.shared.services.skills_registry import SkillsRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/skills", tags=["skills-v3"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SkillListResponse(BaseModel):
    """Response for skill list."""
    skills: List[dict]
    total: int
    sources: dict[str, int]  # Count by source


class SkillDetailResponse(BaseModel):
    """Response for skill details."""
    id: str
    name: str
    description: str
    source: str
    layer: str
    enabled: bool
    content: Optional[str] = None
    reference_files: List[str] = []
    examples_files: List[str] = []
    scripts: List[str] = []
    metadata: dict = {}


class SkillSearchRequest(BaseModel):
    """Request for skill search."""
    query: str = Field(..., min_length=1, description="Search query")
    source: Optional[str] = Field(None, description="Filter by source (file/database)")


class ReferenceFileRequest(BaseModel):
    """Request to load a reference file."""
    filename: str = Field(..., description="Name of the reference file")


class ReferenceFileResponse(BaseModel):
    """Response with reference file content."""
    filename: str
    content: str
    skill_name: str


class SkillsPromptResponse(BaseModel):
    """Response with formatted skills prompt."""
    prompt: str
    skill_count: int


# ============================================================================
# Dependencies
# ============================================================================

async def get_unified_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UnifiedSkillsRepository:
    """Get unified skills repository."""
    return UnifiedSkillsRepository(session, skills_dir="skills")


async def get_file_registry() -> SkillsRegistry:
    """Get file-based skills registry."""
    return SkillsRegistry(skills_dir="skills")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=SkillListResponse)
async def list_skills(
    source: Optional[str] = None,
    enabled_only: bool = True,
    force_refresh: bool = False,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    List all available skills.

    Supports skills from both file system (Claude Skills) and database.
    """
    # Parse source filter
    source_filter = None
    if source:
        try:
            source_filter = SkillSource(source)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source: {source}. Must be 'file' or 'database'."
            )

    skills = await repository.list_skills(
        source=source_filter,
        enabled_only=enabled_only,
        force_refresh=force_refresh,
    )

    # Count by source
    source_counts = {"file": 0, "database": 0}
    for skill in skills:
        source_counts[skill.source.value] += 1

    return SkillListResponse(
        skills=[s.to_dict() for s in skills],
        total=len(skills),
        sources=source_counts,
    )


@router.get("/health", tags=["health"])
async def skills_health_check(
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Health check for the skills system.

    Verifies that:
    - Skills directory exists
    - At least one skill is available
    - Cache is working
    """
    try:
        skills = await repository.list_skills()

        return {
            "status": "healthy",
            "skills_directory": str(repository._file_registry._skills_dir),
            "total_skills": len(skills),
            "cache_status": "valid" if not repository._cache_dirty else "dirty",
        }
    except Exception as e:
        logger.error(f"Skills health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Skills system unhealthy: {str(e)}"
        )


@router.get("/{skill_name}", response_model=SkillDetailResponse)
async def get_skill(
    skill_name: str,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Get skill details.

    Loads the full skill definition including content,
    reference files, and available scripts.
    """
    skill = await repository.get_skill(skill_name)

    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    return SkillDetailResponse(
        id=skill.metadata.name,
        name=skill.metadata.name,
        description=skill.metadata.description,
        source=skill.metadata.source.value,
        layer=skill.metadata.layer.value,
        enabled=skill.metadata.enabled,
        content=skill.content,
        reference_files=skill.reference_files,
        examples_files=skill.examples_files,
        scripts=skill.scripts,
        metadata=skill.metadata.to_dict(),
    )


@router.get("/{skill_name}/metadata")
async def get_skill_metadata(
    skill_name: str,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Get skill metadata only (without full content).

    More efficient when you only need to know about the skill,
    not its complete definition.
    """
    metadata = await repository.get_skill_metadata(skill_name)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    return {
        "name": metadata.name,
        "description": metadata.description,
        "source": metadata.source.value,
        "layer": metadata.layer.value,
        "enabled": metadata.enabled,
        "version": metadata.version,
        "author": metadata.author,
        "tags": metadata.tags,
        "requires": metadata.requires,
    }


@router.post("/search", response_model=SkillListResponse)
async def search_skills(
    request: SkillSearchRequest,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Search skills by name or description.

    Returns skills that match the query in their name or description.
    """
    # Parse source filter
    source_filter = None
    if request.source:
        try:
            source_filter = SkillSource(request.source)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source: {request.source}"
            )

    skills = await repository.search_skills(
        query=request.query,
        source=source_filter,
    )

    return SkillListResponse(
        skills=[s.to_dict() for s in skills],
        total=len(skills),
        sources={"file": 0, "database": 0},  # Not counted in search
    )


@router.get("/{skill_name}/reference/{filename:path}", response_model=ReferenceFileResponse)
async def get_reference_file(
    skill_name: str,
    filename: str,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Get a reference file for a skill.

    Reference files contain detailed documentation that is
    loaded on-demand as part of progressive disclosure.
    """
    content = await repository.load_reference_file(skill_name, filename)

    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reference file not found: {skill_name}/reference/{filename}"
        )

    return ReferenceFileResponse(
        filename=filename,
        content=content,
        skill_name=skill_name,
    )


@router.get("/{skill_name}/references")
async def list_reference_files(
    skill_name: str,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    List available reference files for a skill.
    """
    skill = await repository.get_skill(skill_name)

    if not skill:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    return {
        "skill_name": skill_name,
        "reference_files": skill.reference_files,
    }


@router.get("/prompt/llm", response_model=SkillsPromptResponse)
async def get_skills_prompt(
    enabled_only: bool = True,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Get formatted prompt listing all skills for LLM consumption.

    Useful for including in system prompts to help the LLM
    understand available capabilities.
    """
    # Force refresh to ensure latest skills
    skills = await repository.list_skills(
        enabled_only=enabled_only,
        force_refresh=True,
    )

    prompt = await repository.get_skills_prompt()

    return SkillsPromptResponse(
        prompt=prompt,
        skill_count=len(skills),
    )


@router.post("/cache/refresh")
async def refresh_skill_cache(
    background_tasks: BackgroundTasks,
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Refresh the skills cache.

    Useful when skills have been modified externally.
    """
    def do_refresh():
        """Background refresh task."""
        try:
            repository.invalidate_cache()
            # Trigger rebuild by listing
            import asyncio
            asyncio.run(repository.list_skills(force_refresh=True))
            logger.info("Skill cache refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing skill cache: {e}")

    background_tasks.add_task(do_refresh)

    return {
        "message": "Cache refresh started in background",
        "status": "refreshing",
    }


@router.get("/stats/summary")
async def get_skills_stats(
    repository: UnifiedSkillsRepository = Depends(get_unified_repository),
):
    """
    Get statistics about available skills.
    """
    all_skills = await repository.list_skills(enabled_only=False)
    enabled_skills = await repository.list_skills(enabled_only=True)

    # Count by source
    source_counts_all = {"file": 0, "database": 0}
    source_counts_enabled = {"file": 0, "database": 0}

    # Count by layer
    layer_counts = {"basic": 0, "domain": 0, "composite": 0}

    for skill in all_skills:
        source_counts_all[skill.source.value] += 1
        layer_counts[skill.layer] = layer_counts.get(skill.layer, 0) + 1

    for skill in enabled_skills:
        source_counts_enabled[skill.source.value] += 1

    return {
        "total_skills": len(all_skills),
        "enabled_skills": len(enabled_skills),
        "by_source": {
            "all": source_counts_all,
            "enabled": source_counts_enabled,
        },
        "by_layer": layer_counts,
    }

# ============================================================================
# File Management for Web Editor
# ============================================================================

def _find_skill_registry(skill_name: str):
    """
    Helper function to find skill registry in the skills directory.

    Args:
        skill_name: Skill identifier

    Returns:
        Tuple of (SkillMetadata, SkillsRegistry) or (None, None) if not found
    """
    from src.domain.shared.services.skills_registry import SkillsRegistry
    from src.domain.shared.services.skills_registry import SkillMetadata

    # Only search in 'skills' directory, not '.claude/skills'
    registry = SkillsRegistry("skills")
    metadata = registry.get_skill_metadata(skill_name)
    if metadata:
        return metadata, registry
    return None, None


@router.get("/{skill_name}/files")
async def get_skill_files(skill_name: str):
    """
    Get list of files in a skill directory for web editor.

    Args:
        skill_name: Skill identifier (skill directory name)

    Returns:
        List of files in the skill directory with their types
    """
    metadata, _registry = _find_skill_registry(skill_name)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    skill_dir = metadata.directory
    import sys
    sys.stderr.write(f"DEBUG: Skill directory: {skill_dir}, is_absolute: {skill_dir.is_absolute()}\n")
    sys.stderr.flush()

    # Convert to absolute path if needed
    if not skill_dir.is_absolute():
        import os
        skill_dir = Path(os.path.abspath(skill_dir))
        sys.stderr.write(f"DEBUG: Converted to absolute: {skill_dir}\n")
        sys.stderr.flush()

    sys.stderr.write(f"DEBUG: Directory exists: {skill_dir.exists()}\n")
    sys.stderr.flush()

    def get_file_type(file_path: Path, skill_dir: Path) -> str:
        """Determine the type of file based on its location"""
        name = file_path.name
        parent_name = file_path.parent.name

        if name == "SKILL.md":
            return "main"
        elif parent_name == "reference":
            return "reference"
        elif parent_name == "scripts":
            return "script"
        elif parent_name == "assets":
            return "asset"
        elif name.startswith("examples"):
            return "examples"
        elif parent_name == "references":
            return "reference"
        elif name.endswith(".md"):
            return "markdown"
        elif name.endswith((".py", ".js", ".ts")):
            return "code"
        elif name.endswith((".json", ".yaml", ".yml")):
            return "data"
        elif name.endswith((".txt", ".csv")):
            return "text"
        else:
            return "file"

    # Recursively get all files in the skill directory
    def collect_files(directory: Path, base_path: Path = None, files_list: list = None):
        """Recursively collect all files"""
        if files_list is None:
            files_list = []
        if base_path is None:
            base_path = directory

        for item in directory.iterdir():
            # Skip __pycache__ and hidden files/directories
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            if item.is_file():
                # Get relative path from skill directory
                rel_path = item.relative_to(base_path)
                files_list.append({
                    "name": item.name,
                    "path": str(rel_path).replace("\\", "/"),
                    "type": get_file_type(item, base_path),
                    "size": item.stat().st_size,
                })
            elif item.is_dir():
                # Recursively process subdirectories
                collect_files(item, base_path, files_list)
        return files_list

    # Start collecting from skill directory
    files = []
    if skill_dir.exists():
        files = collect_files(skill_dir)
        import sys
        sys.stderr.write(f"DEBUG: Collected {len(files)} files from {skill_dir}\n")
        for f in files[:5]:
            sys.stderr.write(f"  - {f['path']}\n")
        sys.stderr.flush()
    else:
        import sys
        sys.stderr.write(f"DEBUG: Skill directory does not exist: {skill_dir}\n")
        sys.stderr.flush()

    # Sort files: SKILL.md first, then by type, then by name
    def file_sort_key(f):
        if f["name"] == "SKILL.md":
            return (0, f["name"])
        type_priority = {
            "main": 0,
            "script": 1,
            "reference": 2,
            "asset": 3,
            "examples": 4,
        }
        priority = type_priority.get(f["type"], 99)
        return (priority, f["path"])

    files.sort(key=file_sort_key)

    return {"files": files}


@router.get("/{skill_name}/files/{file_path:path}")
async def get_skill_file_content(skill_name: str, file_path: str):
    """
    Get content of a specific file in a skill directory for web editor.

    Args:
        skill_name: Skill identifier
        file_path: Path to the file relative to skill directory

    Returns:
        File content
    """
    metadata, _registry = _find_skill_registry(skill_name)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    file_full_path = metadata.directory / file_path
    if not file_full_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )

    try:
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "name": file_full_path.name,
            "path": file_path,
            "content": content,
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )


@router.put("/{skill_name}/files/{file_path:path}")
async def update_skill_file_content(
    skill_name: str,
    file_path: str,
    request: dict,
):
    """
    Update content of a specific file in a skill directory from web editor.

    Args:
        skill_name: Skill identifier
        file_path: Path to the file relative to skill directory
        request: Request body containing 'content' field

    Returns:
        Updated file info
    """
    metadata, registry = _find_skill_registry(skill_name)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {skill_name}"
        )

    file_full_path = metadata.directory / file_path
    if not file_full_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )

    content = request.get("content", "")
    if content is None:
        content = ""

    try:
        with open(file_full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Invalidate cache for this skill
        if registry:
            registry.invalidate_cache(skill_name)

        return {
            "name": file_full_path.name,
            "path": file_path,
            "content": content,
            "size": len(content),
            "updated": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error writing file: {str(e)}"
        )
