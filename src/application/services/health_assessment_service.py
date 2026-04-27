"""
Health assessment application service.

Orchestrates health assessment operations including vital signs analysis
and risk assessment.
"""
import logging
from typing import Any
from uuid import uuid4

from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException
from src.domain.shared.exceptions.patient_not_found import PatientNotFoundException
from src.domain.shared.value_objects.blood_pressure import BloodPressure
from src.domain.shared.value_objects.blood_glucose import BloodGlucose
from src.domain.shared.value_objects.lipid_profile import LipidProfile
from src.domain.shared.value_objects.uric_acid import UricAcid
from src.domain.shared.value_objects.bmi import BMI
from src.domain.shared.value_objects.patient_data import PatientData
from src.infrastructure.mcp.client_factory import MCPClientFactory

logger = logging.getLogger(__name__)


class HealthAssessmentApplicationService:
    """
    Application service for health assessment operations.

    Coordinates vital signs validation, risk assessment,
    and health profile generation.
    """

    def __init__(
        self,
        mcp_client_factory: MCPClientFactory,
    ) -> None:
        """
        Initialize HealthAssessmentApplicationService.

        Args:
            mcp_client_factory: Factory for creating MCP clients
        """
        self._mcp_client_factory = mcp_client_factory

    async def assess_vital_signs(
        self,
        patient_id: str,
        vital_signs_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Assess vital signs and generate health profile.

        Args:
            patient_id: Patient identifier
            vital_signs_data: Dictionary with vital signs measurements

        Returns:
            Health assessment profile with classifications and risks
        """
        # Validate and parse vital signs
        try:
            vital_signs = self._parse_vital_signs(vital_signs_data)
        except (ValueError, KeyError) as e:
            raise InvalidVitalSignsException(f"Invalid vital signs data: {e}")

        # Get patient profile for context
        profile_client = self._mcp_client_factory.get_client("profile")
        patient_profile: dict[str, Any] | None = None
        if profile_client:
            try:
                patient_profile = await profile_client.get_patient_profile(patient_id)
            except Exception as e:
                logger.warning(f"Failed to retrieve patient profile: {e}")

        # Create patient data context
        patient_data = self._create_patient_data(
            patient_id=patient_id,
            profile=patient_profile,
            vital_signs=vital_signs,
        )

        # Assess each vital sign
        assessments = {}
        if "blood_pressure" in vital_signs:
            assessments["blood_pressure"] = self._assess_blood_pressure(
                vital_signs["blood_pressure"]
            )
        if "blood_glucose" in vital_signs:
            assessments["blood_glucose"] = self._assess_blood_glucose(
                vital_signs["blood_glucose"]
            )
        if "lipid_profile" in vital_signs:
            assessments["lipid_profile"] = self._assess_lipid_profile(
                vital_signs["lipid_profile"]
            )
        if "uric_acid" in vital_signs:
            assessments["uric_acid"] = self._assess_uric_acid(vital_signs["uric_acid"])
        if "bmi" in vital_signs:
            assessments["bmi"] = self._assess_bmi(vital_signs["bmi"])

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(assessments)

        # Generate recommendations
        recommendations = await self._generate_recommendations(
            patient_data=patient_data,
            assessments=assessments,
            overall_risk=overall_risk,
        )

        return {
            "assessment_id": str(uuid4()),
            "patient_id": patient_id,
            "vital_signs": {k: v.to_dict() for k, v in vital_signs.items()},
            "assessments": assessments,
            "overall_risk": overall_risk,
            "recommendations": recommendations,
            "assessed_at": patient_data.assessed_at.isoformat(),
        }

    def _parse_vital_signs(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate vital signs data."""
        vital_signs = {}

        if "systolic" in data and "diastolic" in data:
            vital_signs["blood_pressure"] = BloodPressure(
                systolic=float(data["systolic"]),
                diastolic=float(data["diastolic"]),
            )

        if "fasting_glucose" in data or "random_glucose" in data:
            vital_signs["blood_glucose"] = BloodGlucose(
                fasting_glucose=float(data.get("fasting_glucose", 0)),
                random_glucose=float(data.get("random_glucose", 0)),
            )

        if "total_cholesterol" in data:
            vital_signs["lipid_profile"] = LipidProfile(
                total_cholesterol=float(data["total_cholesterol"]),
                ldl_cholesterol=float(data.get("ldl_cholesterol", 0)),
                hdl_cholesterol=float(data.get("hdl_cholesterol", 0)),
                triglycerides=float(data.get("triglycerides", 0)),
            )

        if "uric_acid" in data:
            vital_signs["uric_acid"] = UricAcid(
                value=float(data["uric_acid"]),
            )

        if "height" in data and "weight" in data:
            vital_signs["bmi"] = BMI(
                height_cm=float(data["height"]),
                weight_kg=float(data["weight"]),
            )

        if not vital_signs:
            raise ValueError("No valid vital signs provided")

        return vital_signs

    def _create_patient_data(
        self,
        patient_id: str,
        profile: dict[str, Any] | None,
        vital_signs: dict[str, Any],
    ) -> PatientData:
        """Create PatientData value object."""
        from datetime import datetime

        return PatientData(
            patient_id=patient_id,
            age=int(profile.get("age", 0)) if profile else 0,
            gender=profile.get("gender") if profile else None,
            assessed_at=datetime.now(),
        )

    def _assess_blood_pressure(self, bp: BloodPressure) -> dict[str, Any]:
        """Assess blood pressure and return classification."""
        return {
            "value": f"{bp.systolic}/{bp.diastolic} mmHg",
            "classification": bp.get_classification(),
            "is_normal": bp.is_normal(),
            "risk_level": self._get_risk_from_classification(bp.get_classification()),
        }

    def _assess_blood_glucose(self, glucose: BloodGlucose) -> dict[str, Any]:
        """Assess blood glucose and return classification."""
        return {
            "value": f"{glucose.fasting_glucose} mmol/L (空腹)",
            "classification": glucose.get_classification(),
            "is_normal": glucose.is_normal(),
            "risk_level": self._get_risk_from_classification(glucose.get_classification()),
        }

    def _assess_lipid_profile(self, lipid: LipidProfile) -> dict[str, Any]:
        """Assess lipid profile and return classification."""
        return {
            "total_cholesterol": {
                "value": f"{lipid.total_cholesterol} mmol/L",
                "classification": lipid.get_tc_classification(),
            },
            "ldl_cholesterol": {
                "value": f"{lipid.ldl_cholesterol} mmol/L",
                "classification": lipid.get_ldl_classification(),
            },
            "hdl_cholesterol": {
                "value": f"{lipid.hdl_cholesterol} mmol/L",
                "classification": lipid.get_hdl_classification(),
            },
            "triglycerides": {
                "value": f"{lipid.triglycerides} mmol/L",
                "classification": lipid.get_tg_classification(),
            },
            "is_normal": lipid.is_normal(),
            "risk_level": self._get_lipid_risk_level(lipid),
        }

    def _assess_uric_acid(self, uric_acid: UricAcid) -> dict[str, Any]:
        """Assess uric acid and return classification."""
        return {
            "value": f"{uric_acid.value} μmol/L",
            "classification": uric_acid.get_classification(),
            "is_normal": uric_acid.is_normal(),
            "risk_level": self._get_risk_from_classification(uric_acid.get_classification()),
        }

    def _assess_bmi(self, bmi: BMI) -> dict[str, Any]:
        """Assess BMI and return classification."""
        return {
            "value": f"{bmi.value:.1f}",
            "classification": bmi.get_classification(),
            "is_normal": bmi.is_normal(),
            "risk_level": self._get_risk_from_classification(bmi.get_classification()),
        }

    def _get_risk_from_classification(self, classification: str) -> str:
        """Map classification to risk level."""
        risk_mapping = {
            "normal": "normal",
            "optimal": "normal",
            "low": "low_risk",
            "borderline": "low_risk",
            "elevated": "medium_risk",
            "high": "high_risk",
            "very_high": "high_risk",
        }
        return risk_mapping.get(classification.lower(), "medium_risk")

    def _get_lipid_risk_level(self, lipid: LipidProfile) -> str:
        """Calculate overall lipid risk level."""
        if lipid.is_normal():
            return "normal"
        if not lipid.is_tc_normal() or not lipid.is_ldl_normal():
            return "high_risk"
        return "medium_risk"

    def _calculate_overall_risk(self, assessments: dict[str, Any]) -> str:
        """Calculate overall risk from all assessments."""
        if not assessments:
            return "normal"

        risk_levels = []
        for assessment in assessments.values():
            if isinstance(assessment, dict) and "risk_level" in assessment:
                risk_levels.append(assessment["risk_level"])
            elif isinstance(assessment, dict) and "is_normal" in assessment:
                if not assessment["is_normal"]:
                    risk_levels.append("medium_risk")

        if not risk_levels:
            return "normal"

        if any(r == "high_risk" for r in risk_levels):
            return "high_risk"
        if any(r == "medium_risk" for r in risk_levels):
            return "medium_risk"
        if any(r == "low_risk" for r in risk_levels):
            return "low_risk"
        return "normal"

    async def _generate_recommendations(
        self,
        patient_data: PatientData,
        assessments: dict[str, Any],
        overall_risk: str,
    ) -> list[dict[str, Any]]:
        """Generate health recommendations based on assessments."""
        recommendations = []

        # Blood pressure recommendations
        if "blood_pressure" in assessments:
            bp_assessment = assessments["blood_pressure"]
            if not bp_assessment["is_normal"]:
                recommendations.append({
                    "category": "blood_pressure",
                    "priority": "high" if bp_assessment["risk_level"] == "high_risk" else "medium",
                    "title": "血压管理建议",
                    "description": self._get_bp_recommendation(bp_assessment),
                })

        # Blood glucose recommendations
        if "blood_glucose" in assessments:
            glucose_assessment = assessments["blood_glucose"]
            if not glucose_assessment["is_normal"]:
                recommendations.append({
                    "category": "blood_glucose",
                    "priority": "high" if glucose_assessment["risk_level"] == "high_risk" else "medium",
                    "title": "血糖管理建议",
                    "description": self._get_glucose_recommendation(glucose_assessment),
                })

        # BMI recommendations
        if "bmi" in assessments:
            bmi_assessment = assessments["bmi"]
            if not bmi_assessment["is_normal"]:
                recommendations.append({
                    "category": "weight_management",
                    "priority": "medium",
                    "title": "体重管理建议",
                    "description": self._get_bmi_recommendation(bmi_assessment),
                })

        return recommendations

    def _get_bp_recommendation(self, assessment: dict[str, Any]) -> str:
        """Get blood pressure recommendation."""
        classification = assessment["classification"]
        if "高血压" in classification or "高" in classification:
            return "建议减少钠盐摄入，增加运动，保持健康体重。如血压持续偏高，请咨询医生。"
        return "建议保持健康生活方式，定期监测血压。"

    def _get_glucose_recommendation(self, assessment: dict[str, Any]) -> str:
        """Get blood glucose recommendation."""
        classification = assessment["classification"]
        if "糖尿病" in classification or "高" in classification:
            return "建议控制碳水化合物摄入，增加运动，定期监测血糖。请咨询医生进行进一步检查。"
        return "建议保持均衡饮食，定期监测血糖水平。"

    def _get_bmi_recommendation(self, assessment: dict[str, Any]) -> str:
        """Get BMI recommendation."""
        classification = assessment["classification"]
        if "肥胖" in classification:
            return "建议控制饮食总热量，增加运动量。建议每周至少150分钟中等强度运动。"
        elif "超重" in classification:
            return "建议适当控制饮食，增加运动量，维持健康体重。"
        return "建议保持当前健康生活方式。"

    async def get_patient_health_profile(
        self,
        patient_id: str,
    ) -> dict[str, Any]:
        """
        Get patient health profile from profile service.

        Args:
            patient_id: Patient identifier

        Returns:
            Patient health profile data
        """
        profile_client = self._mcp_client_factory.get_client("profile")
        if not profile_client:
            raise PatientNotFoundException(patient_id)

        try:
            profile = await profile_client.get_patient_profile(patient_id)
            return profile
        except Exception as e:
            logger.error(f"Failed to retrieve patient profile: {e}")
            raise PatientNotFoundException(patient_id)
