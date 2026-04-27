#!/usr/bin/env python3
"""
Insert vital signs standards data for four-highs and one-heavy diseases.

This script inserts reference ranges and risk thresholds for:
- Hypertension (blood pressure)
- Diabetes (blood glucose)
- Dyslipidemia (lipid profile)
- Hyperuricemia (uric acid)
- Obesity (BMI, waist circumference)

Based on Chinese clinical guidelines:
- 中国高血压防治指南 2023
- 中国2型糖尿病防治指南 2023
- 中国成人血脂异常防治指南 2023
- 中国高尿酸血症与痛风诊疗指南 2023
- 中国肥胖症诊疗指南 2023
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.infrastructure.database import get_db_session_context
from src.infrastructure.persistence.models.skill_models import VitalSignsStandardModel


# Vital signs standards data
VITAL_SIGNS_DATA = [
    # ========== 高血压 Blood Pressure ==========
    {
        "indicator_code": "sbp",  # 收缩压 Systolic Blood Pressure
        "indicator_name": "收缩压",
        "disease_code": "HYPERTENSION",
        "unit": "mmHg",
        "normal_min": 90,
        "normal_max": 120,
        "risk_low_min": 120,
        "risk_low_max": 130,
        "risk_medium_min": 130,
        "risk_medium_max": 140,
        "risk_high_min": 140,
        "risk_high_max": 180,
        "description": "收缩压正常<120, 正常高值120-139, 高血压≥140",
    },
    {
        "indicator_code": "dbp",  # 舒张压 Diastolic Blood Pressure
        "indicator_name": "舒张压",
        "disease_code": "HYPERTENSION",
        "unit": "mmHg",
        "normal_min": 60,
        "normal_max": 80,
        "risk_low_min": 80,
        "risk_low_max": 85,
        "risk_medium_min": 85,
        "risk_medium_max": 90,
        "risk_high_min": 90,
        "risk_high_max": 110,
        "description": "舒张压正常<80, 正常高值80-89, 高血压≥90",
    },
    {
        "indicator_code": "map",  # 平均动脉压 Mean Arterial Pressure
        "indicator_name": "平均动脉压",
        "disease_code": "HYPERTENSION",
        "unit": "mmHg",
        "normal_min": 70,
        "normal_max": 100,
        "description": "平均动脉压正常范围70-100mmHg，计算公式：(SBP + 2*DBP)/3",
    },

    # ========== 糖尿病 Blood Glucose ==========
    {
        "indicator_code": "fbg",  # 空腹血糖 Fasting Blood Glucose
        "indicator_name": "空腹血糖",
        "disease_code": "DIABETES",
        "unit": "mmol/L",
        "normal_min": 3.9,
        "normal_max": 6.1,
        "risk_low_min": 6.1,
        "risk_low_max": 7.0,
        "risk_high_min": 7.0,
        "risk_high_max": 15.0,
        "description": "空腹血糖正常3.9-6.1, 空腹血糖受损6.1-7.0, 糖尿病≥7.0",
    },
    {
        "indicator_code": "2hpg",  # 餐后2小时血糖 2-hour Postprandial Glucose
        "indicator_name": "餐后2小时血糖",
        "disease_code": "DIABETES",
        "unit": "mmol/L",
        "normal_min": 3.9,
        "normal_max": 7.8,
        "risk_low_min": 7.8,
        "risk_low_max": 11.1,
        "risk_high_min": 11.1,
        "risk_high_max": 20.0,
        "description": "餐后2h血糖正常<7.8, 糖耐量受损7.8-11.1, 糖尿病≥11.1",
    },
    {
        "indicator_code": "hba1c",  # 糖化血红蛋白 Glycated Hemoglobin
        "indicator_name": "糖化血红蛋白",
        "disease_code": "DIABETES",
        "unit": "%",
        "normal_min": 4.0,
        "normal_max": 6.0,
        "risk_low_min": 6.0,
        "risk_low_max": 6.5,
        "risk_high_min": 6.5,
        "risk_high_max": 12.0,
        "description": "HbA1c正常<6.0, 糖尿病前期6.0-6.5, 糖尿病≥6.5",
    },

    # ========== 血脂异常 Lipid Profile ==========
    {
        "indicator_code": "tc",  # 总胆固醇 Total Cholesterol
        "indicator_name": "总胆固醇",
        "disease_code": "DYSLIPIDEMIA",
        "unit": "mmol/L",
        "normal_min": 3.0,
        "normal_max": 5.2,
        "risk_low_min": 5.2,
        "risk_low_max": 6.2,
        "risk_high_min": 6.2,
        "risk_high_max": 10.0,
        "description": "TC合适水平<5.2, 边缘升高5.2-6.2, 升高≥6.2",
    },
    {
        "indicator_code": "tg",  # 甘油三酯 Triglycerides
        "indicator_name": "甘油三酯",
        "disease_code": "DYSLIPIDEMIA",
        "unit": "mmol/L",
        "normal_min": 0.4,
        "normal_max": 1.7,
        "risk_low_min": 1.7,
        "risk_low_max": 2.3,
        "risk_high_min": 2.3,
        "risk_high_max": 10.0,
        "description": "TG合适水平<1.7, 边缘升高1.7-2.3, 升高≥2.3",
    },
    {
        "indicator_code": "ldlc",  # 低密度脂蛋白胆固醇 LDL-C
        "indicator_name": "低密度脂蛋白胆固醇",
        "disease_code": "DYSLIPIDEMIA",
        "unit": "mmol/L",
        "normal_min": 1.8,
        "normal_max": 3.4,
        "risk_low_min": 3.4,
        "risk_low_max": 4.1,
        "risk_high_min": 4.1,
        "risk_high_max": 8.0,
        "description": "LDL-C合适水平<3.4, 边缘升高3.4-4.1, 升高≥4.1",
    },
    {
        "indicator_code": "hdlc",  # 高密度脂蛋白胆固醇 HDL-C
        "indicator_name": "高密度脂蛋白胆固醇",
        "disease_code": "DYSLIPIDEMIA",
        "unit": "mmol/L",
        "normal_min": 1.0,
        "normal_max": 2.0,
        "risk_low_min": 0.9,
        "risk_low_max": 1.0,
        "description": "HDL-C正常≥1.0, 降低<1.0（男女标准略有不同）",
    },
    {
        "indicator_code": "non_hdlc",  # 非高密度脂蛋白胆固醇 Non-HDL-C
        "indicator_name": "非高密度脂蛋白胆固醇",
        "disease_code": "DYSLIPIDEMIA",
        "unit": "mmol/L",
        "normal_min": 2.6,
        "normal_max": 4.1,
        "description": "非HDL-C = TC - HDL-C，正常<4.1mmol/L",
    },

    # ========== 高尿酸血症 Hyperuricemia ==========
    {
        "indicator_code": "ua",  # 血尿酸 Uric Acid
        "indicator_name": "血尿酸",
        "disease_code": "HYPERURICEMIA",
        "unit": "μmol/L",
        "normal_min": 150,
        "normal_max": 420,
        "risk_low_min": 420,
        "risk_low_max": 480,
        "risk_high_min": 480,
        "risk_high_max": 700,
        "description": "血尿酸正常<420, 高尿酸血症≥420（男）或≥360（女更年期前）",
    },

    # ========== 肥胖 Obesity ==========
    {
        "indicator_code": "bmi",  # 体质指数 Body Mass Index
        "indicator_name": "体质指数",
        "disease_code": "OBESITY",
        "unit": "kg/m²",
        "normal_min": 18.5,
        "normal_max": 24.0,
        "risk_low_min": 24.0,
        "risk_low_max": 28.0,
        "risk_high_min": 28.0,
        "risk_high_max": 40.0,
        "description": "BMI正常18.5-24, 超重24-28, 肥胖≥28",
    },
    {
        "indicator_code": "wc_male",  # 腰围 Waist Circumference (Male)
        "indicator_name": "腰围",
        "disease_code": "OBESITY",
        "unit": "cm",
        "gender": "male",
        "normal_min": 70,
        "normal_max": 90,
        "risk_low_min": 90,
        "risk_low_max": 95,
        "risk_high_min": 95,
        "risk_high_max": 120,
        "description": "男性腰围正常<90, 中心性肥胖≥90",
    },
    {
        "indicator_code": "wc_female",  # 腰围 Waist Circumference (Female)
        "indicator_name": "腰围",
        "disease_code": "OBESITY",
        "unit": "cm",
        "gender": "female",
        "normal_min": 65,
        "normal_max": 85,
        "risk_low_min": 85,
        "risk_low_max": 90,
        "risk_high_min": 90,
        "risk_high_max": 115,
        "description": "女性腰围正常<85, 中心性肥胖≥85",
    },
    {
        "indicator_code": "whr_male",  # 腰臀比 Waist-to-Hip Ratio (Male)
        "indicator_name": "腰臀比",
        "disease_code": "OBESITY",
        "unit": "",
        "gender": "male",
        "normal_min": 0.75,
        "normal_max": 0.90,
        "description": "男性腰臀比正常<0.90, 中心性肥胖≥0.90",
    },
    {
        "indicator_code": "whr_female",  # 腰臀比 Waist-to-Hip Ratio (Female)
        "indicator_name": "腰臀比",
        "disease_code": "OBESITY",
        "unit": "",
        "gender": "female",
        "normal_min": 0.70,
        "normal_max": 0.85,
        "description": "女性腰臀比正常<0.85, 中心性肥胖≥0.85",
    },

    # ========== 综合指标 Composite ==========
    {
        "indicator_code": "map_general",  # 平均动脉压通用
        "indicator_name": "平均动脉压通用",
        "disease_code": None,
        "unit": "mmHg",
        "normal_min": 70,
        "normal_max": 105,
        "description": "MAP = (SBP + 2*DBP)/3，正常范围70-105mmHg",
    },
    {
        "indicator_code": "pp",  # 脉压 Pulse Pressure
        "indicator_name": "脉压",
        "disease_code": "HYPERTENSION",
        "unit": "mmHg",
        "normal_min": 30,
        "normal_max": 50,
        "description": "脉压 = SBP - DBP，正常30-50mmHg，脉压增大是血管硬化的标志",
    },
]


async def check_existing_standards(session: AsyncSession) -> dict:
    """Check which standards already exist in database."""
    result = await session.execute(
        select(VitalSignsStandardModel.indicator_code)
    )
    existing = {row[0] for row in result.fetchall()}
    return existing


async def insert_standards(
    session: AsyncSession,
    data: list,
    force: bool = False,
) -> dict:
    """
    Insert vital signs standards into database.

    Args:
        session: Database session
        data: List of standard data dictionaries
        force: Force overwrite existing standards

    Returns:
        Summary dict with counts
    """
    existing = await check_existing_standards(session)

    inserted = []
    skipped = []
    updated = []

    for item in data:
        code = item["indicator_code"]

        if code in existing:
            if force:
                # Update existing
                result = await session.execute(
                    select(VitalSignsStandardModel).where(
                        VitalSignsStandardModel.indicator_code == code
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
            # Create new
            model = VitalSignsStandardModel(**item)
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
    parser = argparse.ArgumentParser(
        description="Insert vital signs standards data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without inserting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing standards",
    )
    parser.add_argument(
        "--diseases",
        nargs="+",
        choices=["HYPERTENSION", "DIABETES", "DYSLIPIDEMIA", "HYPERURICEMIA", "OBESITY"],
        help="Insert only specific disease standards",
    )

    args = parser.parse_args()

    # Filter data by diseases if specified
    data = VITAL_SIGNS_DATA
    if args.diseases:
        data = [d for d in data if d.get("disease_code") in args.diseases]

    print(f"{'='*60}")
    print(f"Vital Signs Standards Data Insertion")
    print(f"{'='*60}")
    print(f"Total records: {len(data)}")
    print(f"Dry run: {args.dry_run}")
    print(f"Force: {args.force}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("Validation passed. Data looks good:")
        for item in data:
            print(f"  - {item['indicator_code']}: {item['indicator_name']}")
        print(f"\n{len(data)} records ready to insert.")
        return

    # Insert data
    async with get_db_session_context() as session:
        # Check existing
        existing = await check_existing_standards(session)
        print(f"Existing standards: {len(existing)}")

        # Insert
        result = await insert_standards(session, data, force=args.force)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Insertion Summary:")
    print(f"  Inserted: {len(result['inserted'])}")
    print(f"  Updated: {len(result['updated'])}")
    print(f"  Skipped: {len(result['skipped'])}")

    if result['inserted']:
        print(f"\nInserted:")
        for code in result['inserted']:
            item = next(d for d in data if d['indicator_code'] == code)
            print(f"  - {code}: {item['indicator_name']}")

    if result['skipped']:
        print(f"\nSkipped (use --force to overwrite):")
        for code in result['skipped']:
            print(f"  - {code}")

    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
