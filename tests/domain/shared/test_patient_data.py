"""Unit tests for PatientData value object."""

import pytest
from datetime import date, datetime

from src.domain.shared.value_objects.patient_data import PatientData
from src.domain.shared.enums.gender import GenderEnum


class TestPatientData:
    """Tests for PatientData value object."""

    def test_create_valid_patient_data(self):
        """Test creating valid patient data."""
        patient = PatientData(
            patient_id="P123",
            name="张三",
        )
        assert patient.patient_id == "P123"
        assert patient.name == "张三"

    def test_missing_patient_id_raises_exception(self):
        """Test that missing patient ID raises exception."""
        with pytest.raises(ValueError):
            PatientData(patient_id="", name="张三")

    def test_missing_name_raises_exception(self):
        """Test that missing name raises exception."""
        with pytest.raises(ValueError):
            PatientData(patient_id="P123", name="")

    def test_create_with_all_fields(self):
        """Test creating patient data with all fields."""
        birth_date = date(1980, 1, 1)
        patient = PatientData(
            patient_id="P123",
            name="张三",
            age=44,
            birth_date=birth_date,
            gender=GenderEnum.MALE,
            phone="13800138000",
            email="zhangsan@example.com",
            address="北京市朝阳区",
            emergency_contact="李四",
            emergency_phone="13900139000",
        )
        assert patient.patient_id == "P123"
        assert patient.age == 44
        assert patient.gender == GenderEnum.MALE

    def test_calculate_age_from_birth_date(self):
        """Test calculating age from birth date."""
        birth_date = date(1990, 1, 1)
        patient = PatientData(
            patient_id="P123", name="张三", birth_date=birth_date
        )
        age = patient.calculate_age()
        assert age is not None
        assert age >= 34  # Assuming current date is after 2024

    def test_calculate_age_returns_age_when_no_birth_date(self):
        """Test that calculate_age returns age field when no birth date."""
        patient = PatientData(patient_id="P123", name="张三", age=30)
        assert patient.calculate_age() == 30

    def test_to_dict(self):
        """Test conversion to dictionary."""
        birth_date = date(1980, 1, 1)
        patient = PatientData(
            patient_id="P123",
            name="张三",
            age=44,
            birth_date=birth_date,
            gender=GenderEnum.MALE,
            phone="13800138000",
        )
        result = patient.to_dict()
        assert result["patient_id"] == "P123"
        assert result["name"] == "张三"
        assert result["age"] == 44
        assert result["birth_date"] == "1980-01-01"
        assert result["gender"] == "male"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "patient_id": "P123",
            "name": "张三",
            "age": 44,
            "birth_date": "1980-01-01",
            "gender": "male",
            "phone": "13800138000",
            "email": "zhangsan@example.com",
        }
        patient = PatientData.from_dict(data)
        assert patient.patient_id == "P123"
        assert patient.name == "张三"
        assert patient.age == 44
        assert patient.gender == GenderEnum.MALE

    def test_display_name(self):
        """Test formatted display name."""
        patient = PatientData(
            patient_id="P123",
            name="张三",
            age=44,
            gender=GenderEnum.MALE,
        )
        display = patient.display_name
        assert "张三" in display
        assert "44岁" in display
        assert "男" in display

    def test_display_name_female(self):
        """Test display name with female gender."""
        patient = PatientData(
            patient_id="P123",
            name="李四",
            age=30,
            gender=GenderEnum.FEMALE,
        )
        display = patient.display_name
        assert "李四" in display
        assert "30岁" in display
        assert "女" in display

    def test_display_name_minimal(self):
        """Test display name with minimal info."""
        patient = PatientData(patient_id="P123", name="王五")
        assert patient.display_name == "王五"

    def test_metadata(self):
        """Test metadata field."""
        patient = PatientData(
            patient_id="P123",
            name="张三",
            metadata={"insurance": "ABC123", "notes": "VIP patient"},
        )
        assert patient.metadata["insurance"] == "ABC123"
