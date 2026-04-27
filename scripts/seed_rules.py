"""
Seed rules for four-highs-one-heavy diseases.

Inserts configured rules for hypertension, diabetes, dyslipidemia,
gout, and obesity assessment.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config.settings import get_settings
from src.infrastructure.persistence.models.rule_models import (
    RuleModel,
    VitalSignStandardModel,
    RiskScoreRuleModel,
)
from src.infrastructure.persistence.models.base import Base
from uuid import uuid4


# Rule definitions for four-highs diseases
HYPERTENSION_RULES = [
    {
        "name": "hypertension_bp_high",
        "display_name": "高血压诊断：血压偏高",
        "description": "收缩压≥140mmHg或舒张压≥90mmHg",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 100,
        "rule_config": {
            "conditions": [
                {"field": "systolic", "operator": ">=", "threshold": 140},
                {"field": "diastolic", "operator": ">=", "threshold": 90}
            ],
            "logic": "OR",
            "confidence": 0.95
        }
    },
    {
        "name": "hypertension_bp_grade1",
        "display_name": "高血压1级",
        "description": "收缩压140-159或舒张压90-99",
        "rule_type": "range",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 90,
        "rule_config": {
            "systolic_min": 140, "systolic_max": 159,
            "diastolic_min": 90, "diastolic_max": 99,
            "logic": "OR",
            "confidence": 0.9
        }
    },
    {
        "name": "hypertension_bp_grade2",
        "display_name": "高血压2级",
        "description": "收缩压160-179或舒张压100-109",
        "rule_type": "range",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 91,
        "rule_config": {
            "systolic_min": 160, "systolic_max": 179,
            "diastolic_min": 100, "diastolic_max": 109,
            "logic": "OR",
            "confidence": 0.95
        }
    },
    {
        "name": "hypertension_bp_grade3",
        "display_name": "高血压3级",
        "description": "收缩压≥180或舒张压≥110",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 92,
        "rule_config": {
            "conditions": [
                {"field": "systolic", "operator": ">=", "threshold": 180},
                {"field": "diastolic", "operator": ">=", "threshold": 110}
            ],
            "logic": "OR",
            "confidence": 1.0
        }
    },
]

DIABETES_RULES = [
    {
        "name": "diabetes_fasting_glucose_high",
        "display_name": "糖尿病诊断：空腹血糖高",
        "description": "空腹血糖≥7.0mmol/L",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "diabetes",
        "priority": 100,
        "rule_config": {
            "field": "fasting_glucose",
            "operator": ">=",
            "threshold": 7.0,
            "confidence": 0.95
        }
    },
    {
        "name": "diabetes_impaired_glucose",
        "display_name": "糖尿病前期：空腹血糖受损",
        "description": "空腹血糖6.1-6.9mmol/L",
        "rule_type": "range",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "diabetes",
        "priority": 80,
        "rule_config": {
            "field": "fasting_glucose",
            "min": 6.1,
            "max": 6.9,
            "confidence": 0.9
        }
    },
    {
        "name": "diabetes_hba1c_high",
        "display_name": "糖尿病诊断：糖化血红蛋白高",
        "description": "HbA1c≥6.5%",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "diabetes",
        "priority": 95,
        "rule_config": {
            "field": "hba1c",
            "operator": ">=",
            "threshold": 6.5,
            "confidence": 0.95
        }
    },
]

DYSLIPIDEMIA_RULES = [
    {
        "name": "dyslipidemia_high_tc",
        "display_name": "血脂异常：总胆固醇高",
        "description": "总胆固醇≥6.2mmol/L",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "dyslipidemia",
        "priority": 90,
        "rule_config": {
            "field": "total_cholesterol",
            "operator": ">=",
            "threshold": 6.2,
            "confidence": 0.9
        }
    },
    {
        "name": "dyslipidemia_high_ldl",
        "display_name": "血脂异常：低密度脂蛋白高",
        "description": "LDL-C≥4.1mmol/L",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "dyslipidemia",
        "priority": 95,
        "rule_config": {
            "field": "ldl_cholesterol",
            "operator": ">=",
            "threshold": 4.1,
            "confidence": 0.95
        }
    },
    {
        "name": "dyslipidemia_low_hdl",
        "display_name": "血脂异常：高密度脂蛋白低",
        "description": "HDL-C<1.0mmol/L",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "dyslipidemia",
        "priority": 85,
        "rule_config": {
            "field": "hdl_cholesterol",
            "operator": "<",
            "threshold": 1.0,
            "confidence": 0.9
        }
    },
    {
        "name": "dyslipidemia_high_tg",
        "display_name": "血脂异常：甘油三酯高",
        "description": "甘油三酯≥2.3mmol/L",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "dyslipidemia",
        "priority": 85,
        "rule_config": {
            "field": "triglycerides",
            "operator": ">=",
            "threshold": 2.3,
            "confidence": 0.9
        }
    },
]

GOUT_RULES = [
    {
        "name": "gout_hyperuricemia",
        "display_name": "高尿酸血症诊断",
        "description": "尿酸≥420μmol/L(男)或≥360μmol/L(女)",
        "rule_type": "condition",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "gout",
        "priority": 100,
        "rule_config": {
            "conditions": [
                {"field": "uric_acid", "operator": ">=", "threshold": 420, "gender": "male"},
                {"field": "uric_acid", "operator": ">=", "threshold": 360, "gender": "female"}
            ],
            "logic": "OR",
            "confidence": 0.95
        }
    },
    {
        "name": "gout_risk_score",
        "display_name": "痛风风险评分",
        "description": "根据尿酸、BMI、饮酒等评估痛风风险",
        "rule_type": "score",
        "category": "risk_assessment",
        "target_type": "combined",
        "disease_code": "gout",
        "priority": 90,
        "rule_config": {
            "factors": [
                {"name": "uric_acid", "weight": 0.4, "type": "range", "min": 200, "max": 600},
                {"name": "bmi", "weight": 0.25, "type": "range", "min": 18, "max": 35},
                {"name": "alcohol_consumption", "weight": 0.2, "type": "range", "min": 0, "max": 10},
                {"name": "family_history", "weight": 0.15, "type": "binary"}
            ],
            "thresholds": {"low": 0.3, "medium": 0.5, "high": 0.7, "very_high": 0.85}
        }
    },
]

OBESITY_RULES = [
    {
        "name": "obesity_bmi_high",
        "display_name": "肥胖诊断：BMI高",
        "description": "BMI≥28kg/m²",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "obesity",
        "priority": 100,
        "rule_config": {
            "field": "bmi",
            "operator": ">=",
            "threshold": 28.0,
            "confidence": 0.95
        }
    },
    {
        "name": "obesity_overweight",
        "display_name": "超重诊断",
        "description": "BMI 24-28kg/m²",
        "rule_type": "range",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "obesity",
        "priority": 90,
        "rule_config": {
            "field": "bmi",
            "min": 24.0,
            "max": 28.0,
            "confidence": 0.9
        }
    },
    {
        "name": "obesity_metabolic_syndrome",
        "display_name": "代谢综合征诊断",
        "description": "满足以下3项及以上：中心性肥胖、高血压、高血糖、高血脂",
        "rule_type": "score",
        "category": "diagnosis",
        "target_type": "combined",
        "disease_code": "metabolic_syndrome",
        "priority": 95,
        "rule_config": {
            "factors": [
                {"name": "waist_circumference", "weight": 0.25, "type": "threshold", "threshold": 90},
                {"name": "systolic_bp", "weight": 0.25, "type": "threshold", "threshold": 130},
                {"name": "diastolic_bp", "weight": 0.25, "type": "threshold", "threshold": 85},
                {"name": "fasting_glucose", "weight": 0.25, "type": "threshold", "threshold": 5.6},
                {"name": "tg", "weight": 0.25, "type": "threshold", "threshold": 1.7},
                {"name": "hdl_low", "weight": 0.25, "type": "threshold", "threshold": 1.0}
            ],
            "threshold": 3,
            "thresholds": {"low": 2, "medium": 3, "high": 4, "very_high": 5}
        }
    },
]


async def seed_rules():
    """Seed all rules to database."""
    settings = get_settings()

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed hypertension rules
        print("Seeding hypertension rules...")
        for rule_data in HYPERTENSION_RULES:
            rule = RuleModel(
                id=uuid4().hex,
                **rule_data
            )
            session.add(rule)

        # Seed diabetes rules
        print("Seeding diabetes rules...")
        for rule_data in DIABETES_RULES:
            rule = RuleModel(
                id=uuid4().hex,
                **rule_data
            )
            session.add(rule)

        # Seed dyslipidemia rules
        print("Seeding dyslipidemia rules...")
        for rule_data in DYSLIPIDEMIA_RULES:
            rule = RuleModel(
                id=uuid4().hex,
                **rule_data
            )
            session.add(rule)

        # Seed gout rules
        print("Seeding gout rules...")
        for rule_data in GOUT_RULES:
            rule = RuleModel(
                id=uuid4().hex,
                **rule_data
            )
            session.add(rule)

        # Seed obesity rules
        print("Seeding obesity rules...")
        for rule_data in OBESITY_RULES:
            rule = RuleModel(
                id=uuid4().hex,
                **rule_data
            )
            session.add(rule)

        await session.commit()
        print(f"Seeded {len(HYPERTENSION_RULES) + len(DIABETES_RULES) + len(DYSLIPIDEMIA_RULES) + len(GOUT_RULES) + len(OBESITY_RULES)} rules")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_rules())
