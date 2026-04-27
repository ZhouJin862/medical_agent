"""Unit tests for HealthPlan aggregate."""
import pytest
from datetime import datetime, timedelta

from src.domain.health_plan.entities.health_plan import (
    HealthPlan,
    PlanType,
)
from src.domain.health_plan.entities.prescriptions.diet_prescription import (
    DietPrescription,
)
from src.domain.health_plan.entities.prescriptions.exercise_prescription import (
    ExercisePrescription,
)
from src.domain.health_plan.entities.prescriptions.medication_prescription import (
    MedicationPrescription,
)
from src.domain.health_plan.entities.prescriptions.prescription import (
    PrescriptionType,
)
from src.domain.health_plan.entities.prescriptions.psychological_prescription import (
    PsychologicalPrescription,
)
from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
    SleepPrescription,
)
from src.domain.health_plan.value_objects.health_plan_id import HealthPlanId
from src.domain.health_plan.value_objects.target_goals import (
    GoalStatus,
    TargetGoal,
    TargetGoals,
)


class TestHealthPlanId:
    """Tests for HealthPlanId value object."""

    def test_create_valid_health_plan_id(self):
        plan_id = HealthPlanId(value="plan-123")
        assert plan_id.value == "plan-123"

    def test_health_plan_id_empty_string_raises_error(self):
        with pytest.raises(ValueError, match="non-empty string"):
            HealthPlanId(value="")

    def test_health_plan_id_none_raises_error(self):
        with pytest.raises(ValueError, match="non-empty string"):
            HealthPlanId(value=None)


class TestTargetGoals:
    """Tests for TargetGoals value object."""

    def test_create_empty_target_goals(self):
        goals = TargetGoals()
        assert len(goals) == 0
        assert list(goals) == []

    def test_create_target_goals_with_goals(self):
        goal1 = TargetGoal(
            description="Lose 5kg",
            target_value="70kg",
            category="weight"
        )
        goal2 = TargetGoal(
            description="Exercise 3x per week",
            category="exercise"
        )
        goals = TargetGoals(goals=(goal1, goal2))

        assert len(goals) == 2
        assert len(goals.active_goals) == 2
        assert len(goals.achieved_goals) == 0

    def test_add_goal_to_target_goals(self):
        goal = TargetGoal(description="Drink 2L water daily")
        goals = TargetGoals()
        updated_goals = goals.add_goal(goal)

        assert len(updated_goals) == 1

    def test_achieved_goals_filter(self):
        pending_goal = TargetGoal(
            description="Pending goal",
            status=GoalStatus.PENDING
        )
        achieved_goal = TargetGoal(
            description="Achieved goal",
            status=GoalStatus.ACHIEVED
        )
        in_progress_goal = TargetGoal(
            description="In progress goal",
            status=GoalStatus.IN_PROGRESS
        )

        goals = TargetGoals(goals=(pending_goal, achieved_goal, in_progress_goal))

        assert len(goals.achieved_goals) == 1
        assert len(goals.active_goals) == 2


class TestHealthPlanAggregate:
    """Tests for HealthPlan aggregate root."""

    def test_create_health_plan(self):
        plan_id = HealthPlanId(value="plan-001")
        plan = HealthPlan(
            plan_id=plan_id,
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        assert plan.plan_id == plan_id
        assert plan.patient_id == "patient-123"
        assert plan.plan_type == PlanType.WELLNESS
        assert len(plan.prescriptions) == 0

    def test_add_diet_prescription(self):
        plan = HealthPlan(
            plan_id=HealthPlanId(value="plan-001"),
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        diet_prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=2000,
            meals={"breakfast": "oatmeal"},
            restrictions=["nuts"],
            recommendations=["eat more vegetables"]
        )

        plan.add_prescription(diet_prescription)

        assert len(plan.prescriptions) == 1
        assert plan.prescriptions[0].prescription_id == "diet-001"

    def test_add_duplicate_prescription_raises_error(self):
        plan = HealthPlan(
            plan_id=HealthPlanId(value="plan-001"),
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now()
        )

        plan.add_prescription(prescription)

        with pytest.raises(ValueError, match="already exists"):
            plan.add_prescription(prescription)

    def test_get_prescriptions_by_type(self):
        plan = HealthPlan(
            plan_id=HealthPlanId(value="plan-001"),
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        diet_prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now()
        )

        exercise_prescription = ExercisePrescription(
            prescription_id="exercise-001",
            prescription_type=PrescriptionType.EXERCISE,
            created_at=datetime.now()
        )

        plan.add_prescription(diet_prescription)
        plan.add_prescription(exercise_prescription)

        diet_prescriptions = plan.get_prescriptions_by_type(PrescriptionType.DIET)
        exercise_prescriptions = plan.get_prescriptions_by_type(
            PrescriptionType.EXERCISE
        )

        assert len(diet_prescriptions) == 1
        assert len(exercise_prescriptions) == 1

    def test_remove_prescription(self):
        plan = HealthPlan(
            plan_id=HealthPlanId(value="plan-001"),
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now()
        )

        plan.add_prescription(prescription)
        assert len(plan.prescriptions) == 1

        result = plan.remove_prescription("diet-001")
        assert result is True
        assert len(plan.prescriptions) == 0

    def test_generate_summary(self):
        plan_id = HealthPlanId(value="plan-001")
        plan = HealthPlan(
            plan_id=plan_id,
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        diet_prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=2000
        )

        exercise_prescription = ExercisePrescription(
            prescription_id="exercise-001",
            prescription_type=PrescriptionType.EXERCISE,
            created_at=datetime.now()
        )

        plan.add_prescription(diet_prescription)
        plan.add_prescription(exercise_prescription)

        goal = TargetGoal(description="Walk 10000 steps daily")
        plan.target_goals = plan.target_goals.add_goal(goal)

        summary = plan.generate_summary()

        assert summary["plan_id"] == str(plan_id)
        assert summary["patient_id"] == "patient-123"
        assert summary["plan_type"] == "wellness"
        assert summary["total_prescriptions"] == 2
        assert summary["prescriptions_by_type"]["diet"] == 1
        assert summary["prescriptions_by_type"]["exercise"] == 1
        assert summary["target_goals"]["total"] == 1
        assert summary["target_goals"]["active"] == 1

    def test_mark_as_generated_raises_event(self):
        plan = HealthPlan(
            plan_id=HealthPlanId(value="plan-001"),
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS
        )

        plan.mark_as_generated()

        events = plan._get_domain_events()
        assert len(events) == 1
        assert events[0].plan_id == "plan-001"
        assert events[0].patient_id == "patient-123"
        assert events[0].plan_type == "wellness"


class TestDietPrescription:
    """Tests for DietPrescription entity."""

    def test_create_diet_prescription(self):
        prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=2000,
            restrictions=["nuts"],
            recommendations=["eat more fiber"]
        )

        assert prescription.prescription_type == PrescriptionType.DIET
        assert prescription.daily_calories == 2000
        assert prescription.restrictions == ["nuts"]

    def test_diet_prescription_get_details(self):
        prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=1800,
            meals={"lunch": "salad"},
        )

        details = prescription.get_details()

        assert details["daily_calories"] == 1800
        assert details["meals"] == {"lunch": "salad"}

    def test_diet_prescription_add_restriction(self):
        prescription = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now()
        )

        prescription.add_restriction("gluten")
        assert "gluten" in prescription.restrictions

    def test_diet_prescription_negative_calories_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            DietPrescription(
                prescription_id="diet-001",
                prescription_type=PrescriptionType.DIET,
                created_at=datetime.now(),
                daily_calories=-100
            )


class TestExercisePrescription:
    """Tests for ExercisePrescription entity."""

    def test_create_exercise_prescription(self):
        from src.domain.health_plan.entities.prescriptions.exercise_prescription import (
            ExerciseType,
            IntensityLevel,
        )

        prescription = ExercisePrescription(
            prescription_id="exercise-001",
            prescription_type=PrescriptionType.EXERCISE,
            created_at=datetime.now(),
            exercise_type=ExerciseType.CARDIO,
            frequency="3 times per week",
            duration="30 minutes",
            intensity=IntensityLevel.MODERATE,
        )

        assert prescription.prescription_type == PrescriptionType.EXERCISE
        assert prescription.exercise_type == ExerciseType.CARDIO
        assert prescription.frequency == "3 times per week"


class TestSleepPrescription:
    """Tests for SleepPrescription entity."""

    def test_create_sleep_prescription(self):
        from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
            SleepQualityRating,
        )

        prescription = SleepPrescription(
            prescription_id="sleep-001",
            prescription_type=PrescriptionType.SLEEP,
            created_at=datetime.now(),
            sleep_duration="7-8 hours",
            sleep_quality=SleepQualityRating.GOOD,
        )

        assert prescription.prescription_type == PrescriptionType.SLEEP
        assert prescription.sleep_duration == "7-8 hours"


class TestMedicationPrescription:
    """Tests for MedicationPrescription entity."""

    def test_create_medication_prescription(self):
        prescription = MedicationPrescription(
            prescription_id="med-001",
            prescription_type=PrescriptionType.MEDICATION,
            created_at=datetime.now(),
            drug_name="Aspirin",
            dosage="100mg",
            frequency="once daily",
            duration="30 days",
        )

        assert prescription.prescription_type == PrescriptionType.MEDICATION
        assert prescription.drug_name == "Aspirin"
        assert prescription.dosage == "100mg"

    def test_medication_prescription_empty_drug_name_raises_error(self):
        with pytest.raises(ValueError, match="drug_name cannot be empty"):
            MedicationPrescription(
                prescription_id="med-001",
                prescription_type=PrescriptionType.MEDICATION,
                created_at=datetime.now(),
                drug_name="",
                dosage="100mg",
                frequency="daily",
            )


class TestPsychologicalPrescription:
    """Tests for PsychologicalPrescription entity."""

    def test_create_psychological_prescription(self):
        prescription = PsychologicalPrescription(
            prescription_id="psych-001",
            prescription_type=PrescriptionType.PSYCHOLOGICAL,
            created_at=datetime.now(),
            interventions=["CBT", "mindfulness"],
            goals=["reduce anxiety", "improve sleep"],
        )

        assert prescription.prescription_type == PrescriptionType.PSYCHOLOGICAL
        assert "CBT" in prescription.interventions

    def test_psychological_prescription_add_intervention(self):
        prescription = PsychologicalPrescription(
            prescription_id="psych-001",
            prescription_type=PrescriptionType.PSYCHOLOGICAL,
            created_at=datetime.now()
        )

        prescription.add_intervention("exposure therapy")
        assert "exposure therapy" in prescription.interventions
