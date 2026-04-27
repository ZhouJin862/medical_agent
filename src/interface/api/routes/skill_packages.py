"""
Skill Package API Endpoints.

Provides import/export functionality for skill packages (ZIP format).
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.domain.shared.services.skill_package_manager import (
    SkillPackageManager,
    ExportOptions,
    ImportOptions,
    get_available_skills_for_export,
)
from src.infrastructure.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/skills/packages",
    tags=["skill-packages"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class ExportRequest(BaseModel):
    """Request to export skills to a package."""
    package_name: str = Field(..., description="Name for the package")
    skills: Optional[List[str]] = Field(
        None,
        description="Specific skills to export (null = all)",
    )
    include_reference_files: bool = Field(
        default=True,
        description="Include reference files",
    )
    include_scripts: bool = Field(
        default=True,
        description="Include script files",
    )
    include_database_skills: bool = Field(
        default=True,
        description="Include database skills",
    )


class ImportRequest(BaseModel):
    """Options for importing a skill package."""
    overwrite_existing: bool = Field(
        default=False,
        description="Overwrite existing skills",
    )
    skip_existing: bool = Field(
        default=False,
        description="Skip existing skills (conflicts with overwrite)",
    )
    import_file_skills: bool = Field(
        default=True,
        description="Import file-based skills",
    )
    import_database_skills: bool = Field(
        default=True,
        description="Import database skills",
    )


class SkillInfo(BaseModel):
    """Information about an exportable skill."""
    name: str
    description: str
    source: str
    layer: Optional[str] = None
    type: Optional[str] = None


class AvailableSkillsResponse(BaseModel):
    """Response with available skills for export."""
    file: List[SkillInfo]
    database: List[SkillInfo]


class ImportErrorResponse(BaseModel):
    """An error that occurred during import."""
    skill_name: str
    error_type: str
    message: str


class ImportResultResponse(BaseModel):
    """Result of skill package import."""
    success: bool
    total_skills: int = 0
    imported_skills: List[str] = []
    skipped_skills: List[str] = []
    failed_skills: List[str] = []
    errors: List[ImportErrorResponse] = []
    warnings: List[str] = []
    manifest: Optional[dict] = None


class ExportResultResponse(BaseModel):
    """Result of skill package export."""
    success: bool
    filename: str = ""
    total_skills: int = 0
    file_skills: List[str] = []
    database_skills: List[str] = []
    warnings: List[str] = []


class ValidationResultResponse(BaseModel):
    """Result of package validation."""
    valid: bool
    manifest: Optional[dict] = None
    errors: List[ImportErrorResponse] = []
    warnings: List[str] = []


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/available", response_model=AvailableSkillsResponse)
async def get_available_skills():
    """
    Get list of skills available for export.

    Returns both file-based and database skills.
    """
    try:
        async for session in get_db_session():
            skills_data = await get_available_skills_for_export(session)
            break

        return AvailableSkillsResponse(
            file=[
                SkillInfo(**s) for s in skills_data.get("file", [])
            ],
            database=[
                SkillInfo(**s) for s in skills_data.get("database", [])
            ],
        )

    except Exception as e:
        logger.error(f"Failed to get available skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get skills: {str(e)}",
        )


@router.post("/export")
async def export_skills(request: ExportRequest):
    """
    Export skills to a ZIP package.

    Returns the package as a downloadable ZIP file.
    """
    try:
        async for session in get_db_session():
            # Create export options
            options = ExportOptions(
                include_reference_files=request.include_reference_files,
                include_scripts=request.include_scripts,
                include_database_skills=request.include_database_skills,
                skills=request.skills,
            )

            # Export package
            manager = SkillPackageManager()
            result = await manager.export_package(
                session,
                request.package_name,
                options,
            )

            if not result.success:
                if result.total_skills == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No skills found to export",
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Export failed",
                )

            # Return ZIP file
            return Response(
                content=result.package_bytes,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{result.filename}"',
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.post("/import", response_model=ImportResultResponse)
async def import_skills(
    file: UploadFile = File(..., description="ZIP package file"),
    overwrite: bool = False,
    skip_existing: bool = False,
    import_file_skills: bool = True,
    import_database_skills: bool = True,
):
    """
    Import skills from a ZIP package.

    Upload a ZIP file containing skills to import.
    """
    try:
        # Read uploaded file
        package_bytes = await file.read()

        # Validate file type
        if not file.filename or not file.filename.endswith('.zip'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only ZIP files are supported",
            )

        # Create import options
        options = ImportOptions(
            overwrite_existing=overwrite,
            skip_existing=skip_existing,
            import_file_skills=import_file_skills,
            import_database_skills=import_database_skills,
        )

        # Import package
        async for session in get_db_session():
            manager = SkillPackageManager()
            result = await manager.import_package(
                session,
                package_bytes,
                options,
            )
            break

        # Convert errors
        error_responses = [
            ImportErrorResponse(
                skill_name=e.skill_name,
                error_type=e.error_type,
                message=e.message,
            )
            for e in result.errors
        ]

        return ImportResultResponse(
            success=result.success,
            total_skills=result.total_skills,
            imported_skills=result.imported_skills,
            skipped_skills=result.skipped_skills,
            failed_skills=result.failed_skills,
            errors=error_responses,
            warnings=result.warnings,
            manifest=result.manifest.to_dict() if result.manifest else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@router.post("/debug-upload", response_model=dict)
async def debug_upload(
    file: UploadFile = File(..., description="ZIP package to debug"),
):
    """
    Debug endpoint for file upload testing.
    """
    try:
        # Read uploaded file
        package_bytes = await file.read()

        logger.info(f"Debug upload: {file.filename}, size: {len(package_bytes)} bytes")

        # Try to read as ZIP
        import zipfile
        from io import BytesIO
        try:
            with zipfile.ZipFile(BytesIO(package_bytes), 'r') as zip_file:
                files = zip_file.namelist()
                return {
                    "filename": file.filename,
                    "size": len(package_bytes),
                    "is_zip": True,
                    "files_count": len(files),
                    "files": files[:10],  # First 10 files
                }
        except Exception as e:
            return {
                "filename": file.filename,
                "size": len(package_bytes),
                "is_zip": False,
                "error": str(e),
            }

    except Exception as e:
        logger.error(f"Debug upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug failed: {str(e)}",
        )


@router.post("/validate", response_model=ValidationResultResponse)
async def validate_package(
    file: UploadFile = File(..., description="ZIP package to validate"),
):
    """
    Validate a skill package without importing.

    Checks the package structure and reports any issues.
    """
    try:
        # Read uploaded file
        package_bytes = await file.read()

        logger.info(f"Validating package: {file.filename}, size: {len(package_bytes)} bytes")

        # Validate file type
        if not file.filename or not file.filename.endswith('.zip'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only ZIP files are supported",
            )

        # Validate package
        async for session in get_db_session():
            manager = SkillPackageManager()
            result = await manager.import_package(
                session,
                package_bytes,
                ImportOptions(validate_only=True),
            )
            break

        # Convert errors
        error_responses = [
            ImportErrorResponse(
                skill_name=e.skill_name,
                error_type=e.error_type,
                message=e.message,
            )
            for e in result.errors
        ]

        return ValidationResultResponse(
            valid=result.success,
            manifest=result.manifest.to_dict() if result.manifest else None,
            errors=error_responses,
            warnings=result.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@router.get("/template")
async def download_package_template():
    """
    Download a minimal skill package template.

    Returns a ZIP file with the basic structure for creating a skill package.
    """
    import json
    from datetime import datetime
    from io import BytesIO
    import zipfile

    try:
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Create manifest
            manifest = {
                "name": "skill-package-template",
                "version": "1.0.0",
                "description": "Skill package template",
                "author": "",
                "created_at": datetime.utcnow().isoformat(),
                "skills": {
                    "file": [],
                    "database": []
                }
            }

            zip_file.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2)
            )

            # Create template SKILL.md
            skill_template = """---
name: example-skill
description: Example skill description
version: "1.0.0"
layer: domain
tags:
  - example
  - template
---

# Example Skill

## Purpose
This is a template for creating a new skill.

## Usage
Replace this content with your skill implementation.

## Expertise
Describe the domain expertise this skill provides.

## Guidelines
- Guideline 1
- Guideline 2
"""

            zip_file.writestr(
                "skills/example-skill/SKILL.md",
                skill_template
            )

            # Create README
            readme = """# Skill Package

This is a template for creating a skill package.

## Structure

- `manifest.json` - Package metadata
- `skills/` - Claude Skills (file-based)
  - `skill-name/`
    - `SKILL.md` - Main skill definition
    - `reference/` - Optional reference files
    - `scripts/` - Optional scripts
- `database/skills.json` - Optional database skills

## Creating a Package

1. Add your skills to the `skills/` directory
2. Update `manifest.json` with skill names
3. ZIP the contents
4. Import via API
"""

            zip_file.writestr("README.md", readme)

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="skill-package-template.zip"',
            },
        )

    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}",
        )


@router.get("/formats", response_model=dict)
async def get_package_format_info():
    """
    Get information about the skill package format.
    """
    return {
        "format": "ZIP",
        "version": "1.0",
        "structure": {
            "manifest.json": "Package metadata",
            "skills/": "Claude Skills (file-based)",
            "skills/{skill-name}/SKILL.md": "Main skill definition",
            "skills/{skill-name}/reference/": "Optional reference files",
            "skills/{skill-name}/scripts/": "Optional scripts",
            "database/skills.json": "Database skill definitions (optional)",
        },
        "manifest_format": {
            "name": "Package name (required)",
            "version": "Package version (default: 1.0.0)",
            "description": "Package description",
            "author": "Package author",
            "created_at": "ISO timestamp",
            "skills": {
                "file": ["List of file skill names"],
                "database": ["List of database skill names"],
            }
        },
        "examples": {
            "export_specific_skills": {
                "package_name": "my-skills",
                "skills": ["hypertension-assessment", "diabetes_assessment"],
            },
            "export_all": {
                "package_name": "all-skills",
                # skills: null (omitted) = export all
            }
        }
    }
