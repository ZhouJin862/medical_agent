"""Unit tests for UricAcid value object."""

import pytest
from datetime import datetime

from src.domain.shared.value_objects.uric_acid import UricAcid, GenderEnum
from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException


class TestUricAcid:
    """Tests for UricAcid value object."""

    def test_create_valid_uric_acid(self):
        """Test creating a valid uric acid reading."""
        ua = UricAcid(
            value=350,
            measured_at=datetime.now(),
            gender=GenderEnum.MALE,
        )
        assert ua.value == 350
        assert ua.gender == GenderEnum.MALE

    def test_create_without_gender(self):
        """Test creating uric acid without gender."""
        ua = UricAcid(value=350, measured_at=datetime.now())
        assert ua.value == 350
        assert ua.gender is None

    def test_value_out_of_range_low(self):
        """Test that low value raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            UricAcid(value=30, measured_at=datetime.now())

    def test_value_out_of_range_high(self):
        """Test that high value raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            UricAcid(value=1500, measured_at=datetime.now())

    def test_reference_upper_male(self):
        """Test reference upper limit for male."""
        ua = UricAcid(value=400, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.reference_upper == 420

    def test_reference_upper_female(self):
        """Test reference upper limit for female."""
        ua = UricAcid(
            value=400, measured_at=datetime.now(), gender=GenderEnum.FEMALE
        )
        assert ua.reference_upper == 360

    def test_is_normal_male(self):
        """Test is_normal for male."""
        ua = UricAcid(value=350, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.is_normal()

    def test_is_normal_female(self):
        """Test is_normal for female."""
        ua = UricAcid(
            value=300, measured_at=datetime.now(), gender=GenderEnum.FEMALE
        )
        assert ua.is_normal()

    def test_is_abnormal_male(self):
        """Test is_normal for abnormal male value."""
        ua = UricAcid(value=450, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert not ua.is_normal()

    def test_classify_normal(self):
        """Test classification of normal uric acid."""
        ua = UricAcid(value=350, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.classify() == "正常"

    def test_classify_mild_elevation(self):
        """Test classification of mild elevation."""
        ua = UricAcid(value=450, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.classify() == "轻度升高"

    def test_classify_moderate_elevation(self):
        """Test classification of moderate elevation."""
        ua = UricAcid(value=500, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.classify() == "中度升高"

    def test_classify_severe_elevation(self):
        """Test classification of severe elevation."""
        ua = UricAcid(value=600, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.classify() == "重度升高"

    def test_risk_level_normal(self):
        """Test risk level for normal value."""
        ua = UricAcid(value=350, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.get_risk_level() == "正常"

    def test_risk_level_low(self):
        """Test risk level for low risk."""
        ua = UricAcid(value=430, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.get_risk_level() == "低风险"

    def test_risk_level_medium(self):
        """Test risk level for medium risk."""
        ua = UricAcid(value=500, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.get_risk_level() == "中风险"

    def test_risk_level_high(self):
        """Test risk level for high risk."""
        ua = UricAcid(value=550, measured_at=datetime.now(), gender=GenderEnum.MALE)
        assert ua.get_risk_level() == "高风险"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime.now()
        ua = UricAcid(
            value=400,
            measured_at=now,
            gender=GenderEnum.MALE,
            source="lab",
        )
        result = ua.to_dict()
        assert result["value"] == 400
        assert result["unit"] == "μmol/L"
        assert result["gender"] == "male"
        assert result["reference_upper"] == 420
        assert result["source"] == "lab"

    def test_from_dict(self):
        """Test creation from dictionary."""
        now = datetime.now()
        data = {
            "value": 400,
            "measured_at": now.isoformat(),
            "gender": "male",
            "source": "clinic",
        }
        ua = UricAcid.from_dict(data)
        assert ua.value == 400
        assert ua.gender == GenderEnum.MALE
        assert ua.source == "clinic"
