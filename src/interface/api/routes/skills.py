"""
Skills API routes.

Provides endpoints for skill management operations.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, status, HTTPException

from src.application.services.skill_management_service import (
    SkillManagementApplicationService,
    SkillNotFoundException,
)
from src.interface.api.dto.request import (
    SkillCreateRequest,
    SkillUpdateRequest,
    SkillPromptUpdateRequest,
    SkillModelConfigUpdateRequest,
)
from src.interface.api.dto.response import SkillResponse, SkillListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/skills", tags=["skills"])


from src.interface.api.dependencies import get_skill_service

# Removed local get_skill_service - now using dependency from dependencies.py


@router.get("")
async def list_skills(
    skill_type: str | None = None,
    category: str | None = None,
    enabled_only: bool = False,
    page: int = 1,
    page_size: int = 10,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
):
    """
    List skills with optional filtering and pagination.

    Args:
        skill_type: Filter by skill type
        category: Filter by category
        enabled_only: Only return enabled skills
        page: Page number (1-indexed)
        page_size: Number of items per page
        skill_service: Injected skill service

    Returns:
        Paginated list of skills (both file-based and database)
    """
    from datetime import datetime

    # Validate page parameters
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 100"
        )

    skills = []

    # Get file-based skills from SkillsRegistry (only from 'skills' directory, not '.claude/skills')
    from src.domain.shared.services.skills_registry import SkillsRegistry
    registry = SkillsRegistry("skills")
    for metadata in registry.scan_skills():
        if enabled_only and not metadata.enabled:
            continue
        # Add file-based skill with all required fields
        # Use name as display_name for file-based skills (from SKILL.md frontmatter)
        skills.append({
            "id": metadata.name,
            "name": metadata.name,
            "display_name": metadata.name,  # Use the 'name' from SKILL.md frontmatter
            "description": metadata.description,  # Use the 'description' from SKILL.md frontmatter
            "type": "file",  # Use "file" as the type for file-based skills
            "category": None,
            "enabled": metadata.enabled,
            "version": metadata.version,
            "intent_keywords": [],
            "config": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        })

    # Get database skills
    db_skills = await skill_service.list_skills(
        skill_type=skill_type,
        category=category,
        enabled_only=enabled_only,
    )
    skills.extend(db_skills)

    # Get total count before pagination
    total_count = len(skills)
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_skills = skills[start_idx:end_idx]

    return {
        "items": paginated_skills,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Get skill by ID.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service

    Returns:
        Skill data
    """
    try:
        skill = await skill_service.get_skill(
            skill_id=skill_id,
        )
        return SkillResponse(**skill)
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    request: SkillCreateRequest,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Create a new skill.

    Args:
        request: Skill creation request
        skill_service: Injected skill service

    Returns:
        Created skill data
    """
    try:
        logger.info(f"Creating skill: {request.name}")
        skill = await skill_service.create_skill(
            name=request.name,
            display_name=request.display_name,
            skill_type=request.skill_type,
            category=request.category,
            description=request.description,
            intent_keywords=request.intent_keywords,
            config=request.config,
            model_config=request.model_config,
            prompts=request.prompts,
        )
        logger.info(f"Skill created successfully: {skill}")
        return SkillResponse(**skill)
    except Exception as e:
        logger.error(f"Error creating skill: {type(e).__name__}: {e}", exc_info=True)
        if "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        raise


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    request: SkillUpdateRequest,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Update an existing skill.

    Args:
        skill_id: Skill identifier
        request: Skill update request
        skill_service: Injected skill service

    Returns:
        Updated skill data
    """
    try:
        skill = await skill_service.update_skill(
            skill_id=skill_id,
            display_name=request.display_name,
            description=request.description,
            intent_keywords=request.intent_keywords,
            config=request.config,
        )
        return SkillResponse(**skill)
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{skill_id}/enable", response_model=SkillResponse)
async def enable_skill(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Enable a skill.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service

    Returns:
        Updated skill data
    """
    try:
        skill = await skill_service.enable_skill(
            skill_id=skill_id,
        )
        return SkillResponse(**skill)
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{skill_id}/disable", response_model=SkillResponse)
async def disable_skill(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Disable a skill.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service

    Returns:
        Updated skill data
    """
    try:
        skill = await skill_service.disable_skill(
            skill_id=skill_id,
        )
        return SkillResponse(**skill)
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{skill_id}/reload", response_model=SkillResponse)
async def reload_skill(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> SkillResponse:
    """
    Reload a skill from database.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service

    Returns:
        Reloaded skill data
    """
    try:
        skill = await skill_service.reload_skill(
            skill_id=skill_id,
        )
        return SkillResponse(**skill)
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> None:
    """
    Delete a skill.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service
    """
    try:
        await skill_service.delete_skill(
            skill_id=skill_id,
        )
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{skill_id}/prompts", response_model=list)
async def get_skill_prompts(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> list:
    """
    Get prompts for a skill.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service

    Returns:
        List of prompt data
    """
    try:
        prompts = await skill_service.get_skill_prompts(
            skill_id=skill_id,
        )
        return prompts
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{skill_id}/prompts", response_model=dict)
async def update_skill_prompt(
    skill_id: str,
    request: SkillPromptUpdateRequest,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> dict:
    """
    Update a prompt for a skill.

    Args:
        skill_id: Skill identifier
        request: Prompt update request
        skill_service: Injected skill service

    Returns:
        Updated prompt data
    """
    try:
        prompt = await skill_service.update_skill_prompt(
            skill_id=skill_id,
            prompt_type=request.prompt_type,
            content=request.content,
        )
        return prompt
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{skill_id}/model-config", response_model=dict)
async def get_skill_model_config(
    skill_id: str,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> dict | None:
    """
    Get model configuration for a skill.

    Args:
        skill_id: Skill identifier
        skill_service: Injected skill service

    Returns:
        Model config data or None
    """
    try:
        config = await skill_service.get_skill_model_config(
            skill_id=skill_id,
        )
        return config
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{skill_id}/model-config", response_model=dict)
async def update_skill_model_config(
    skill_id: str,
    request: SkillModelConfigUpdateRequest,
    skill_service: SkillManagementApplicationService = Depends(get_skill_service),
) -> dict:
    """
    Update model configuration for a skill.

    Args:
        skill_id: Skill identifier
        request: Model config update request
        skill_service: Injected skill service

    Returns:
        Updated model config data
    """
    try:
        model_config = {
            "provider": request.provider,
            "model_name": request.model_name,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "extra_config": request.extra_config,
        }

        config = await skill_service.update_skill_model_config(
            skill_id=skill_id,
            model_config=model_config,
        )
        return config
    except SkillNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


def _find_skill_metadata(skill_id: str):
    """
    Helper function to find skill metadata in any of the skill directories.

    Args:
        skill_id: Skill identifier

    Returns:
        Skill metadata or None if not found
    """
    from src.domain.shared.services.skills_registry import SkillsRegistry

    for skills_dir in ["skills", ".claude/skills"]:
        registry = SkillsRegistry(skills_dir)
        metadata = registry.get_skill_metadata(skill_id)
        if metadata:
            return metadata, registry
    return None, None


@router.get("/{skill_id}/files")
async def get_skill_files(skill_id: str) -> dict:
    """
    Get list of files in a skill directory with tree structure.

    Args:
        skill_id: Skill identifier (skill directory name)

    Returns:
        Tree structure of files and folders
    """
    from pathlib import Path
    import os

    metadata, registry = _find_skill_metadata(skill_id)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill not found: {skill_id}",
        )

    skill_dir = metadata.directory

    # Convert to absolute path if needed
    if not skill_dir.is_absolute():
        skill_dir = Path(os.path.abspath(skill_dir))

    def get_file_type(file_path: Path, skill_dir: Path) -> str:
        """Determine the type of file based on its location"""
        name = file_path.name
        parent_name = file_path.parent.name

        if name == "SKILL.md":
            return "main"
        elif parent_name == "reference":
            return "reference"
        elif parent_name == "references":
            return "reference"
        elif parent_name == "scripts":
            return "script"
        elif parent_name == "assets":
            return "asset"
        elif name.startswith("examples"):
            return "examples"
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

    def build_tree(directory: Path, base_path: Path = None) -> list:
        """Build a tree structure of files and folders"""
        if base_path is None:
            base_path = directory

        items = []
        try:
            # Sort: directories first, then files
            entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))

            for item in entries:
                # Skip __pycache__ and hidden files/directories
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue

                rel_path = item.relative_to(base_path)
                path_str = str(rel_path).replace("\\", "/")

                if item.is_dir():
                    # Recursively build subtree for directories
                    children = build_tree(item, base_path)
                    items.append({
                        "name": item.name,
                        "path": path_str,
                        "type": "folder",
                        "children": children,
                    })
                elif item.is_file():
                    items.append({
                        "name": item.name,
                        "path": path_str,
                        "type": get_file_type(item, base_path),
                        "size": item.stat().st_size,
                    })
        except PermissionError:
            pass

        return items

    # Build tree structure
    tree = []
    if skill_dir.exists():
        tree = build_tree(skill_dir)

    # Sort tree: SKILL.md first, then folders, then files by type
    def tree_sort_key(item):
        if item["type"] == "folder":
            return (0, item["name"])
        elif item["name"] == "SKILL.md":
            return (1, "")
        else:
            type_priority = {
                "main": 1,
                "script": 2,
                "reference": 3,
                "asset": 4,
                "examples": 5,
            }
            priority = type_priority.get(item["type"], 99)
            return (priority, item["name"])

    tree.sort(key=tree_sort_key)

    return {"tree": tree}


@router.get("/{skill_id}/files/{file_path:path}")
async def get_skill_file_content(skill_id: str, file_path: str) -> dict:
    """
    Get content of a specific file in a skill directory.

    Args:
        skill_id: Skill identifier
        file_path: Path to the file relative to skill directory

    Returns:
        File content
    """
    from pathlib import Path
    import os

    metadata, registry = _find_skill_metadata(skill_id)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill not found: {skill_id}",
        )

    skill_dir = metadata.directory
    # Convert to absolute path if needed
    if not skill_dir.is_absolute():
        skill_dir = Path(os.path.abspath(skill_dir))

    # Normalize the file path to handle forward slashes
    file_full_path = skill_dir / file_path.replace("/", os.sep)

    if not file_full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {str(e)}",
        )


@router.put("/{skill_id}/files/{file_path:path}")
async def update_skill_file_content(
    skill_id: str,
    file_path: str,
    request: dict,
) -> dict:
    """
    Update content of a specific file in a skill directory.

    Args:
        skill_id: Skill identifier
        file_path: Path to the file relative to skill directory
        request: Request body containing 'content' field

    Returns:
        Updated file info
    """
    metadata, registry = _find_skill_metadata(skill_id)

    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill not found: {skill_id}",
        )

    file_path = metadata.directory / file_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    content = request.get("content", "")
    if content is None:
        content = ""

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Invalidate cache for this skill
        registry.invalidate_cache(skill_id)

        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(metadata.directory)),
            "content": content,
            "size": len(content),
            "updated": True,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error writing file: {str(e)}",
        )
