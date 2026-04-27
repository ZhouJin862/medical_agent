"""Unit tests for ContextSnapshot value object."""

import pytest
from datetime import datetime, timedelta

from src.domain.shared.value_objects.context_snapshot import ContextSnapshot
from src.domain.shared.value_objects.patient_data import PatientData
from src.domain.shared.enums.gender import GenderEnum


class TestContextSnapshot:
    """Tests for ContextSnapshot value object."""

    def test_create_context_snapshot(self):
        """Test creating a context snapshot."""
        patient = PatientData(patient_id="P123", name="张三")
        snapshot = ContextSnapshot(patient_data=patient)
        assert snapshot.patient_data.patient_id == "P123"
        assert snapshot.vital_signs == {}
        assert snapshot.medical_history == []

    def test_create_with_all_fields(self):
        """Test creating snapshot with all fields."""
        patient = PatientData(patient_id="P123", name="张三")
        vital_signs = {"blood_pressure": "120/80"}
        medical_history = [{"condition": "hypertension", "year": 2020}]
        medications = [{"drug": "amlodipine", "dose": "5mg"}]
        allergies = ["penicillin"]

        snapshot = ContextSnapshot(
            patient_data=patient,
            vital_signs=vital_signs,
            medical_history=medical_history,
            current_medications=medications,
            allergies=allergies,
            ttl_seconds=1800,
        )
        assert snapshot.vital_signs == vital_signs
        assert snapshot.medical_history == medical_history
        assert snapshot.current_medications == medications
        assert snapshot.allergies == allergies
        assert snapshot.ttl_seconds == 1800

    def test_is_expired_false(self):
        """Test is_expired returns False for fresh snapshot."""
        patient = PatientData(patient_id="P123", name="张三")
        snapshot = ContextSnapshot(patient_data=patient, ttl_seconds=3600)
        assert not snapshot.is_expired()

    def test_is_expired_true(self):
        """Test is_expired returns True for old snapshot."""
        patient = PatientData(patient_id="P123", name="张三")
        old_time = datetime.now() - timedelta(seconds=3700)
        snapshot = ContextSnapshot(
            patient_data=patient,
            cached_at=old_time,
            ttl_seconds=3600,
        )
        assert snapshot.is_expired()

    def test_get_age_seconds(self):
        """Test getting snapshot age."""
        patient = PatientData(patient_id="P123", name="张三")
        old_time = datetime.now() - timedelta(seconds=100)
        snapshot = ContextSnapshot(patient_data=patient, cached_at=old_time)
        age = snapshot.get_age_seconds()
        assert 100 <= age < 105  # Allow small time difference

    def test_to_dict(self):
        """Test conversion to dictionary."""
        patient = PatientData(patient_id="P123", name="张三", age=44)
        snapshot = ContextSnapshot(
            patient_data=patient,
            vital_signs={"bp": "120/80"},
            allergies=["penicillin"],
        )
        result = snapshot.to_dict()
        assert result["patient_data"]["patient_id"] == "P123"
        assert result["vital_signs"]["bp"] == "120/80"
        assert result["allergies"] == ["penicillin"]
        assert "is_expired" in result
        assert "age_seconds" in result

    def test_from_dict(self):
        """Test creation from dictionary."""
        patient = PatientData(patient_id="P123", name="张三", age=44)
        data = {
            "patient_data": patient.to_dict(),
            "vital_signs": {"bp": "120/80"},
            "medical_history": [],
            "current_medications": [],
            "allergies": ["penicillin"],
            "cached_at": datetime.now().isoformat(),
            "ttl_seconds": 3600,
        }
        snapshot = ContextSnapshot.from_dict(data)
        assert snapshot.patient_data.patient_id == "P123"
        assert snapshot.vital_signs["bp"] == "120/80"
        assert snapshot.allergies == ["penicillin"]

    def test_create_factory_method(self):
        """Test create factory method."""
        patient = PatientData(patient_id="P123", name="张三")
        vital_signs = {"bp": "120/80"}
        allergies = ["penicillin"]

        snapshot = ContextSnapshot.create(
            patient_data=patient,
            vital_signs=vital_signs,
            allergies=allergies,
            ttl_seconds=1800,
        )
        assert snapshot.patient_data.patient_id == "P123"
        assert snapshot.vital_signs == vital_signs
        assert snapshot.allergies == allergies
        assert snapshot.ttl_seconds == 1800
        assert not snapshot.is_expired()
