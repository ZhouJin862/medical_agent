#!/usr/bin/env python3
"""
Insert disease types data (四高一重).

This script inserts the four-highs (四高) and one-heavy (一重) disease types.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.infrastructure.database import get_db_session_context
from src.infrastructure.persistence.models.skill_models import DiseaseTypeModel


DISEASE_TYPES_DATA = [
    # 四高 (Four Highs)
    {
        "code": "HYPERTENSION",
        "name": "高血压",
        "name_en": "Hypertension",
        "category": "four_highs",
        "icd_code": "I10",
        "description": "动脉血压持续升高的慢性疾病，是心血管疾病的主要危险因素",
    },
    {
        "code": "DIABETES",
        "name": "糖尿病",
        "name_en": "Diabetes Mellitus",
        "category": "four_highs",
        "icd_code": "E11",
        "description": "以血糖升高为特征的代谢性疾病，分为1型和2型",
    },
    {
        "code": "DYSLIPIDEMIA",
        "name": "血脂异常",
        "name_en": "Dyslipidemia",
        "category": "four_highs",
        "icd_code": "E78",
        "description": "血浆中胆固醇或甘油三酯水平升高，或高密度脂蛋白胆固醇水平降低",
    },
    {
        "code": "HYPERURICEMIA",
        "name": "高尿酸血症",
        "name_en": "Hyperuricemia",
        "category": "four_highs",
        "icd_code": "E79",
        "description": "血尿酸水平升高的代谢性疾病，可导致痛风和肾结石",
    },
    # 一重 (One Heavy - 肥胖)
    {
        "code": "OBESITY",
        "name": "肥胖症",
        "name_en": "Obesity",
        "category": "obesity",
        "icd_code": "E66",
        "description": "体内脂肪堆积过多，可能损害健康的慢性代谢性疾病",
    },
]


async def check_existing_diseases(session: AsyncSession) -> set:
    """Check which disease types already exist."""
    result = await session.execute(
        select(DiseaseTypeModel.code)
    )
    existing = {row[0] for row in result.fetchall()}
    return existing


async def insert_disease_types(
    session: AsyncSession,
    data: list,
    force: bool = False,
) -> dict:
    """Insert disease types into database."""
    existing = await check_existing_diseases(session)

    inserted = []
    skipped = []
    updated = []

    for item in data:
        code = item["code"]

        if code in existing:
            if force:
                result = await session.execute(
                    select(DiseaseTypeModel).where(
                        DiseaseTypeModel.code == code
                    )
                )
                model = result.scalar_one_or_none()
                if model:
                    for key, value in item.items():
                        setattr(model, key, value)
                    updated.append(code)
            else:
                skipped.append(code)
                continue
        else:
            model = DiseaseTypeModel(**item)
            session.add(model)
            inserted.append(code)

    await session.commit()

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Insert disease types data")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing data")
    parser.add_argument("--dry-run", action="store_true", help="Validate without inserting")

    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"Disease Types Data Insertion (四高一重)")
    print(f"{'='*60}")
    print(f"Total records: {len(DISEASE_TYPES_DATA)}")
    print(f"Force: {args.force}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("Validation passed. Data looks good:")
        for item in DISEASE_TYPES_DATA:
            print(f"  - {item['code']}: {item['name']}")
        print(f"\n{len(DISEASE_TYPES_DATA)} records ready to insert.")
        return

    async with get_db_session_context() as session:
        # Check existing
        existing = await check_existing_diseases(session)
        print(f"Existing disease types: {len(existing)}")

        # Insert
        result = await insert_disease_types(session, DISEASE_TYPES_DATA, force=args.force)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Insertion Summary:")
    print(f"  Inserted: {len(result['inserted'])}")
    print(f"  Updated: {len(result['updated'])}")
    print(f"  Skipped: {len(result['skipped'])}")

    if result['inserted']:
        print(f"\nInserted:")
        for code in result['inserted']:
            item = next(d for d in DISEASE_TYPES_DATA if d['code'] == code)
            print(f"  - {code}: {item['name']}")

    if result['skipped']:
        print(f"\nSkipped (use --force to overwrite):")
        for code in result['skipped']:
            print(f"  - {code}")

    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
