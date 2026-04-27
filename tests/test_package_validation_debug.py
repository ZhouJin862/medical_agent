"""
Debug test for skill package validation.
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
)


async def debug_export_and_validate():
    """Export a package and then validate it."""
    print("="*60)
    print("Debug: Export and Validate Package")
    print("="*60)

    try:
        # Initialize database
        await init_database()

        # Export a package
        print("\n1. Exporting package...")
        async for session in get_db_session():
            manager = SkillPackageManager()

            options = ExportOptions(
                skills=["hypertension-assessment"],
                include_reference_files=True,
                include_scripts=False,
            )

            result = await manager.export_package(
                session,
                "debug-test",
                options,
            )
            break

        if not result.success:
            print(f"[FAIL] Export failed")
            return

        print(f"[OK] Export successful")
        print(f"  - File skills: {result.file_skills}")
        print(f"  - Package size: {len(result.package_bytes)} bytes")

        # Inspect ZIP contents
        print("\n2. Inspecting ZIP contents...")
        with zipfile.ZipFile(BytesIO(result.package_bytes), 'r') as zip_file:
            files = zip_file.namelist()
            print(f"  Files in ZIP ({len(files)} total):")
            for f in files:
                print(f"    - {f}")

            # Read manifest
            print("\n3. Reading manifest...")
            manifest_bytes = zip_file.read("manifest.json")
            manifest = json.loads(manifest_bytes.decode('utf-8'))
            print(f"  - Name: {manifest.get('name')}")
            print(f"  - Version: {manifest.get('version')}")
            print(f"  - Skills: {manifest.get('skills')}")

        # Validate the package
        print("\n4. Validating package...")
        async for session in get_db_session():
            manager = SkillPackageManager()

            validate_result = await manager.import_package(
                session,
                result.package_bytes,
                ImportOptions(validate_only=True),
            )
            break

        print(f"  - Valid: {validate_result.success}")
        print(f"  - Errors: {len(validate_result.errors)}")
        for err in validate_result.errors:
            print(f"    * {err.skill_name}: {err.message}")

        print(f"  - Warnings: {len(validate_result.warnings)}")
        for warn in validate_result.warnings:
            print(f"    * {warn}")

        if validate_result.success:
            print("\n[OK] Validation passed!")
        else:
            print("\n[FAIL] Validation failed!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


async def debug_validate_existing_package(zip_path: str):
    """Validate an existing package file."""
    print("="*60)
    print(f"Debug: Validate Existing Package: {zip_path}")
    print("="*60)

    try:
        # Read the package
        with open(zip_path, 'rb') as f:
            package_bytes = f.read()

        # Inspect ZIP contents
        print("\n1. Inspecting ZIP contents...")
        with zipfile.ZipFile(BytesIO(package_bytes), 'r') as zip_file:
            files = zip_file.namelist()
            print(f"  Files in ZIP ({len(files)} total):")
            for f in files:
                print(f"    - {f}")

            # Read manifest
            print("\n2. Reading manifest...")
            try:
                manifest_bytes = zip_file.read("manifest.json")
                manifest = json.loads(manifest_bytes.decode('utf-8'))
                print(f"  - Name: {manifest.get('name')}")
                print(f"  - Version: {manifest.get('version')}")
                print(f"  - Skills: {manifest.get('skills')}")
            except Exception as e:
                print(f"  [ERROR] Failed to read manifest: {e}")
                return

        # Validate the package
        print("\n3. Validating package...")
        await init_database()

        async for session in get_db_session():
            manager = SkillPackageManager()

            validate_result = await manager.import_package(
                session,
                package_bytes,
                ImportOptions(validate_only=True),
            )
            break

        print(f"  - Valid: {validate_result.success}")
        print(f"  - Errors: {len(validate_result.errors)}")
        for err in validate_result.errors:
            print(f"    * {err.skill_name}: {err.message}")

        print(f"  - Warnings: {len(validate_result.warnings)}")
        for warn in validate_result.warnings:
            print(f"    * {warn}")

        if validate_result.success:
            print("\n[OK] Validation passed!")
        else:
            print("\n[FAIL] Validation failed!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run debug tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Debug skill package validation")
    parser.add_argument("--validate", type=str, help="Path to existing ZIP file to validate")
    parser.add_argument("--export-validate", action="store_true", help="Export and then validate")

    args = parser.parse_args()

    if args.validate:
        await debug_validate_existing_package(args.validate)
    elif args.export_validate:
        await debug_export_and_validate()
    else:
        print("Usage:")
        print("  --validate <path>     Validate an existing package")
        print("  --export-validate     Export a test package and validate it")
        print("\nExample:")
        print("  python test_package_validation_debug.py --export-validate")


if __name__ == "__main__":
    asyncio.run(main())
