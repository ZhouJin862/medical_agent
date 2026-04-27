"""Unit tests for BMI value object."""

import pytest
from datetime import datetime

from src.domain.shared.value_objects.bmi import BMI
from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException


class TestBMI:
    """Tests for BMI value object."""

    def test_create_valid_bmi(self):
        """Test creating a valid BMI."""
        bmi = BMI(value=22.5, measured_at=datetime.now())
        assert bmi.value == 22.5

    def test_value_out_of_range_low(self):
        """Test that low BMI raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BMI(value=5.0, measured_at=datetime.now())

    def test_value_out_of_range_high(self):
        """Test that high BMI raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BMI(value=80.0, measured_at=datetime.now())

    def test_calculate_valid(self):
        """Test calculating BMI from weight and height."""
        bmi = BMI.calculate(weight_kg=70, height_m=1.75)
        expected_bmi = round(70 / (1.75**2), 1)
        assert bmi.value == expected_bmi

    def test_calculate_weight_out_of_range_low(self):
        """Test that low weight raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BMI.calculate(weight_kg=20, height_m=1.75)

    def test_calculate_weight_out_of_range_high(self):
        """Test that high weight raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BMI.calculate(weight_kg=350, height_m=1.75)

    def test_calculate_height_out_of_range_low(self):
        """Test that low height raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BMI.calculate(weight_kg=70, height_m=0.5)

    def test_calculate_height_out_of_range_high(self):
        """Test that high height raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            BMI.calculate(weight_kg=70, height_m=3.0)

    def test_is_normal_underweight(self):
        """Test is_normal for underweight."""
        bmi = BMI(value=17.0, measured_at=datetime.now())
        assert not bmi.is_normal()

    def test_is_normal_normal(self):
        """Test is_normal for normal BMI."""
        bmi = BMI(value=22.0, measured_at=datetime.now())
        assert bmi.is_normal()

    def test_is_normal_overweight(self):
        """Test is_normal for overweight."""
        bmi = BMI(value=26.0, measured_at=datetime.now())
        assert not bmi.is_normal()

    def test_classify_underweight(self):
        """Test classification of underweight."""
        bmi = BMI(value=17.0, measured_at=datetime.now())
        assert bmi.classify() == "偏瘦"

    def test_classify_normal(self):
        """Test classification of normal BMI."""
        bmi = BMI(value=22.0, measured_at=datetime.now())
        assert bmi.classify() == "正常"

    def test_classify_overweight(self):
        """Test classification of overweight."""
        bmi = BMI(value=26.0, measured_at=datetime.now())
        assert bmi.classify() == "超重"

    def test_classify_obese(self):
        """Test classification of obese."""
        bmi = BMI(value=30.0, measured_at=datetime.now())
        assert bmi.classify() == "肥胖"

    def test_boundary_normal_lower(self):
        """Test boundary at 18.5 (lower limit of normal)."""
        bmi = BMI(value=18.5, measured_at=datetime.now())
        assert bmi.classify() == "正常"
        assert bmi.is_normal()

    def test_boundary_normal_upper(self):
        """Test boundary at 24.0 (upper limit of normal)."""
        bmi = BMI(value=23.9, measured_at=datetime.now())
        assert bmi.classify() == "正常"
        assert bmi.is_normal()

    def test_boundary_overweight_lower(self):
        """Test boundary at 24.0 (lower limit of overweight)."""
        bmi = BMI(value=24.0, measured_at=datetime.now())
        assert bmi.classify() == "超重"

    def test_boundary_obese_lower(self):
        """Test boundary at 28.0 (lower limit of obese)."""
        bmi = BMI(value=28.0, measured_at=datetime.now())
        assert bmi.classify() == "肥胖"

    def test_health_risk_underweight(self):
        """Test health risk for underweight."""
        bmi = BMI(value=17.0, measured_at=datetime.now())
        assert bmi.get_health_risk() == "营养不良风险"

    def test_health_risk_normal(self):
        """Test health risk for normal BMI."""
        bmi = BMI(value=22.0, measured_at=datetime.now())
        assert bmi.get_health_risk() == "低风险"

    def test_health_risk_overweight(self):
        """Test health risk for overweight."""
        bmi = BMI(value=26.0, measured_at=datetime.now())
        assert bmi.get_health_risk() == "增加风险"

    def test_health_risk_obese(self):
        """Test health risk for obese."""
        bmi = BMI(value=30.0, measured_at=datetime.now())
        assert bmi.get_health_risk() == "高风险"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime.now()
        bmi = BMI(value=24.5, measured_at=now, source="clinic")
        result = bmi.to_dict()
        assert result["value"] == 24.5
        assert result["unit"] == "kg/m²"
        assert result["classification"] == "超重"
        assert result["source"] == "clinic"

    def test_from_dict(self):
        """Test creation from dictionary."""
        now = datetime.now()
        data = {
            "value": 22.0,
            "measured_at": now.isoformat(),
            "source": "home",
        }
        bmi = BMI.from_dict(data)
        assert bmi.value == 22.0
        assert bmi.source == "home"
