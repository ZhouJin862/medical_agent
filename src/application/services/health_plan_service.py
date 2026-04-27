"""
Health plan application service.

Orchestrates health plan generation and management operations.
"""
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.domain.health_plan.entities.health_plan import HealthPlan, PlanType
from src.domain.health_plan.entities.prescriptions.diet_prescription import (
    DietPrescription,
)
from src.domain.health_plan.entities.prescriptions.exercise_prescription import (
    ExercisePrescription,
)
from src.domain.health_plan.entities.prescriptions.medication_prescription import (
    MedicationPrescription,
)
from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
    SleepPrescription,
)
from src.domain.health_plan.entities.prescriptions.psychological_prescription import (
    PsychologicalPrescription,
)
from src.domain.health_plan.repositories.i_health_plan_repository import (
    IHealthPlanRepository,
)
from src.domain.health_plan.value_objects.health_plan_id import HealthPlanId
from src.domain.health_plan.value_objects.target_goals import TargetGoals, TargetGoal
from src.domain.shared.exceptions.patient_not_found import PatientNotFoundException
from src.infrastructure.mcp.client_factory import MCPClientFactory

logger = logging.getLogger(__name__)


class HealthPlanApplicationService:
    """
    Application service for health plan operations.

    Coordinates health plan creation, prescription generation,
    and plan management.
    """

    def __init__(
        self,
        health_plan_repository: IHealthPlanRepository,
        mcp_client_factory: MCPClientFactory,
    ) -> None:
        """
        Initialize HealthPlanApplicationService.

        Args:
            health_plan_repository: Repository for health plan operations
            mcp_client_factory: Factory for creating MCP clients
        """
        self._health_plan_repository = health_plan_repository
        self._mcp_client_factory = mcp_client_factory

    async def generate_health_plan(
        self,
        patient_id: str,
        assessment_data: dict[str, Any] | None = None,
        plan_type: str = "preventive",
    ) -> dict[str, Any]:
        """
        Generate a new health plan for a patient.

        Args:
            patient_id: Patient identifier
            assessment_data: Health assessment data (optional)
            plan_type: Type of plan to generate

        Returns:
            Generated health plan data
        """
        # Get patient profile
        profile_client = self._mcp_client_factory.get_client("profile")
        patient_profile: dict[str, Any] | None = None
        if profile_client:
            try:
                patient_profile = await profile_client.get_patient_profile(patient_id)
            except Exception as e:
                logger.warning(f"Failed to retrieve patient profile: {e}")

        if not patient_profile:
            raise PatientNotFoundException(patient_id)

        # Create plan ID
        plan_id = HealthPlanId(value=str(uuid4()))

        # Determine plan type
        plan_type_enum = PlanType(plan_type) if isinstance(plan_type, str) else plan_type

        # Create target goals
        target_goals = self._create_target_goals(
            patient_profile=patient_profile,
            assessment_data=assessment_data,
        )

        # Generate prescriptions
        prescriptions = await self._generate_prescriptions(
            patient_id=patient_id,
            patient_profile=patient_profile,
            assessment_data=assessment_data,
            plan_type=plan_type_enum,
        )

        # Create health plan
        health_plan = HealthPlan(
            plan_id=plan_id,
            patient_id=patient_id,
            plan_type=plan_type_enum,
            prescriptions=prescriptions,
            target_goals=target_goals,
        )

        # Mark as generated
        health_plan.mark_as_generated()

        # Save plan
        await self._health_plan_repository.save(health_plan)

        return health_plan.generate_summary()

    def _create_target_goals(
        self,
        patient_profile: dict[str, Any],
        assessment_data: dict[str, Any] | None,
    ) -> TargetGoals:
        """Create target goals based on patient profile and assessment."""
        goals = []

        # Add goals based on assessment data
        if assessment_data:
            assessments = assessment_data.get("assessments", {})

            # Blood pressure goal
            if "blood_pressure" in assessments:
                bp = assessments["blood_pressure"]
                if not bp.get("is_normal", True):
                    goals.append(TargetGoal(
                        goal_id=str(uuid4()),
                        category="blood_pressure",
                        title="血压控制目标",
                        description="将血压控制在正常范围内",
                        target_value="收缩压<120 mmHg，舒张压<80 mmHg",
                        current_status=bp.get("classification", "未知"),
                        priority="high" if bp.get("risk_level") == "high_risk" else "medium",
                        deadline_days=90,
                    ))

            # Blood glucose goal
            if "blood_glucose" in assessments:
                glucose = assessments["blood_glucose"]
                if not glucose.get("is_normal", True):
                    goals.append(TargetGoal(
                        goal_id=str(uuid4()),
                        category="blood_glucose",
                        title="血糖控制目标",
                        description="将血糖控制在正常范围内",
                        target_value="空腹血糖<6.1 mmol/L",
                        current_status=glucose.get("classification", "未知"),
                        priority="high" if glucose.get("risk_level") == "high_risk" else "medium",
                        deadline_days=90,
                    ))

            # BMI goal
            if "bmi" in assessments:
                bmi = assessments["bmi"]
                if not bmi.get("is_normal", True):
                    goals.append(TargetGoal(
                        goal_id=str(uuid4()),
                        category="weight_management",
                        title="体重管理目标",
                        description="将体重控制在正常范围内",
                        target_value="BMI 18.5-23.9",
                        current_status=bmi.get("classification", "未知"),
                        priority="medium",
                        deadline_days=120,
                    ))

        # Add default wellness goals if no specific issues
        if not goals:
            goals.extend([
                TargetGoal(
                    goal_id=str(uuid4()),
                    category="wellness",
                    title="保持健康生活方式",
                    description="维持当前健康状态",
                    target_value="定期体检，健康饮食，适量运动",
                    current_status="良好",
                    priority="low",
                    deadline_days=180,
                ),
                TargetGoal(
                    goal_id=str(uuid4()),
                    category="exercise",
                    title="运动目标",
                    description="每周保持规律运动",
                    target_value="每周至少150分钟中等强度运动",
                    current_status="待开始",
                    priority="medium",
                    deadline_days=30,
                ),
            ])

        return TargetGoals(goals=goals)

    async def _generate_prescriptions(
        self,
        patient_id: str,
        patient_profile: dict[str, Any],
        assessment_data: dict[str, Any] | None,
        plan_type: PlanType,
    ) -> list:
        """Generate prescriptions for the health plan."""
        prescriptions = []
        now = datetime.now()

        # Get medication recommendations
        medication_client = self._mcp_client_factory.get_client("medication")
        service_client = self._mcp_client_factory.get_client("service")

        # Generate diet prescription
        diet_prescription = DietPrescription(
            prescription_id=str(uuid4()),
            patient_id=patient_id,
            created_at=now,
            dietary_recommendations=self._get_dietary_recommendations(
                assessment_data=assessment_data,
            ),
            restrictions=self._get_dietary_restrictions(
                patient_profile=patient_profile,
                assessment_data=assessment_data,
            ),
            meal_plan=self._get_meal_plan(),
        )
        prescriptions.append(diet_prescription)

        # Generate exercise prescription
        exercise_prescription = ExercisePrescription(
            prescription_id=str(uuid4()),
            patient_id=patient_id,
            created_at=now,
            exercise_type=self._get_exercise_type(
                patient_profile=patient_profile,
                assessment_data=assessment_data,
            ),
            frequency_weekly=self._get_exercise_frequency(
                assessment_data=assessment_data,
            ),
            duration_minutes=self._get_exercise_duration(
                assessment_data=assessment_data,
            ),
            intensity_level="moderate",
            precautions=self._get_exercise_precautions(
                assessment_data=assessment_data,
            ),
        )
        prescriptions.append(exercise_prescription)

        # Generate sleep prescription
        sleep_prescription = SleepPrescription(
            prescription_id=str(uuid4()),
            patient_id=patient_id,
            created_at=now,
            target_sleep_hours=self._get_target_sleep_hours(
                patient_profile=patient_profile,
            ),
            bedtime_recommendation="22:00-23:00",
            wake_time_recommendation="6:00-7:00",
            sleep_hygiene_tips=self._get_sleep_hygiene_tips(),
        )
        prescriptions.append(sleep_prescription)

        # Generate psychological prescription
        psychological_prescription = PsychologicalPrescription(
            prescription_id=str(uuid4()),
            patient_id=patient_id,
            created_at=now,
            stress_management_techniques=self._get_stress_management_techniques(),
            relaxation_exercises=self._get_relaxation_exercises(),
            recommended_activities=["阅读", "音乐", "散步", "社交活动"],
        )
        prescriptions.append(psychological_prescription)

        return prescriptions

    def _get_dietary_recommendations(
        self,
        assessment_data: dict[str, Any] | None,
    ) -> list[str]:
        """Get dietary recommendations."""
        recommendations = [
            "保持均衡饮食，每日摄入蔬菜水果",
            "控制盐分摄入，每日不超过6克",
            "减少高油高糖食物",
        ]

        if assessment_data:
            assessments = assessment_data.get("assessments", {})

            if "blood_pressure" in assessments:
                if not assessments["blood_pressure"].get("is_normal", True):
                    recommendations.extend([
                        "采用DASH饮食法（低钠高钾）",
                        "增加富含钾的食物：香蕉、橙子、菠菜等",
                    ])

            if "blood_glucose" in assessments:
                if not assessments["blood_glucose"].get("is_normal", True):
                    recommendations.extend([
                        "控制碳水化合物摄入",
                        "选择低升糖指数食物",
                        "规律进食，避免暴饮暴食",
                    ])

            if "bmi" in assessments:
                if not assessments["bmi"].get("is_normal", True):
                    recommendations.append("控制总热量摄入，适量减少")

        return recommendations

    def _get_dietary_restrictions(
        self,
        patient_profile: dict[str, Any],
        assessment_data: dict[str, Any] | None,
    ) -> list[str]:
        """Get dietary restrictions."""
        restrictions = []

        # Check for allergies from profile
        allergies = patient_profile.get("allergies", [])
        if allergies:
            restrictions.extend([f"避免{allergy}" for allergy in allergies])

        if assessment_data:
            assessments = assessment_data.get("assessments", {})

            if "blood_pressure" in assessments:
                if not assessments["blood_pressure"].get("is_normal", True):
                    restrictions.append("限制高盐食物")
                    restrictions.append("避免腌制食品")

            if "uric_acid" in assessments:
                if not assessments["uric_acid"].get("is_normal", True):
                    restrictions.extend([
                        "限制高嘌呤食物",
                        "避免动物内脏",
                        "限制海鲜摄入",
                        "禁止饮酒",
                    ])

        return restrictions

    def _get_meal_plan(self) -> dict[str, Any]:
        """Get meal plan structure."""
        return {
            "breakfast": "全谷物食品 + 蛋白质 + 水果",
            "lunch": "主食 + 蔬菜 + 瘦肉蛋白",
            "dinner": "少量主食 + 蔬菜 + 豆制品",
            "snacks": "坚果、酸奶、水果（适量）",
        }

    def _get_exercise_type(
        self,
        patient_profile: dict[str, Any],
        assessment_data: dict[str, Any] | None,
    ) -> str:
        """Get recommended exercise type."""
        age = patient_profile.get("age", 40)

        if assessment_data:
            bmi_assessment = assessment_data.get("assessments", {}).get("bmi", {})
            if not bmi_assessment.get("is_normal", True):
                return "有氧运动为主，配合力量训练"

        if age > 60:
            return "低强度有氧运动（散步、太极）"
        elif age > 40:
            return "中等强度有氧运动（快走、游泳）"
        else:
            return "多样化运动（跑步、骑行、球类运动）"

    def _get_exercise_frequency(
        self,
        assessment_data: dict[str, Any] | None,
    ) -> int:
        """Get weekly exercise frequency."""
        return 5  # 5 times per week as default

    def _get_exercise_duration(
        self,
        assessment_data: dict[str, Any] | None,
    ) -> int:
        """Get exercise duration in minutes."""
        return 30  # 30 minutes as default

    def _get_exercise_precautions(
        self,
        assessment_data: dict[str, Any] | None,
    ) -> list[str]:
        """Get exercise precautions."""
        precautions = ["运动前热身，运动后拉伸"]

        if assessment_data:
            bp_assessment = assessment_data.get("assessments", {}).get("blood_pressure", {})
            if not bp_assessment.get("is_normal", True):
                precautions.extend([
                    "避免剧烈运动",
                    "运动时监测心率",
                    "如有不适应立即停止",
                ])

        return precautions

    def _get_target_sleep_hours(
        self,
        patient_profile: dict[str, Any],
    ) -> int:
        """Get target sleep hours."""
        age = patient_profile.get("age", 40)
        if age > 65:
            return 7
        return 8

    def _get_sleep_hygiene_tips(self) -> list[str]:
        """Get sleep hygiene tips."""
        return [
            "保持规律作息时间",
            "睡前避免使用电子设备",
            "保持卧室安静、黑暗、凉爽",
            "睡前避免咖啡、茶、酒精",
            "建立放松的睡前仪式",
        ]

    def _get_stress_management_techniques(self) -> list[str]:
        """Get stress management techniques."""
        return [
            "深呼吸练习",
            "正念冥想",
            "时间管理",
            "社交支持",
            "爱好培养",
        ]

    def _get_relaxation_exercises(self) -> list[str]:
        """Get relaxation exercises."""
        return [
            "渐进式肌肉放松",
            "瑜伽",
            "太极",
            "散步",
            "听音乐",
        ]

    async def get_health_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any] | None:
        """
        Get health plan by ID.

        Args:
            plan_id: Health plan identifier

        Returns:
            Health plan data or None
        """
        health_plan = await self._health_plan_repository.find_by_id(
            HealthPlanId(value=plan_id)
        )
        return health_plan.generate_summary() if health_plan else None

    async def get_patient_health_plans(
        self,
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get all health plans for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            List of health plan summaries
        """
        health_plans = await self._health_plan_repository.find_by_patient_id(patient_id)
        return [hp.generate_summary() for hp in health_plans]

    async def update_plan_goals(
        self,
        plan_id: str,
        new_goals: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Update health plan goals.

        Args:
            plan_id: Health plan identifier
            new_goals: List of new goal data

        Returns:
            Updated health plan summary
        """
        health_plan = await self._health_plan_repository.find_by_id(
            HealthPlanId(value=plan_id)
        )

        if not health_plan:
            return None

        # Convert goal dicts to TargetGoal objects
        goals = [
            TargetGoal(
                goal_id=g.get("goal_id", str(uuid4())),
                category=g["category"],
                title=g["title"],
                description=g.get("description", ""),
                target_value=g.get("target_value", ""),
                current_status=g.get("current_status", "pending"),
                priority=g.get("priority", "medium"),
                deadline_days=g.get("deadline_days", 90),
            )
            for g in new_goals
        ]

        target_goals = TargetGoals(goals=goals)
        health_plan.update_target_goals(target_goals)

        await self._health_plan_repository.save(health_plan)

        return health_plan.generate_summary()

    async def add_prescription_to_plan(
        self,
        plan_id: str,
        prescription_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Add a prescription to an existing health plan.

        Args:
            plan_id: Health plan identifier
            prescription_data: Prescription data

        Returns:
            Updated health plan summary
        """
        health_plan = await self._health_plan_repository.find_by_id(
            HealthPlanId(value=plan_id)
        )

        if not health_plan:
            return None

        # Create prescription based on type
        prescription = self._create_prescription_from_data(
            patient_id=health_plan.patient_id,
            prescription_data=prescription_data,
        )

        health_plan.add_prescription(prescription)
        await self._health_plan_repository.save(health_plan)

        return health_plan.generate_summary()

    def _create_prescription_from_data(
        self,
        patient_id: str,
        prescription_data: dict[str, Any],
    ):
        """Create prescription object from data."""
        prescription_type = prescription_data.get("type")
        now = datetime.now()

        if prescription_type == "diet":
            return DietPrescription(
                prescription_id=str(uuid4()),
                patient_id=patient_id,
                created_at=now,
                dietary_recommendations=prescription_data.get(
                    "dietary_recommendations", []
                ),
                restrictions=prescription_data.get("restrictions", []),
                meal_plan=prescription_data.get("meal_plan", {}),
            )
        elif prescription_type == "exercise":
            return ExercisePrescription(
                prescription_id=str(uuid4()),
                patient_id=patient_id,
                created_at=now,
                exercise_type=prescription_data.get("exercise_type", "有氧运动"),
                frequency_weekly=prescription_data.get("frequency_weekly", 3),
                duration_minutes=prescription_data.get("duration_minutes", 30),
                intensity_level=prescription_data.get("intensity_level", "moderate"),
                precautions=prescription_data.get("precautions", []),
            )
        elif prescription_type == "sleep":
            return SleepPrescription(
                prescription_id=str(uuid4()),
                patient_id=patient_id,
                created_at=now,
                target_sleep_hours=prescription_data.get("target_sleep_hours", 8),
                bedtime_recommendation=prescription_data.get(
                    "bedtime_recommendation", "22:00-23:00"
                ),
                wake_time_recommendation=prescription_data.get(
                    "wake_time_recommendation", "6:00-7:00"
                ),
                sleep_hygiene_tips=prescription_data.get("sleep_hygiene_tips", []),
            )
        elif prescription_type == "psychological":
            return PsychologicalPrescription(
                prescription_id=str(uuid4()),
                patient_id=patient_id,
                created_at=now,
                stress_management_techniques=prescription_data.get(
                    "stress_management_techniques", []
                ),
                relaxation_exercises=prescription_data.get("relaxation_exercises", []),
                recommended_activities=prescription_data.get("recommended_activities", []),
            )
        elif prescription_type == "medication":
            return MedicationPrescription(
                prescription_id=str(uuid4()),
                patient_id=patient_id,
                created_at=now,
                medication_name=prescription_data.get("medication_name", ""),
                dosage=prescription_data.get("dosage", ""),
                frequency=prescription_data.get("frequency", ""),
                duration_days=prescription_data.get("duration_days", 30),
                instructions=prescription_data.get("instructions", ""),
            )
        else:
            raise ValueError(f"Unknown prescription type: {prescription_type}")
