"""Unit tests for BloodGlucose value object."""

import pytest
from datetime import datetime

from src.domain.shared.value_objects.blood_glucose import (
    BloodGlucose,
    GlucoseMeasurementType,
)
from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException


class TestBloodGlucose:
    """Tests for BloodGlucose value object."""

    def test_create_valid_fasting_glucose(self):
        """Test creating a valid fasting blood glucose reading."""
        bg = BloodGlucose(
            value=5.5,
            measurement_type=GlucoseMeasurementType.FASTING,
            measured_at=datetime.now(),
        )
        assert bg.value == 5.5
        assert bg.measurement_type == GlucoseMeasurementType.FASTING

    def test_negative_glucose_raises_exception(self):
        """Test that negative glucose raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodGlucose(
                value=-1.0,
                measurement_type=GlucoseMeasurementType.FASTING,
                measured_at=datetime.now(),
            )

    def test_hba1c_out_of_range_low(self):
        """Test that low HbA1c raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodGlucose(
                value=2.0,
                measurement_type=GlucoseMeasurementType.HBA1C,
                measured_at=datetime.now(),
            )

    def test_hba1c_out_of_range_high(self):
        """Test that high HbA1c raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BloodGlucose(
                value=20.0,
                measurement_type=GlucoseMeasurementType.HBA1C,
                measured_at=datetime.now(),
            )

    def test_fasting_normal(self):
        """Test normal fasting glucose classification."""
        bg = BloodGlucose(
            value=5.0,
            measurement_type=GlucoseMeasurementType.FASTING,
            measured_at=datetime.now(),
        )
        assert bg.is_normal()
        assert bg.classify() == "正常"

    def test_fasting_impaired(self):
        """Test impaired fasting glucose classification."""
        bg = BloodGlucose(
            value=6.5,
            measurement_type=GlucoseMeasurementType.FASTING,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "空腹血糖受损"

    def test_fasting_diabetes(self):
        """Test diabetes classification for fasting glucose."""
        bg = BloodGlucose(
            value=7.5,
            measurement_type=GlucoseMeasurementType.FASTING,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "糖尿病"

    def test_postprandial_normal(self):
        """Test normal postprandial glucose classification."""
        bg = BloodGlucose(
            value=6.5,
            measurement_type=GlucoseMeasurementType.POSTPRANDIAL_2H,
            measured_at=datetime.now(),
        )
        assert bg.is_normal()
        assert bg.classify() == "正常"

    def test_postprandial_impaired(self):
        """Test impaired glucose tolerance classification."""
        bg = BloodGlucose(
            value=9.0,
            measurement_type=GlucoseMeasurementType.POSTPRANDIAL_2H,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "糖耐量受损"

    def test_postprandial_diabetes(self):
        """Test diabetes classification for postprandial glucose."""
        bg = BloodGlucose(
            value=12.0,
            measurement_type=GlucoseMeasurementType.POSTPRANDIAL_2H,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "糖尿病"

    def test_hba1c_normal(self):
        """Test normal HbA1c classification."""
        bg = BloodGlucose(
            value=5.0,
            measurement_type=GlucoseMeasurementType.HBA1C,
            measured_at=datetime.now(),
        )
        assert bg.is_normal()
        assert bg.classify() == "正常"

    def test_hba1c_prediabetes(self):
        """Test prediabetes HbA1c classification."""
        bg = BloodGlucose(
            value=6.0,
            measurement_type=GlucoseMeasurementType.HBA1C,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "糖尿病前期"

    def test_hba1c_diabetes(self):
        """Test diabetes HbA1c classification."""
        bg = BloodGlucose(
            value=7.0,
            measurement_type=GlucoseMeasurementType.HBA1C,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "糖尿病"

    def test_random_glucose_normal(self):
        """Test normal random glucose classification."""
        bg = BloodGlucose(
            value=8.0,
            measurement_type=GlucoseMeasurementType.RANDOM,
            measured_at=datetime.now(),
        )
        assert bg.is_normal()
        assert bg.classify() == "正常"

    def test_random_glucose_diabetes(self):
        """Test diabetes classification for random glucose."""
        bg = BloodGlucose(
            value=15.0,
            measurement_type=GlucoseMeasurementType.RANDOM,
            measured_at=datetime.now(),
        )
        assert bg.classify() == "糖尿病可能"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime.now()
        bg = BloodGlucose(
            value=5.5,
            measurement_type=GlucoseMeasurementType.FASTING,
            measured_at=now,
            source="lab",
        )
        result = bg.to_dict()
        assert result["value"] == 5.5
        assert result["unit"] == "mmol/L"
        assert result["measurement_type"] == "fasting"
        assert result["source"] == "lab"

    def test_to_dict_hba1c_unit(self):
        """Test that HbA1c uses % unit."""
        bg = BloodGlucose(
            value=6.5,
            measurement_type=GlucoseMeasurementType.HBA1C,
            measured_at=datetime.now(),
        )
        result = bg.to_dict()
        assert result["unit"] == "%"

    def test_from_dict(self):
        """Test creation from dictionary."""
        now = datetime.now()
        data = {
            "value": 7.0,
            "measurement_type": "fasting",
            "measured_at": now.isoformat(),
            "source": "clinic",
        }
        bg = BloodGlucose.from_dict(data)
        assert bg.value == 7.0
        assert bg.measurement_type == GlucoseMeasurementType.FASTING
        assert bg.source == "clinic"
