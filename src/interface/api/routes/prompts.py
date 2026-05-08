"""
System Prompt Management API Routes.

Provides CRUD endpoints for managing system prompts
with versioning and activation support.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from src.domain.shared.services.system_prompt_service import get_system_prompt_service
from src.interface.api.dto.response import (
    SystemPromptResponse,
    SystemPromptListItem,
    SystemPromptListResponse,
    SystemPromptHistoryItem,
    SystemPromptHistoryResponse,
    SystemPromptUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


@router.get("", response_model=SystemPromptListResponse)
async def list_prompts():
    """List all active system prompts with metadata."""
    service = get_system_prompt_service()
    prompts = await service.list_prompts()
    items = [
        SystemPromptListItem(
            id=p["id"],
            prompt_key=p["prompt_key"],
            description=p["description"],
            version=p["version"],
            variables=p.get("variables"),
            updated_at=p["updated_at"],
        )
        for p in prompts
    ]
    return SystemPromptListResponse(prompts=items, total_count=len(items))


@router.get("/{key}", response_model=SystemPromptResponse)
async def get_prompt(key: str):
    """Get the active version of a system prompt by key."""
    service = get_system_prompt_service()
    detail = await service.get_prompt_detail(key)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{key}' not found",
        )
    return SystemPromptResponse(
        id=detail["id"],
        prompt_key=detail["prompt_key"],
        description=detail.get("prompt_desc", detail.get("description", "")),
        content=detail.get("prompt_content", detail.get("content", "")),
        version=detail.get("prompt_version", detail.get("version", 1)),
        is_active=detail["is_active"],
        variables=detail.get("variables") or detail.get("prompt_variables"),
        updated_at=detail.get("updated_date", detail.get("updated_at", "")),
    )


@router.get("/{key}/history", response_model=SystemPromptHistoryResponse)
async def get_prompt_history(key: str):
    """Get version history for a system prompt."""
    service = get_system_prompt_service()
    history = await service.get_history(key)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No history found for prompt '{key}'",
        )
    versions = [
        SystemPromptHistoryItem(
            id=v["id"],
            prompt_key=v["prompt_key"],
            version=v["version"],
            is_active=v["is_active"],
            description=v["description"],
            updated_at=v["updated_at"],
        )
        for v in history
    ]
    return SystemPromptHistoryResponse(prompt_key=key, versions=versions)


@router.put("/{key}", response_model=SystemPromptResponse)
async def update_prompt(key: str, request: SystemPromptUpdateRequest):
    """Update a system prompt (creates a new version and activates it)."""
    service = get_system_prompt_service()
    try:
        new_prompt = await service.update_prompt(
            key=key,
            content=request.content,
            description=request.description,
        )
        return SystemPromptResponse(
            id=new_prompt.id,
            prompt_key=new_prompt.prompt_key,
            description=new_prompt.prompt_desc,
            content=new_prompt.prompt_content,
            version=new_prompt.prompt_version,
            is_active=new_prompt.is_active,
            variables=new_prompt.get_variables_list() or None,
            updated_at=new_prompt.updated_date.isoformat() if new_prompt.updated_date else "",
        )
    except Exception as e:
        logger.error(f"Failed to update prompt '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt: {str(e)}",
        )


@router.put("/{prompt_id}/activate", response_model=SystemPromptResponse)
async def activate_version(prompt_id: str):
    """Activate a specific prompt version by its ID."""
    service = get_system_prompt_service()
    prompt = await service.activate_version(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version '{prompt_id}' not found",
        )
    return SystemPromptResponse(
        id=prompt.id,
        prompt_key=prompt.prompt_key,
        description=prompt.prompt_desc,
        content=prompt.prompt_content,
        version=prompt.prompt_version,
        is_active=prompt.is_active,
        variables=prompt.get_variables_list() or None,
        updated_at=prompt.updated_date.isoformat() if prompt.updated_date else "",
    )


@router.delete("/{prompt_id}")
async def delete_version(prompt_id: str):
    """Delete a specific prompt version (cannot delete active version)."""
    service = get_system_prompt_service()
    deleted = await service.delete_version(prompt_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete: version not found or it is the active version",
        )
    return {"message": "Prompt version deleted successfully"}
