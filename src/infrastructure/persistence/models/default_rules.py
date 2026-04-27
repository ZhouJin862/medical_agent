"""
Default rules for health assessment.

These rules will be initialized when the database is first set up.
"""
from typing import List, Dict, Any


DEFAULT_RULES: List[Dict[str, Any]] = [
    # Blood pressure threshold rule
    {
        "name": "bp_systolic_high",
        "display_name": "收缩压偏高",
        "description": "检测收缩压是否偏高（≥140mmHg）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 100,
        "enabled": True,
        "rule_config": {
            "field": "systolic_bp",
            "operator": ">=",
            "threshold": 140,
            "unit": "mmHg"
        }
    },
    {
        "name": "bp_diastolic_high",
        "display_name": "舒张压偏高",
        "description": "检测舒张压是否偏高（≥90mmHg）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 100,
        "enabled": True,
        "rule_config": {
            "field": "diastolic_bp",
            "operator": ">=",
            "threshold": 90,
            "unit": "mmHg"
        }
    },
    # Blood glucose threshold rules
    {
        "name": "fasting_glucose_high",
        "display_name": "空腹血糖偏高",
        "description": "检测空腹血糖是否偏高（≥7.0mmol/L）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "diabetes",
        "priority": 100,
        "enabled": True,
        "rule_config": {
            "field": "fasting_glucose",
            "operator": ">=",
            "threshold": 7.0,
            "unit": "mmol/L"
        }
    },
    {
        "name": "hba1c_high",
        "display_name": "糖化血红蛋白偏高",
        "description": "检测糖化血红蛋白是否偏高（≥6.5%）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "diabetes",
        "priority": 90,
        "enabled": True,
        "rule_config": {
            "field": "hba1c",
            "operator": ">=",
            "threshold": 6.5,
            "unit": "%"
        }
    },
    # BMI threshold rule
    {
        "name": "bmi_overweight",
        "display_name": "BMI超重",
        "description": "检测BMI是否超重（≥24）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "obesity",
        "priority": 100,
        "enabled": True,
        "rule_config": {
            "field": "bmi",
            "operator": ">=",
            "threshold": 24.0,
            "unit": "kg/m²"
        }
    },
    # Cholesterol threshold rule
    {
        "name": "total_cholesterol_high",
        "display_name": "总胆固醇偏高",
        "description": "检测总胆固醇是否偏高（≥5.2mmol/L）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "dyslipidemia",
        "priority": 80,
        "enabled": True,
        "rule_config": {
            "field": "total_cholesterol",
            "operator": ">=",
            "threshold": 5.2,
            "unit": "mmol/L"
        }
    },
    # Uric acid threshold rule
    {
        "name": "uric_acid_high",
        "display_name": "血尿酸偏高",
        "description": "检测血尿酸是否偏高（≥420μmol/L）",
        "rule_type": "threshold",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "gout",
        "priority": 90,
        "enabled": True,
        "rule_config": {
            "field": "uric_acid",
            "operator": ">=",
            "threshold": 420,
            "unit": "μmol/L"
        }
    },
    # Hypertension grade 2 rule
    {
        "name": "hypertension_grade_2",
        "display_name": "高血压2级",
        "description": "诊断高血压2级（收缩压≥160或舒张压≥100）",
        "rule_type": "condition",
        "category": "diagnosis",
        "target_type": "vital_sign",
        "disease_code": "hypertension",
        "priority": 95,
        "enabled": True,
        "rule_config": {
            "logic": "OR",
            "conditions": [
                {
                    "field": "systolic_bp",
                    "operator": ">=",
                    "threshold": 160
                },
                {
                    "field": "diastolic_bp",
                    "operator": ">=",
                    "threshold": 100
                }
            ]
        }
    },
    # Diabetes risk score rule
    {
        "name": "diabetes_risk_score",
        "display_name": "糖尿病风险评分",
        "description": "计算2型糖尿病风险评分",
        "rule_type": "score",
        "category": "risk_assessment",
        "target_type": "combined",
        "disease_code": "diabetes",
        "priority": 70,
        "enabled": True,
        "rule_config": {
            "factors": [
                {"name": "age", "weight": 0.3, "type": "range", "min": 40, "max": 80},
                {"name": "bmi", "weight": 0.25, "type": "range", "min": 24, "max": 35},
                {"name": "fasting_glucose", "weight": 0.3, "type": "range", "min": 5.6, "max": 7.0},
                {"name": "family_history", "weight": 0.15, "type": "binary"},
            ],
            "thresholds": {
                "low": 0.2,
                "medium": 0.4,
                "high": 0.6,
                "very_high": 0.8
            }
        }
    },
]


def get_default_rules() -> List[Dict[str, Any]]:
    """Get list of default rules for initialization."""
    return DEFAULT_RULES
