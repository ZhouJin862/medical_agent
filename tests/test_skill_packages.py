"""
Test script for Skill Package Import/Export functionality.
"""
import asyncio
import sys
import zipfile
from pathlib import Path
from io import BytesIO
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import init_database, get_db_session
from src.domain.shared.services.skill_package_manager import (
    SkillPackageManager,
    ExportOptions,
    ImportOptions,
    get_available_skills_for_export,
)


async def test_get_available_skills():
    """Test getting available skills for export."""
    print("\n" + "="*60)
    print("Test 1: Get Available Skills")
    print("="*60)

    try:
        async for session in get_db_session():
            skills_data = await get_available_skills_for_export(session)
            break

        file_skills = skills_data.get("file", [])
        db_skills = skills_data.get("database", [])

        print(f"[OK] Retrieved available skills")
        print(f"  - File skills: {len(file_skills)}")
        for skill in file_skills[:3]:
            print(f"    * {skill['name']}: {skill.get('description', 'N/A')[:50]}...")
        if len(file_skills) > 3:
            print(f"    ... and {len(file_skills) - 3} more")

        print(f"  - Database skills: {len(db_skills)}")
        for skill in db_skills[:3]:
            print(f"    * {skill['name']}: {skill.get('description', 'N/A')[:50]}...")
        if len(db_skills) > 3:
            print(f"    ... and {len(db_skills) - 3} more")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_export_all_skills():
    """Test exporting all skills to a package."""
    print("\n" + "="*60)
    print("Test 2: Export All Skills")
    print("="*60)

    try:
        async for session in get_db_session():
            manager = SkillPackageManager()

            options = ExportOptions(
                include_reference_files=True,
                include_scripts=True,
                include_database_skills=True,
            )

            result = await manager.export_package(
                session,
                "test-all-skills",
                options,
            )
            break

        if not result.success:
            print(f"[FAIL] Export failed")
            return False

        print(f"[OK] Export successful")
        print(f"  - Filename: {result.filename}")
        print(f"  - Total skills: {result.total_skills}")
        print(f"  - File skills: {len(result.file_skills)}")
        print(f"  - Database skills: {len(result.database_skills)}")
        print(f"  - Package size: {len(result.package_bytes)} bytes")

        # Verify ZIP structure
        with zipfile.ZipFile(BytesIO(result.package_bytes), 'r') as zip_file:
            files = zip_file.namelist()
            print(f"  - ZIP entries: {len(files)}")

            # Check for manifest
            if "manifest.json" in files:
                manifest = json.loads(zip_file.read("manifest.json").decode('utf-8'))
                print(f"  - Manifest: {manifest.get('name')} v{manifest.get('version')}")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_export_specific_skills():
    """Test exporting specific skills."""
    print("\n" + "="*60)
    print("Test 3: Export Specific Skills")
    print("="*60)

    try:
        async for session in get_db_session():
            manager = SkillPackageManager()

            options = ExportOptions(
                skills=["hypertension-assessment"],
                include_reference_files=True,
                include_scripts=False,
                include_database_skills=False,
            )

            result = await manager.export_package(
                session,
                "test-specific-skills",
                options,
            )
            break

        if not result.success:
            print(f"[FAIL] Export failed")
            return False

        print(f"[OK] Export successful")
        print(f"  - Skills exported: {result.file_skills}")

        # Verify content
        with zipfile.ZipFile(BytesIO(result.package_bytes), 'r') as zip_file:
            files = zip_file.namelist()
            print(f"  - Files in package: {files[:5]}...")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_validate_package():
    """Test validating a package."""
    print("\n" + "="*60)
    print("Test 4: Validate Package")
    print("="*60)

    try:
        # First, create a package
        async for session in get_db_session():
            manager = SkillPackageManager()

            export_options = ExportOptions(
                skills=["hypertension-assessment"],
                include_reference_files=False,
                include_scripts=False,
            )

            export_result = await manager.export_package(
                session,
                "validate-test",
                export_options,
            )
            break

        if not export_result.success:
            print(f"[FAIL] Failed to create test package")
            return False

        # Now validate it
        async for session in get_db_session():
            import_options = ImportOptions(validate_only=True)

            validate_result = await manager.import_package(
                session,
                export_result.package_bytes,
                import_options,
            )
            break

        print(f"[OK] Validation complete")
        print(f"  - Valid: {validate_result.success}")
        print(f"  - Total skills: {validate_result.total_skills}")

        if validate_result.manifest:
            print(f"  - Manifest: {validate_result.manifest.name}")

        if validate_result.warnings:
            print(f"  - Warnings: {validate_result.warnings}")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_roundtrip_export_import():
    """Test export then import (roundtrip)."""
    print("\n" + "="*60)
    print("Test 5: Roundtrip Export -> Import")
    print("="*60)

    try:
        # Export a package
        async for session in get_db_session():
            manager = SkillPackageManager()

            export_options = ExportOptions(
                skills=["hypertension-assessment"],
                include_reference_files=True,
                include_scripts=False,
                include_database_skills=False,
            )

            export_result = await manager.export_package(
                session,
                "roundtrip-test",
                export_options,
            )
            break

        if not export_result.success:
            print(f"[FAIL] Export failed")
            return False

        print(f"[OK] Export successful")

        # Import the package (with skip_existing to avoid conflicts)
        async for session in get_db_session():
            import_options = ImportOptions(
                skip_existing=True,
                import_file_skills=True,
                import_database_skills=False,
            )

            import_result = await manager.import_package(
                session,
                export_result.package_bytes,
                import_options,
            )
            break

        print(f"[OK] Import complete")
        print(f"  - Imported: {import_result.imported_skills}")
        print(f"  - Skipped: {import_result.skipped_skills}")
        print(f"  - Failed: {import_result.failed_skills}")

        if import_result.errors:
            for error in import_result.errors[:3]:
                print(f"  - Error: {error.skill_name}: {error.message}")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_export_with_database_skills():
    """Test exporting with database skills included."""
    print("\n" + "="*60)
    print("Test 6: Export with Database Skills")
    print("="*60)

    try:
        async for session in get_db_session():
            manager = SkillPackageManager()

            options = ExportOptions(
                include_database_skills=True,
                include_reference_files=False,
                include_scripts=False,
            )

            result = await manager.export_package(
                session,
                "test-with-db-skills",
                options,
            )
            break

        if not result.success:
            print(f"[FAIL] Export failed")
            return False

        print(f"[OK] Export successful")
        print(f"  - File skills: {len(result.file_skills)}")
        print(f"  - Database skills: {len(result.database_skills)}")

        # Check if database skills are in the package
        with zipfile.ZipFile(BytesIO(result.package_bytes), 'r') as zip_file:
            files = zip_file.namelist()
            has_db_skills = "database/skills.json" in files
            print(f"  - Has database skills file: {has_db_skills}")

            if has_db_skills:
                db_skills_data = json.loads(zip_file.read("database/skills.json").decode('utf-8'))
                print(f"  - Database skills count: {len(db_skills_data)}")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Skill Package Import/Export Test Suite")
    print("="*60)

    try:
        # Initialize database
        await init_database()
        print("[OK] Database initialized")

        # Run tests
        results = []

        results.append(("Get Available Skills", await test_get_available_skills()))
        results.append(("Export All Skills", await test_export_all_skills()))
        results.append(("Export Specific Skills", await test_export_specific_skills()))
        results.append(("Validate Package", await test_validate_package()))
        results.append(("Roundtrip Export/Import", await test_roundtrip_export_import()))
        results.append(("Export with Database Skills", await test_export_with_database_skills()))

        # Summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n[OK] All tests passed!")
        else:
            print(f"\n[WARN] {total - passed} test(s) failed")

    except Exception as e:
        print(f"\n[FAIL] Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
