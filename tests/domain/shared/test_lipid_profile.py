"""Unit tests for LipidProfile value object."""

import pytest
from datetime import datetime

from src.domain.shared.value_objects.lipid_profile import LipidProfile
from src.domain.shared.exceptions.invalid_vital_signs import InvalidVitalSignsException


class TestLipidProfile:
    """Tests for LipidProfile value object."""

    def test_create_valid_lipid_profile(self):
        """Test creating a valid lipid profile."""
        lp = LipidProfile(
            tc=5.0,
            tg=1.5,
            ldl_c=3.0,
            hdl_c=1.2,
            measured_at=datetime.now(),
        )
        assert lp.tc == 5.0
        assert lp.tg == 1.5
        assert lp.ldl_c == 3.0
        assert lp.hdl_c == 1.2

    def test_create_partial_lipid_profile(self):
        """Test creating lipid profile with only some values."""
        lp = LipidProfile(tc=5.0, measured_at=datetime.now())
        assert lp.tc == 5.0
        assert lp.tg is None
        assert lp.ldl_c is None
        assert lp.hdl_c is None

    def test_empty_lipid_profile_raises_exception(self):
        """Test that lipid profile with no values raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            LipidProfile(measured_at=datetime.now())

    def test_tc_out_of_range_low(self):
        """Test that low TC raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            LipidProfile(tc=0.5, measured_at=datetime.now())

    def test_tc_out_of_range_high(self):
        """Test that high TC raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            LipidProfile(tc=25.0, measured_at=datetime.now())

    def test_tg_out_of_range_low(self):
        """Test that low TG raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            LipidProfile(tg=0.1, measured_at=datetime.now())

    def test_ldl_c_out_of_range_high(self):
        """Test that high LDL-C raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            LipidProfile(ldl_c=20.0, measured_at=datetime.now())

    def test_hdl_c_out_of_range_low(self):
        """Test that low HDL-C raises exception."""
        with pytest.raises(InvalidVitalSignsException):
            LipidProfile(hdl_c=0.1, measured_at=datetime.now())

    def test_is_normal_all_normal(self):
        """Test is_normal when all values are normal."""
        lp = LipidProfile(
            tc=4.5,
            tg=1.0,
            ldl_c=2.5,
            hdl_c=1.2,
            measured_at=datetime.now(),
        )
        assert lp.is_normal()

    def test_is_normal_abnormal_tc(self):
        """Test is_normal when TC is abnormal."""
        lp = LipidProfile(tc=6.5, measured_at=datetime.now())
        assert not lp.is_normal()

    def test_classify_normal(self):
        """Test classification of normal lipid profile."""
        lp = LipidProfile(
            tc=4.5,
            tg=1.0,
            ldl_c=2.5,
            hdl_c=1.2,
            measured_at=datetime.now(),
        )
        assert lp.classify() == "正常"

    def test_classify_one_abnormal(self):
        """Test classification with one abnormal value."""
        lp = LipidProfile(tc=6.5, measured_at=datetime.now())
        assert lp.classify() == "边缘异常"

    def test_classify_multiple_abnormal(self):
        """Test classification with multiple abnormal values."""
        lp = LipidProfile(
            tc=6.5,
            tg=2.5,
            measured_at=datetime.now(),
        )
        assert lp.classify() == "血脂异常"

    def test_tc_class(self):
        """Test TC classification."""
        lp = LipidProfile(tc=6.5, measured_at=datetime.now())
        assert lp.tc_class == "升高"

    def test_tg_class(self):
        """Test TG classification."""
        lp = LipidProfile(tg=2.5, measured_at=datetime.now())
        assert lp.tg_class == "升高"

    def test_ldl_c_class(self):
        """Test LDL-C classification."""
        lp = LipidProfile(ldl_c=4.5, measured_at=datetime.now())
        assert lp.ldl_c_class == "升高"

    def test_hdl_c_class_low(self):
        """Test HDL-C classification for low value."""
        lp = LipidProfile(hdl_c=0.8, measured_at=datetime.now())
        assert lp.hdl_c_class == "降低"

    def test_get_abnormal_count(self):
        """Test counting abnormal values."""
        lp = LipidProfile(
            tc=6.5,
            tg=2.5,
            ldl_c=4.0,
            hdl_c=0.8,
            measured_at=datetime.now(),
        )
        assert lp.get_abnormal_count() == 4

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime.now()
        lp = LipidProfile(
            tc=5.0,
            tg=1.5,
            ldl_c=3.0,
            hdl_c=1.2,
            measured_at=now,
            source="lab",
        )
        result = lp.to_dict()
        assert result["tc"] == 5.0
        assert result["unit"] == "mmol/L"
        assert result["source"] == "lab"

    def test_from_dict(self):
        """Test creation from dictionary."""
        now = datetime.now()
        data = {
            "tc": 5.5,
            "tg": 2.0,
            "ldl_c": 3.5,
            "hdl_c": 1.0,
            "measured_at": now.isoformat(),
            "source": "clinic",
        }
        lp = LipidProfile.from_dict(data)
        assert lp.tc == 5.5
        assert lp.tg == 2.0
        assert lp.source == "clinic"
