#!/usr/bin/env python3
"""
Cardiovascular Disease Risk Calculator for Chinese Adults
Based on Chinese Cardiovascular Disease Primary Prevention Guidelines
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Literal


class RiskCategory(Enum):
    LOW = "low"          # 低危
    MEDIUM = "medium"    # 中危
    HIGH = "high"        # 高危
    VERY_HIGH = "very_high"  # 很高危


@dataclass
class PatientData:
    age: int
    gender: Literal["male", "female"]
    sbp: Optional[int] = None        # Systolic BP
    dbp: Optional[int] = None        # Diastolic BP
    ldl_c: Optional[float] = None    # mmol/L
    tc: Optional[float] = None       # Total cholesterol
    hdl_c: Optional[float] = None    # HDL cholesterol
    tg: Optional[float] = None       # Triglycerides
    fasting_glucose: Optional[float] = None  # mmol/L
    hba1c: Optional[float] = None    # HbA1c %
    has_diabetes: bool = False
    diabetes_with_organ_damage: bool = False
    smoker: bool = False
    bmi: Optional[float] = None
    waist_circumference: Optional[float] = None
    family_history_premature_cvd: bool = False
    has_ckd: bool = False
    ckd_stage: Optional[int] = None
    has_established_cvd: bool = False  # For secondary prevention


@dataclass
class RiskAssessmentResult:
    risk_category: RiskCategory
    risk_factors_count: int
    key_factors: list[str]
    recommendations: dict
    follow_up_interval: str


class CVDRiskCalculator:
    """Cardiovascular disease risk assessment calculator for Chinese adults"""

    # Risk factor thresholds
    AGE_THRESHOLD_MALE = 45
    AGE_THRESHOLD_FEMALE = 55
    BP_THRESHOLD_HIGH = (140, 90)
    BP_THRESHOLD_VERY_HIGH = (180, 110)
    LDL_THRESHOLD_ABNORMAL = 4.1
    LDL_THRESHOLD_SEVERE = 4.9
    TC_THRESHOLD_ABNORMAL = 6.2
    TC_THRESHOLD_SEVERE = 7.2
    BMI_THRESHOLD_OBESE = 28
    BMI_THRESHOLD_OVERWEIGHT = 24
    WAIST_THRESHOLD_MALE = 90
    WAIST_THRESHOLD_FEMALE = 85

    def calculate_risk(self, patient: PatientData) -> RiskAssessmentResult:
        """Calculate cardiovascular risk category"""

        # Step 1: Check for established CVD (Secondary prevention)
        if patient.has_established_cvd:
            return self._create_result(
                RiskCategory.VERY_HIGH,
                0,
                ["Established cardiovascular disease"],
                "1-3 months"
            )

        # Step 2: Check for very high risk conditions
        if patient.diabetes_with_organ_damage or self._has_severe_ckd(patient):
            factors = ["Diabetes with target organ damage"] if patient.diabetes_with_organ_damage else []
            if self._has_severe_ckd(patient):
                factors.append("Chronic kidney disease stage 3-5")
            return self._create_result(
                RiskCategory.VERY_HIGH,
                0,
                factors,
                "1-3 months"
            )

        # Step 3: Check for automatic high risk
        severe_factors = self._check_severe_risk_factors(patient)
        if severe_factors:
            # Multiple severe factors (≥2) = Very High Risk
            if len(severe_factors) >= 2:
                return self._create_result(
                    RiskCategory.VERY_HIGH,
                    len(severe_factors),
                    severe_factors,
                    "1-3 months"
                )
            # Single severe factor = High Risk
            return self._create_result(
                RiskCategory.HIGH,
                len(severe_factors),
                severe_factors,
                "3-6 months"
            )

        # Step 4: Count major risk factors
        risk_factors = self._count_risk_factors(patient)

        # Step 5: Determine risk category
        if risk_factors["count"] == 0:
            category = RiskCategory.LOW
            follow_up = "Annually"
        elif risk_factors["count"] <= 2:
            category = RiskCategory.MEDIUM
            follow_up = "Every 6 months"
        else:
            category = RiskCategory.HIGH
            follow_up = "3-6 months"

        return self._create_result(
            category,
            risk_factors["count"],
            risk_factors["factors"],
            follow_up
        )

    def _has_severe_ckd(self, patient: PatientData) -> bool:
        """Check for CKD stage 3-5 (eGFR <60)"""
        return patient.has_ckd and patient.ckd_stage and patient.ckd_stage >= 3

    def _check_severe_risk_factors(self, patient: PatientData) -> list[str]:
        """Check for conditions that automatically confer high risk"""
        severe = []

        # Diabetes without organ damage = high risk
        if patient.has_diabetes and not patient.diabetes_with_organ_damage:
            severe.append("Diabetes mellitus")

        # Severe hypertension
        if patient.sbp and patient.dbp:
            if patient.sbp >= self.BP_THRESHOLD_VERY_HIGH[0] or patient.dbp >= self.BP_THRESHOLD_VERY_HIGH[1]:
                severe.append("Severe hypertension")

        # Severe hyperlipidemia
        if patient.ldl_c and patient.ldl_c >= self.LDL_THRESHOLD_SEVERE:
            severe.append("Severe hyperlipidemia (LDL-C ≥4.9)")
        if patient.tc and patient.tc >= self.TC_THRESHOLD_SEVERE:
            severe.append("Severe hypercholesterolemia (TC ≥7.2)")

        return severe

    def _count_risk_factors(self, patient: PatientData) -> dict:
        """Count major cardiovascular risk factors"""
        factors = []
        count = 0

        # Age
        age_threshold = self.AGE_THRESHOLD_MALE if patient.gender == "male" else self.AGE_THRESHOLD_FEMALE
        if patient.age >= age_threshold:
            factors.append(f"Age ≥{age_threshold} years")
            count += 1

        # Hypertension
        if patient.sbp and patient.dbp:
            if patient.sbp >= self.BP_THRESHOLD_HIGH[0] or patient.dbp >= self.BP_THRESHOLD_HIGH[1]:
                factors.append("Hypertension")
                count += 1

        # Dyslipidemia (LDL-C ≥3.4)
        if patient.ldl_c and patient.ldl_c >= 3.4:
            factors.append("Dyslipidemia")
            count += 1

        # Smoking
        if patient.smoker:
            factors.append("Current smoker")
            count += 1

        # Obesity (BMI ≥28)
        if patient.bmi and patient.bmi >= self.BMI_THRESHOLD_OBESE:
            factors.append("Obesity (BMI ≥28)")
            count += 1
        elif patient.waist_circumference:
            waist_threshold = self.WAIST_THRESHOLD_MALE if patient.gender == "male" else self.WAIST_THRESHOLD_FEMALE
            if patient.waist_circumference >= waist_threshold:
                factors.append(f"Central obesity (waist ≥{waist_threshold}cm)")
                count += 1

        # Family history
        if patient.family_history_premature_cvd:
            factors.append("Family history of premature CVD")
            count += 1

        return {"count": count, "factors": factors}

    def _create_result(self, category: RiskCategory, count: int,
                       factors: list[str], follow_up: str) -> RiskAssessmentResult:
        """Create risk assessment result with recommendations"""
        recommendations = self._get_recommendations(category)
        return RiskAssessmentResult(
            risk_category=category,
            risk_factors_count=count,
            key_factors=factors,
            recommendations=recommendations,
            follow_up_interval=follow_up
        )

    def _get_recommendations(self, category: RiskCategory) -> dict:
        """Get treatment recommendations by risk category"""
        if category == RiskCategory.LOW:
            return {
                "lifestyle": ["DASH/Mediterranean diet", "Regular exercise 150min/week",
                             "Weight management", "Smoking cessation if applicable"],
                "bp_target": "<140/90 mmHg",
                "ldl_target": "<3.4 mmol/L",
                "statin": "Consider if LDL-C ≥4.9",
                "antiplatelet": "Not routinely recommended",
                "follow_up": "Annual risk reassessment"
            }
        elif category == RiskCategory.MEDIUM:
            return {
                "lifestyle": ["DASH/Mediterranean diet", "Regular exercise 150min/week",
                             "Weight management", "Smoking cessation if applicable"],
                "bp_target": "<140/90 mmHg",
                "ldl_target": "<3.4 mmol/L",
                "statin": "Consider if LDL-C ≥3.4 or multiple risk factors",
                "antiplatelet": "Individualize based on bleeding risk",
                "follow_up": "Every 6 months"
            }
        elif category == RiskCategory.HIGH:
            return {
                "lifestyle": ["DASH/Mediterranean diet", "Regular exercise 150-300min/week",
                             "Weight loss 5-10%", "Complete smoking cessation"],
                "bp_target": "<130/80 mmHg",
                "ldl_target": "<2.6 mmol/L (≥50% reduction)",
                "statin": "Moderate to high intensity recommended",
                "antiplatelet": "Consider based on bleeding risk",
                "follow_up": "Every 3-6 months"
            }
        else:  # VERY_HIGH
            return {
                "lifestyle": ["DASH/Mediterranean diet", "Regular exercise as tolerated",
                             "Weight management", "Complete smoking cessation"],
                "bp_target": "<130/80 mmHg",
                "ldl_target": "<1.8 mmol/L (≥50% reduction)",
                "statin": "High intensity recommended",
                "antiplatelet": "Aspirin 75-100mg/day if not contraindicated",
                "additional": ["Consider ACEI/ARB if diabetes, CKD, or LV dysfunction",
                              "Beta-blocker if post-MI or heart failure"],
                "follow_up": "Every 1-3 months"
            }


def main():
    """Example usage"""
    import sys
    import io
    # Handle UTF-8 encoding for Windows console
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    calculator = CVDRiskCalculator()

    # Example: 50-year-old male with hypertension
    patient = PatientData(
        age=50,
        gender="male",
        sbp=150,
        dbp=95,
        ldl_c=3.8,
        has_diabetes=False,
        smoker=True,
        bmi=27
    )

    result = calculator.calculate_risk(patient)

    print(f"Risk Category: {result.risk_category.value.upper()}")
    print(f"Risk Factors Count: {result.risk_factors_count}")
    print(f"Key Factors: {', '.join(result.key_factors)}")
    print(f"\nRecommendations:")
    for key, value in result.recommendations.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
