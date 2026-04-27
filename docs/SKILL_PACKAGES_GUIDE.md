# Skill Packages - Import/Export Guide

## Overview

Skill Packages (ZIP format) allow you to:
- **Export** skills from one environment to another
- **Backup** your skill configurations
- **Share** skills between teams
- **Distribute** skill bundles

## Package Format

### ZIP Structure

```
skill-package.zip
├── manifest.json          # Package metadata (required)
├── skills/                # Claude Skills (file-based)
│   ├── skill-name-1/
│   │   ├── SKILL.md       # Main skill definition
│   │   ├── reference/     # Optional reference files
│   │   │   └── *.md
│   │   └── scripts/       # Optional scripts
│   │       └── *.py
│   └── skill-name-2/
│       └── SKILL.md
└── database/              # Database skills (optional)
    └── skills.json        # Database skill definitions
```

### Manifest Format

```json
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
```

## API Endpoints

### 1. Get Available Skills

List all skills that can be exported.

```bash
GET /api/v2/skills/packages/available
```

**Response**:
```json
{
  "file": [
    {
      "name": "hypertension-assessment",
      "description": "Evaluates blood pressure...",
      "source": "file",
      "layer": "domain"
    }
  ],
  "database": [
    {
      "name": "health_consultation",
      "description": "General health consultation...",
      "source": "database",
      "type": "generic"
    }
  ]
}
```

### 2. Export Skills

Export skills to a ZIP package.

```bash
POST /api/v2/skills/packages/export
Content-Type: application/json

{
  "package_name": "my-skills",
  "skills": ["skill-1", "skill-2"],  // Optional: null = all skills
  "include_reference_files": true,
  "include_scripts": true,
  "include_database_skills": true
}
```

**Response**: ZIP file download

### 3. Import Skills

Import skills from a ZIP package.

```bash
POST /api/v2/skills/packages/import
Content-Type: multipart/form-data

file: <ZIP file>
overwrite: false
skip_existing: true
import_file_skills: true
import_database_skills: true
```

**Response**:
```json
{
  "success": true,
  "total_skills": 3,
  "imported_skills": ["skill-1", "skill-2"],
  "skipped_skills": ["skill-3"],
  "failed_skills": [],
  "errors": [],
  "warnings": [],
  "manifest": {
    "name": "package-name",
    "version": "1.0.0"
  }
}
```

### 4. Validate Package

Validate a package without importing.

```bash
POST /api/v2/skills/packages/validate
Content-Type: multipart/form-data

file: <ZIP file>
```

### 5. Download Template

Get a minimal package template.

```bash
GET /api/v2/skills/packages/template
```

### 6. Get Format Info

Get package format documentation.

```bash
GET /api/v2/skills/packages/formats
```

## Usage Examples

### Export All Skills

```bash
curl -X POST "http://localhost:8006/api/v2/skills/packages/export" \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "all-my-skills"
  }' \
  --output skills-package.zip
```

### Export Specific Skills

```bash
curl -X POST "http://localhost:8006/api/v2/skills/packages/export" \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "cardiology-skills",
    "skills": ["hypertension-assessment", "dyslipidemia-assessment"],
    "include_reference_files": true,
    "include_scripts": false,
    "include_database_skills": false
  }' \
  --output cardiology-skills.zip
```

### Import Package

```bash
curl -X POST "http://localhost:8006/api/v2/skills/packages/import" \
  -F "file=@skills-package.zip" \
  -F "skip_existing=true"
```

### Validate Before Import

```bash
curl -X POST "http://localhost:8006/api/v2/skills/packages/validate" \
  -F "file=@skills-package.zip"
```

## Import Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `overwrite_existing` | boolean | false | Overwrite skills that already exist |
| `skip_existing` | boolean | false | Skip existing skills (conflicts with overwrite) |
| `import_file_skills` | boolean | true | Import file-based skills |
| `import_database_skills` | boolean | true | Import database skills |

**Conflict Handling**:
- If both `overwrite_existing` and `skip_existing` are false: Import fails for conflicts
- If `skip_existing` is true: Existing skills are skipped
- If `overwrite_existing` is true: Existing skills are replaced

## Export Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `package_name` | string | required | Name for the package |
| `skills` | string[] | null | Specific skills to export (null = all) |
| `include_reference_files` | boolean | true | Include reference/ files |
| `include_scripts` | boolean | true | Include scripts/ files |
| `include_database_skills` | boolean | true | Include database skills |

## Use Cases

### 1. Environment Migration

Export from development, import to production:

```bash
# Development: Export
curl -X POST "http://dev:8006/api/v2/skills/packages/export" \
  -d '{"package_name": "production-skills"}' \
  --output skills.zip

# Production: Import
curl -X POST "http://prod:8006/api/v2/skills/packages/import" \
  -F "file=@skills.zip" \
  -F "overwrite=true"
```

### 2. Backup Skills

```bash
# Export all skills as backup
curl -X POST "http://localhost:8006/api/v2/skills/packages/export" \
  -d '{"package_name": "backup-2024-03-24"}' \
  --output backup-2024-03-24.zip
```

### 3. Share Skills Between Teams

```bash
# Team A creates and exports
curl -X POST "http://localhost:8006/api/v2/skills/packages/export" \
  -d '{"package_name": "shared-cardiology", "skills": ["hypertension-assessment"]}' \
  --output cardiology.zip

# Team B imports
curl -X POST "http://localhost:8006/api/v2/skills/packages/import" \
  -F "file=@cardiology.zip"
```

### 4. Version Skills

```bash
# Export versioned package
curl -X POST "http://localhost:8006/api/v2/skills/packages/export" \
  -d '{"package_name": "hypertension-assessment-v1.2", "skills": ["hypertension-assessment"]}' \
  --output hypertension-v1.2.zip
```

## Python Usage

### Export

```python
from src.infrastructure.database import get_db_session
from src.domain.shared.services.skill_package_manager import (
    SkillPackageManager,
    ExportOptions,
)

async def export_skills():
    async for session in get_db_session():
        manager = SkillPackageManager()

        options = ExportOptions(
            package_name="my-skills",
            skills=["hypertension-assessment"],
            include_reference_files=True,
        )

        result = await manager.export_package(session, "my-skills", options)

        if result.success:
            with open("skills.zip", "wb") as f:
                f.write(result.package_bytes)
            print(f"Exported {result.total_skills} skills")
```

### Import

```python
async def import_skills():
    async for session in get_db_session():
        manager = SkillPackageManager()

        # Read package
        with open("skills.zip", "rb") as f:
            package_bytes = f.read()

        options = ImportOptions(
            skip_existing=True,
        )

        result = await manager.import_package(session, package_bytes, options)

        print(f"Imported: {result.imported_skills}")
        print(f"Skipped: {result.skipped_skills}")
        print(f"Failed: {result.failed_skills}")
```

## Best Practices

### 1. Always Validate Before Import

```bash
# First validate
curl -X POST "http://localhost:8006/api/v2/skills/packages/validate" \
  -F "file=@skills.zip"

# Then import
curl -X POST "http://localhost:8006/api/v2/skills/packages/import" \
  -F "file=@skills.zip"
```

### 2. Use Versioned Package Names

```
good: hypertension-assessment-v1.0.zip
good: hypertension-assessment-v1.1.zip
bad: hypertension-assessment.zip
```

### 3. Include Reference Files for Complete Skills

```json
{
  "package_name": "complete-skills",
  "include_reference_files": true,
  "include_scripts": true
}
```

### 4. Test Imports in Development First

```bash
# 1. Validate
curl -X POST "http://dev:8006/api/v2/skills/packages/validate" -F "file=@skills.zip"

# 2. Import with skip_existing
curl -X POST "http://dev:8006/api/v2/skills/packages/import" \
  -F "file=@skills.zip" \
  -F "skip_existing=true"

# 3. Verify skills work

# 4. Export and import to production
```

### 5. Document Custom Skills

Add a README.md to your package:

```
skill-package.zip
├── manifest.json
├── README.md           # Document your skills
└── skills/
    └── ...
```

## Troubleshooting

### Issue: Import fails with "already exists"

**Cause**: Skill with same name exists and `overwrite` is false

**Solution**:
```bash
# Option 1: Skip existing
curl -X POST ".../import" -F "skip_existing=true"

# Option 2: Overwrite
curl -X POST ".../import" -F "overwrite=true"
```

### Issue: Export includes unexpected skills

**Cause**: Not specifying skills list

**Solution**:
```bash
# Explicitly list skills
curl -X POST ".../export" \
  -d '{"package_name": "specific", "skills": ["skill-1", "skill-2"]}'
```

### Issue: Reference files missing

**Cause**: `include_reference_files` is false

**Solution**:
```bash
curl -X POST ".../export" \
  -d '{"include_reference_files": true}'
```

### Issue: Database skills not imported

**Cause**: `import_database_skills` is false

**Solution**:
```bash
curl -X POST ".../import" \
  -F "import_database_skills=true"
```

## Package Creation Example

To manually create a skill package:

```bash
# 1. Create directory structure
mkdir -p my-package/skills/hypertension-assessment/reference

# 2. Copy skill files
cp skills/hypertension-assessment/SKILL.md \
   my-package/skills/hypertension-assessment/
cp skills/hypertension-assessment/reference/*.md \
   my-package/skills/hypertension-assessment/reference/

# 3. Create manifest.json
cat > my-package/manifest.json << EOF
{
  "name": "my-hypertension-skills",
  "version": "1.0.0",
  "description": "Custom hypertension assessment skills",
  "author": "Your Name",
  "skills": {
    "file": ["hypertension-assessment"],
    "database": []
  }
}
EOF

# 4. Create ZIP
cd my-package
zip -r ../my-package.zip .
cd ..

# 5. Validate and import
curl -X POST "http://localhost:8006/api/v2/skills/packages/validate" \
  -F "file=@my-package.zip"
```

## Summary

| Feature | Endpoint | Purpose |
|---------|----------|---------|
| List skills | `GET /packages/available` | See what can be exported |
| Export | `POST /packages/export` | Create ZIP package |
| Import | `POST /packages/import` | Load from ZIP |
| Validate | `POST /packages/validate` | Check package |
| Template | `GET /packages/template` | Get template ZIP |
| Format info | `GET /packages/formats` | Get format docs |
