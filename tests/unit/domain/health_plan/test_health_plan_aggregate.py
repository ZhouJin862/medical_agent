"""
Unit tests for HealthPlan aggregate root.

This test module covers:
- Generating a health plan (mark_as_generated)
- Adding prescriptions (add_prescription)
- Updating plan target_goals (update_target_goals)
- Domain event publishing (HealthPlanGenerated)
- Prescription management (remove, get_by_type)
- Summary generation
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
try:
    from freezegun import freeze_time
except ImportError:
    # If freezegun is not installed, create a simple mock
    from contextlib import contextmanager
    @contextmanager
    def freeze_time(time_str):
        yield

from src.domain.health_plan.entities.health_plan import (
    HealthPlan,
    PlanType,
)
from src.domain.health_plan.entities.prescriptions.diet_prescription import (
    DietPrescription,
)
from src.domain.health_plan.entities.prescriptions.exercise_prescription import (
    ExercisePrescription,
    ExerciseType,
    IntensityLevel,
)
from src.domain.health_plan.entities.prescriptions.medication_prescription import (
    MedicationPrescription,
)
from src.domain.health_plan.entities.prescriptions.psychological_prescription import (
    PsychologicalPrescription,
)
from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
    SleepPrescription,
)
from src.domain.health_plan.entities.prescriptions.prescription import (
    PrescriptionType,
)
from src.domain.health_plan.events.health_plan_generated import (
    HealthPlanGenerated,
)
from src.domain.health_plan.value_objects.health_plan_id import HealthPlanId
from src.domain.health_plan.value_objects.target_goals import (
    GoalStatus,
    TargetGoal,
    TargetGoals,
)


@pytest.fixture
def health_plan_id():
    """Fixture for HealthPlanId."""
    return HealthPlanId(value="hp-test-001")


@pytest.fixture
def sample_health_plan(health_plan_id):
    """Fixture for a sample HealthPlan instance."""
    return HealthPlan(
        plan_id=health_plan_id,
        patient_id="patient-123",
        plan_type=PlanType.WELLNESS,
    )


@pytest.fixture
def sample_diet_prescription():
    """Fixture for a valid DietPrescription."""
    return DietPrescription(
        prescription_id="diet-001",
        prescription_type=PrescriptionType.DIET,
        created_at=datetime.now(),
        daily_calories=2000,
        meals={"breakfast": "oatmeal", "lunch": "salad"},
        restrictions=["nuts"],
        recommendations=["eat more vegetables"],
    )


@pytest.fixture
def sample_exercise_prescription():
    """Fixture for a valid ExercisePrescription."""
    return ExercisePrescription(
        prescription_id="exercise-001",
        prescription_type=PrescriptionType.EXERCISE,
        created_at=datetime.now(),
        exercise_type=ExerciseType.CARDIO,
        frequency="3 times per week",
        duration="30 minutes",
        intensity=IntensityLevel.MODERATE,
        precautions=["knee injury"],
    )


@pytest.fixture
def sample_medication_prescription():
    """Fixture for a valid MedicationPrescription."""
    return MedicationPrescription(
        prescription_id="med-001",
        prescription_type=PrescriptionType.MEDICATION,
        created_at=datetime.now(),
        drug_name="Aspirin",
        dosage="100mg",
        frequency="once daily",
        duration="30 days",
    )


@pytest.fixture
def sample_psychological_prescription():
    """Fixture for a valid PsychologicalPrescription."""
    return PsychologicalPrescription(
        prescription_id="psych-001",
        prescription_type=PrescriptionType.PSYCHOLOGICAL,
        created_at=datetime.now(),
        interventions=["CBT", "mindfulness"],
        goals=["reduce anxiety", "improve sleep"],
    )


@pytest.fixture
def sample_sleep_prescription():
    """Fixture for a valid SleepPrescription."""
    from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
        SleepQualityRating,
    )
    return SleepPrescription(
        prescription_id="sleep-001",
        prescription_type=PrescriptionType.SLEEP,
        created_at=datetime.now(),
        sleep_duration="7-8 hours",
        sleep_quality=SleepQualityRating.GOOD,
    )


@pytest.fixture
def sample_target_goals():
    """Fixture for sample TargetGoals."""
    return TargetGoals(
        goals=(
            TargetGoal(
                description="Lose 5kg",
                target_value="70kg",
                category="weight",
                status=GoalStatus.PENDING,
            ),
            TargetGoal(
                description="Exercise 3x per week",
                category="exercise",
                status=GoalStatus.IN_PROGRESS,
            ),
            TargetGoal(
                description="Drink 2L water daily",
                category="hydration",
                status=GoalStatus.ACHIEVED,
            ),
        )
    )


class TestHealthPlanAggregateCreation:
    """Tests for HealthPlan aggregate root creation and initialization."""

    def test_create_health_plan_with_minimal_args(self, health_plan_id):
        """Test creating a HealthPlan with minimal required arguments."""
        plan = HealthPlan(
            plan_id=health_plan_id,
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS,
        )

        assert plan.plan_id == health_plan_id
        assert plan.patient_id == "patient-123"
        assert plan.plan_type == PlanType.WELLNESS
        assert len(plan.prescriptions) == 0
        assert isinstance(plan.target_goals, TargetGoals)
        assert len(plan.target_goals) == 0
        assert isinstance(plan.created_at, datetime)
        assert isinstance(plan.updated_at, datetime)

    def test_create_health_plan_with_all_plan_types(self, health_plan_id):
        """Test creating a HealthPlan with different plan types."""
        plan_types = [
            PlanType.PREVENTIVE,
            PlanType.TREATMENT,
            PlanType.RECOVERY,
            PlanType.CHRONIC_MANAGEMENT,
            PlanType.WELLNESS,
        ]

        for plan_type in plan_types:
            plan = HealthPlan(
                plan_id=health_plan_id,
                patient_id="patient-123",
                plan_type=plan_type,
            )
            assert plan.plan_type == plan_type

    def test_create_health_plan_with_target_goals(self, health_plan_id, sample_target_goals):
        """Test creating a HealthPlan with target goals."""
        plan = HealthPlan(
            plan_id=health_plan_id,
            patient_id="patient-123",
            plan_type=PlanType.WELLNESS,
            target_goals=sample_target_goals,
        )

        assert len(plan.target_goals) == 3
        assert len(plan.target_goals.active_goals) == 2
        assert len(plan.target_goals.achieved_goals) == 1

    def test_health_plan_aggregate_has_domain_events_list(self, sample_health_plan):
        """Test that HealthPlan aggregate has domain events management."""
        assert hasattr(sample_health_plan, "domain_events")
        assert hasattr(sample_health_plan, "pull_domain_events")
        assert hasattr(sample_health_plan, "clear_domain_events")
        assert hasattr(sample_health_plan, "version")


class TestHealthPlanGeneratePlan:
    """Tests for generating a health plan and domain event publishing."""

    def test_mark_as_generated_raises_health_plan_generated_event(
        self, sample_health_plan
    ):
        """Test that mark_as_generated raises HealthPlanGenerated domain event."""
        # Ensure no events before marking
        events_before = sample_health_plan.pull_domain_events()
        assert len(events_before) == 0

        # Mark as generated
        sample_health_plan.mark_as_generated()

        # Check domain events
        events = sample_health_plan.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], HealthPlanGenerated)

    def test_mark_as_generated_event_contains_correct_data(
        self, sample_health_plan, health_plan_id
    ):
        """Test that HealthPlanGenerated event contains correct plan data."""
        sample_health_plan.mark_as_generated()

        events = sample_health_plan.domain_events
        assert len(events) == 1

        event = events[0]
        assert event.plan_id == health_plan_id.value
        assert event.patient_id == "patient-123"
        assert event.plan_type == PlanType.WELLNESS.value
        assert event.event_type == "HealthPlanGenerated"
        assert isinstance(event.occurred_at, datetime)

    def test_mark_as_generated_increments_version(self, sample_health_plan):
        """Test that mark_as_generated increments the aggregate version."""
        initial_version = sample_health_plan.version
        assert initial_version == 0

        sample_health_plan.mark_as_generated()
        assert sample_health_plan.version == 1

        # Call again and check version increment
        sample_health_plan.mark_as_generated()
        assert sample_health_plan.version == 2

    def test_mark_as_generated_updates_updated_at(self, sample_health_plan):
        """Test that mark_as_generated updates the updated_at timestamp."""
        with freeze_time("2026-03-30 10:00:00"):
            initial_updated_at = sample_health_plan.updated_at

        with freeze_time("2026-03-30 11:00:00"):
            sample_health_plan.mark_as_generated()
            assert sample_health_plan.updated_at > initial_updated_at

    @patch("src.domain.health_plan.entities.health_plan.datetime")
    def test_mark_as_generated_event_timestamp(self, mock_datetime, sample_health_plan):
        """Test that the event timestamp is set correctly."""
        test_time = datetime(2026, 3, 30, 12, 0, 0)
        mock_datetime.now.return_value = test_time

        sample_health_plan.mark_as_generated()

        events = sample_health_plan.domain_events
        assert events[0].occurred_at == test_time

    def test_mark_as_generated_multiple_times_raises_multiple_events(
        self, sample_health_plan
    ):
        """Test calling mark_as_generated multiple times raises multiple events."""
        sample_health_plan.mark_as_generated()
        sample_health_plan.mark_as_generated()

        events = sample_health_plan.domain_events
        assert len(events) == 2

    def test_pull_domain_events_clears_pending_events(self, sample_health_plan):
        """Test that pull_domain_events returns and clears pending events."""
        sample_health_plan.mark_as_generated()

        events_first_pull = sample_health_plan.pull_domain_events()
        assert len(events_first_pull) == 1

        events_second_pull = sample_health_plan.pull_domain_events()
        assert len(events_second_pull) == 0

    def test_domain_events_property_returns_copy(self, sample_health_plan):
        """Test that domain_events property returns a copy (read-only view)."""
        sample_health_plan.mark_as_generated()

        events = sample_health_plan.domain_events
        assert len(events) == 1

        # Modifying returned list should not affect internal state
        events.clear()

        # Internal events should still be present
        assert len(sample_health_plan.domain_events) == 1


class TestHealthPlanAddPrescription:
    """Tests for adding prescriptions to the health plan."""

    def test_add_diet_prescription(self, sample_health_plan, sample_diet_prescription):
        """Test adding a valid diet prescription."""
        sample_health_plan.add_prescription(sample_diet_prescription)

        assert len(sample_health_plan.prescriptions) == 1
        assert sample_health_plan.prescriptions[0] == sample_diet_prescription
        assert sample_health_plan.prescriptions[0].prescription_id == "diet-001"

    def test_add_exercise_prescription(
        self, sample_health_plan, sample_exercise_prescription
    ):
        """Test adding a valid exercise prescription."""
        sample_health_plan.add_prescription(sample_exercise_prescription)

        assert len(sample_health_plan.prescriptions) == 1
        assert sample_health_plan.prescriptions[0].prescription_type == PrescriptionType.EXERCISE

    def test_add_medication_prescription(
        self, sample_health_plan, sample_medication_prescription
    ):
        """Test adding a valid medication prescription."""
        sample_health_plan.add_prescription(sample_medication_prescription)

        assert len(sample_health_plan.prescriptions) == 1
        assert sample_health_plan.prescriptions[0].drug_name == "Aspirin"

    def test_add_psychological_prescription(
        self, sample_health_plan, sample_psychological_prescription
    ):
        """Test adding a valid psychological prescription."""
        sample_health_plan.add_prescription(sample_psychological_prescription)

        assert len(sample_health_plan.prescriptions) == 1
        assert "CBT" in sample_health_plan.prescriptions[0].interventions

    def test_add_sleep_prescription(
        self, sample_health_plan, sample_sleep_prescription
    ):
        """Test adding a valid sleep prescription."""
        sample_health_plan.add_prescription(sample_sleep_prescription)

        assert len(sample_health_plan.prescriptions) == 1
        assert sample_health_plan.prescriptions[0].sleep_duration == "7-8 hours"

    def test_add_multiple_prescriptions(
        self,
        sample_health_plan,
        sample_diet_prescription,
        sample_exercise_prescription,
        sample_medication_prescription,
    ):
        """Test adding multiple different prescription types."""
        sample_health_plan.add_prescription(sample_diet_prescription)
        sample_health_plan.add_prescription(sample_exercise_prescription)
        sample_health_plan.add_prescription(sample_medication_prescription)

        assert len(sample_health_plan.prescriptions) == 3

    def test_add_prescription_updates_updated_at(self, sample_health_plan, sample_diet_prescription):
        """Test that adding a prescription updates the updated_at timestamp."""
        with freeze_time("2026-03-30 10:00:00"):
            initial_updated_at = sample_health_plan.updated_at

        with freeze_time("2026-03-30 11:00:00"):
            sample_health_plan.add_prescription(sample_diet_prescription)
            assert sample_health_plan.updated_at > initial_updated_at

    def test_add_duplicate_prescription_id_raises_error(
        self, sample_health_plan, sample_diet_prescription
    ):
        """Test that adding a prescription with duplicate ID raises ValueError."""
        sample_health_plan.add_prescription(sample_diet_prescription)

        with pytest.raises(ValueError, match="already exists"):
            sample_health_plan.add_prescription(sample_diet_prescription)

    def test_add_invalid_prescription_raises_error(self, sample_health_plan):
        """Test that adding an invalid prescription raises ValueError."""
        # Create an invalid diet prescription (too low calories)
        invalid_prescription = DietPrescription(
            prescription_id="diet-invalid",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=100,  # Below minimum of 500
        )

        with pytest.raises(ValueError, match="Invalid prescription"):
            sample_health_plan.add_prescription(invalid_prescription)

    def test_add_prescription_invalid_exercise_type_raises_error(self, sample_health_plan):
        """Test that adding an invalid exercise prescription raises ValueError."""
        # Exercise prescription without exercise_type is invalid
        invalid_prescription = ExercisePrescription(
            prescription_id="exercise-invalid",
            prescription_type=PrescriptionType.EXERCISE,
            created_at=datetime.now(),
            exercise_type=None,  # Missing required field
        )

        with pytest.raises(ValueError, match="Invalid prescription"):
            sample_health_plan.add_prescription(invalid_prescription)


class TestHealthPlanPrescriptionManagement:
    """Tests for prescription management operations."""

    def test_remove_existing_prescription(self, sample_health_plan, sample_diet_prescription):
        """Test removing an existing prescription."""
        sample_health_plan.add_prescription(sample_diet_prescription)
        assert len(sample_health_plan.prescriptions) == 1

        result = sample_health_plan.remove_prescription("diet-001")

        assert result is True
        assert len(sample_health_plan.prescriptions) == 0

    def test_remove_nonexistent_prescription(self, sample_health_plan):
        """Test removing a prescription that doesn't exist."""
        result = sample_health_plan.remove_prescription("nonexistent-id")

        assert result is False
        assert len(sample_health_plan.prescriptions) == 0

    def test_remove_prescription_updates_updated_at(
        self, sample_health_plan, sample_diet_prescription
    ):
        """Test that removing a prescription updates the updated_at timestamp."""
        sample_health_plan.add_prescription(sample_diet_prescription)

        with freeze_time("2026-03-30 10:00:00"):
            initial_updated_at = sample_health_plan.updated_at

        with freeze_time("2026-03-30 11:00:00"):
            sample_health_plan.remove_prescription("diet-001")
            assert sample_health_plan.updated_at > initial_updated_at

    def test_remove_prescription_does_not_update_updated_at_when_not_found(
        self, sample_health_plan
    ):
        """Test that removing a non-existent prescription doesn't update timestamp."""
        with freeze_time("2026-03-30 10:00:00"):
            initial_updated_at = sample_health_plan.updated_at

        with freeze_time("2026-03-30 11:00:00"):
            sample_health_plan.remove_prescription("nonexistent-id")
            # Should not update since nothing was removed
            assert sample_health_plan.updated_at == initial_updated_at

    def test_get_prescriptions_by_type(
        self,
        sample_health_plan,
        sample_diet_prescription,
        sample_exercise_prescription,
        sample_medication_prescription,
    ):
        """Test filtering prescriptions by type."""
        sample_health_plan.add_prescription(sample_diet_prescription)
        sample_health_plan.add_prescription(sample_exercise_prescription)
        sample_health_plan.add_prescription(sample_medication_prescription)

        diet_prescriptions = sample_health_plan.get_prescriptions_by_type(
            PrescriptionType.DIET
        )
        exercise_prescriptions = sample_health_plan.get_prescriptions_by_type(
            PrescriptionType.EXERCISE
        )
        medication_prescriptions = sample_health_plan.get_prescriptions_by_type(
            PrescriptionType.MEDICATION
        )
        sleep_prescriptions = sample_health_plan.get_prescriptions_by_type(
            PrescriptionType.SLEEP
        )

        assert len(diet_prescriptions) == 1
        assert len(exercise_prescriptions) == 1
        assert len(medication_prescriptions) == 1
        assert len(sleep_prescriptions) == 0
        assert diet_prescriptions[0].prescription_id == "diet-001"

    def test_get_prescriptions_by_type_with_multiple_same_type(
        self, sample_health_plan
    ):
        """Test getting multiple prescriptions of the same type."""
        diet1 = DietPrescription(
            prescription_id="diet-001",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=2000,
        )
        diet2 = DietPrescription(
            prescription_id="diet-002",
            prescription_type=PrescriptionType.DIET,
            created_at=datetime.now(),
            daily_calories=1800,
        )

        sample_health_plan.add_prescription(diet1)
        sample_health_plan.add_prescription(diet2)

        diet_prescriptions = sample_health_plan.get_prescriptions_by_type(
            PrescriptionType.DIET
        )

        assert len(diet_prescriptions) == 2


class TestHealthPlanUpdateTargetGoals:
    """Tests for updating target goals."""

    def test_update_target_goals(self, sample_health_plan, sample_target_goals):
        """Test updating the target goals."""
        assert len(sample_health_plan.target_goals) == 0

        sample_health_plan.update_target_goals(sample_target_goals)

        assert len(sample_health_plan.target_goals) == 3
        assert sample_health_plan.target_goals == sample_target_goals

    def test_update_target_goals_updates_updated_at(
        self, sample_health_plan, sample_target_goals
    ):
        """Test that updating target goals updates the updated_at timestamp."""
        with freeze_time("2026-03-30 10:00:00"):
            initial_updated_at = sample_health_plan.updated_at

        with freeze_time("2026-03-30 11:00:00"):
            sample_health_plan.update_target_goals(sample_target_goals)
            assert sample_health_plan.updated_at > initial_updated_at


class TestHealthPlanGenerateSummary:
    """Tests for health plan summary generation."""

    def test_generate_summary_empty_plan(self, sample_health_plan):
        """Test generating summary for an empty health plan."""
        summary = sample_health_plan.generate_summary()

        assert summary["plan_id"] == "HealthPlanId(hp-test-001)"
        assert summary["patient_id"] == "patient-123"
        assert summary["plan_type"] == "wellness"
        assert summary["total_prescriptions"] == 0
        assert summary["prescriptions_by_type"] == {}
        assert summary["prescription_details"] == []
        assert summary["target_goals"]["total"] == 0
        assert summary["target_goals"]["active"] == 0
        assert summary["target_goals"]["achieved"] == 0

    def test_generate_summary_with_prescriptions(
        self,
        sample_health_plan,
        sample_diet_prescription,
        sample_exercise_prescription,
        sample_medication_prescription,
    ):
        """Test generating summary with multiple prescriptions."""
        sample_health_plan.add_prescription(sample_diet_prescription)
        sample_health_plan.add_prescription(sample_exercise_prescription)
        sample_health_plan.add_prescription(sample_medication_prescription)

        summary = sample_health_plan.generate_summary()

        assert summary["total_prescriptions"] == 3
        assert summary["prescriptions_by_type"]["diet"] == 1
        assert summary["prescriptions_by_type"]["exercise"] == 1
        assert summary["prescriptions_by_type"]["medication"] == 1
        assert len(summary["prescription_details"]) == 3

    def test_generate_summary_includes_prescription_details(
        self, sample_health_plan, sample_diet_prescription
    ):
        """Test that summary includes prescription details."""
        sample_health_plan.add_prescription(sample_diet_prescription)

        summary = sample_health_plan.generate_summary()

        assert len(summary["prescription_details"]) == 1
        detail = summary["prescription_details"][0]
        assert detail["id"] == "diet-001"
        assert detail["type"] == "diet"
        assert "created_at" in detail
        assert "details" in detail
        assert detail["details"]["daily_calories"] == 2000

    def test_generate_summary_with_target_goals(
        self, sample_health_plan, sample_target_goals
    ):
        """Test generating summary with target goals."""
        sample_health_plan.update_target_goals(sample_target_goals)

        summary = sample_health_plan.generate_summary()

        assert summary["target_goals"]["total"] == 3
        assert summary["target_goals"]["active"] == 2
        assert summary["target_goals"]["achieved"] == 1

    def test_generate_summary_with_all_plan_types(self, health_plan_id):
        """Test generating summary for different plan types."""
        plan_types = [
            PlanType.PREVENTIVE,
            PlanType.TREATMENT,
            PlanType.RECOVERY,
            PlanType.CHRONIC_MANAGEMENT,
            PlanType.WELLNESS,
        ]

        for plan_type in plan_types:
            plan = HealthPlan(
                plan_id=health_plan_id,
                patient_id="patient-123",
                plan_type=plan_type,
            )
            summary = plan.generate_summary()
            assert summary["plan_type"] == plan_type.value

    def test_generate_summary_includes_timestamps(self, sample_health_plan):
        """Test that summary includes created_at and updated_at timestamps."""
        summary = sample_health_plan.generate_summary()

        assert "created_at" in summary
        assert "updated_at" in summary
        # Verify ISO format
        datetime.fromisoformat(summary["created_at"])
        datetime.fromisoformat(summary["updated_at"])


class TestHealthPlanDomainEventIntegration:
    """Integration tests for domain events with other operations."""

    def test_add_prescription_does_not_raise_domain_event(
        self, sample_health_plan, sample_diet_prescription
    ):
        """Test that adding a prescription does not raise a domain event."""
        sample_health_plan.add_prescription(sample_diet_prescription)

        events = sample_health_plan.domain_events
        assert len(events) == 0

    def test_mark_as_generated_after_adding_prescriptions(
        self, sample_health_plan, sample_diet_prescription
    ):
        """Test domain event is raised after adding prescriptions."""
        sample_health_plan.add_prescription(sample_diet_prescription)
        sample_health_plan.mark_as_generated()

        events = sample_health_plan.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], HealthPlanGenerated)

    def test_clear_domain_events(self, sample_health_plan):
        """Test clearing domain events without publishing."""
        sample_health_plan.mark_as_generated()

        assert len(sample_health_plan.domain_events) == 1

        sample_health_plan.clear_domain_events()

        assert len(sample_health_plan.domain_events) == 0

    def test_version_increments_with_domain_events(self, sample_health_plan):
        """Test that version increments with each domain event."""
        assert sample_health_plan.version == 0

        sample_health_plan.mark_as_generated()
        assert sample_health_plan.version == 1

        sample_health_plan.mark_as_generated()
        assert sample_health_plan.version == 2

        sample_health_plan.clear_domain_events()
        # Version should remain after clearing
        assert sample_health_plan.version == 2


class TestHealthPlanEdgeCases:
    """Edge case tests for HealthPlan aggregate."""

    def test_health_plan_with_all_prescription_types(self, sample_health_plan):
        """Test health plan with all prescription types."""
        from src.domain.health_plan.entities.prescriptions.sleep_prescription import (
            SleepQualityRating,
        )

        prescriptions = [
            DietPrescription(
                prescription_id="diet-001",
                prescription_type=PrescriptionType.DIET,
                created_at=datetime.now(),
                daily_calories=2000,
            ),
            ExercisePrescription(
                prescription_id="exercise-001",
                prescription_type=PrescriptionType.EXERCISE,
                created_at=datetime.now(),
                exercise_type=ExerciseType.STRENGTH,
            ),
            SleepPrescription(
                prescription_id="sleep-001",
                prescription_type=PrescriptionType.SLEEP,
                created_at=datetime.now(),
                sleep_duration="8 hours",
                sleep_quality=SleepQualityRating.GOOD,
            ),
            MedicationPrescription(
                prescription_id="med-001",
                prescription_type=PrescriptionType.MEDICATION,
                created_at=datetime.now(),
                drug_name="Vitamin D",
                dosage="1000 IU",
                frequency="daily",
            ),
            PsychologicalPrescription(
                prescription_id="psych-001",
                prescription_type=PrescriptionType.PSYCHOLOGICAL,
                created_at=datetime.now(),
                interventions=["meditation"],
            ),
        ]

        for prescription in prescriptions:
            sample_health_plan.add_prescription(prescription)

        summary = sample_health_plan.generate_summary()
        assert summary["total_prescriptions"] == 5
        assert len(summary["prescriptions_by_type"]) == 5

    def test_multiple_operations_sequence(self, sample_health_plan, sample_diet_prescription):
        """Test a sequence of multiple operations."""
        # Add prescription
        sample_health_plan.add_prescription(sample_diet_prescription)
        assert len(sample_health_plan.prescriptions) == 1

        # Add target goals
        goal = TargetGoal(description="Walk daily")
        sample_health_plan.update_target_goals(
            sample_health_plan.target_goals.add_goal(goal)
        )
        assert len(sample_health_plan.target_goals) == 1

        # Mark as generated
        sample_health_plan.mark_as_generated()
        assert len(sample_health_plan.domain_events) == 1

        # Generate summary
        summary = sample_health_plan.generate_summary()
        assert summary["total_prescriptions"] == 1
        assert summary["target_goals"]["total"] == 1

        # Remove prescription
        sample_health_plan.remove_prescription("diet-001")
        assert len(sample_health_plan.prescriptions) == 0
