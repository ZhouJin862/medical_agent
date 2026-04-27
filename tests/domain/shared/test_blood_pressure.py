"""Unit tests for BloodPressure value object."""

import pytest
from datetime import datetime

from src.domain.shared.value_objects.blood_pressure import BloodPressure
from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException


class TestBloodPressure:
    """Tests for BloodPressure value object."""

    def test_create_valid_blood_pressure(self):
        """Test creating a valid blood pressure reading."""
        bp = BloodPressure(
            systolic=120,
            diastolic=80,
            measured_at=datetime.now(),
        )
        assert bp.systolic == 120
        assert bp.diastolic == 80

    def test_systolic_out_of_range_low(self):
        """Test that low systolic raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodPressure(systolic=40, diastolic=70, measured_at=datetime.now())

    def test_systolic_out_of_range_high(self):
        """Test that high systolic raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodPressure(systolic=350, diastolic=90, measured_at=datetime.now())

    def test_diastolic_out_of_range_low(self):
        """Test that low diastolic raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodPressure(systolic=120, diastolic=20, measured_at=datetime.now())

    def test_diastolic_out_of_range_high(self):
        """Test that high diastolic raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodPressure(systolic=120, diastolic=250, measured_at=datetime.now())

    def test_systolic_not_greater_than_diastolic(self):
        """Test that systolic must be greater than diastolic."""
        with pytest.raises(InvalidVitalSignsException):
            BloodPressure(systolic=80, diastolic=80, measured_at=datetime.now())

    def test_classify_normal(self):
        """Test classification of normal blood pressure."""
        bp = BloodPressure(systolic=115, diastolic=75, measured_at=datetime.now())
        assert bp.classify() == "正常"
        assert bp.is_normal()

    def test_classify_high_normal(self):
        """Test classification of high-normal blood pressure."""
        bp = BloodPressure(systolic=130, diastolic=85, measured_at=datetime.now())
        assert bp.classify() == "正常高值"

    def test_classify_grade_1_hypertension(self):
        """Test classification of grade 1 hypertension."""
        bp = BloodPressure(systolic=150, diastolic=95, measured_at=datetime.now())
        assert bp.classify() == "1级"

    def test_classify_grade_2_hypertension(self):
        """Test classification of grade 2 hypertension."""
        bp = BloodPressure(systolic=165, diastolic=105, measured_at=datetime.now())
        assert bp.classify() == "2级"

    def test_classify_grade_3_hypertension(self):
        """Test classification of grade 3 hypertension."""
        bp = BloodPressure(systolic=185, diastolic=115, measured_at=datetime.now())
        assert bp.classify() == "3级"

    def test_pulse_pressure(self):
        """Test pulse pressure calculation."""
        bp = BloodPressure(systolic=120, diastolic=80, measured_at=datetime.now())
        assert bp.pulse_pressure == 40

    def test_mean_arterial_pressure(self):
        """Test mean arterial pressure calculation."""
        bp = BloodPressure(systolic=120, diastolic=80, measured_at=datetime.now())
        expected_map = 80 + (40 / 3)
        assert bp.mean_arterial_pressure == pytest.approx(expected_map)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime.now()
        bp = BloodPressure(
            systolic=120,
            diastolic=80,
            measured_at=now,
            source="home_monitor",
        )
        result = bp.to_dict()
        assert result["systolic"] == 120
        assert result["diastolic"] == 80
        assert result["classification"] == "正常高值"
        assert result["source"] == "home_monitor"

    def test_from_dict(self):
        """Test creation from dictionary."""
        now = datetime.now()
        data = {
            "systolic": 140,
            "diastolic": 90,
            "measured_at": now.isoformat(),
            "source": "clinic",
        }
        bp = BloodPressure.from_dict(data)
        assert bp.systolic == 140
        assert bp.diastolic == 90
        assert bp.source == "clinic"
