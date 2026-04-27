"""Unit tests for domain enums."""

import pytest

from src.domain.shared.enums.gender import GenderEnum
from src.domain.shared.enums.four_highs_type import FourHighsType
from src.domain.shared.enums.risk_level import RiskLevel


class TestGenderEnum:
    """Tests for GenderEnum."""

    def test_male_value(self):
        """Test male enum value."""
        assert GenderEnum.MALE.value == "male"

    def test_female_value(self):
        """Test female enum value."""
        assert GenderEnum.FEMALE.value == "female"

    def test_other_value(self):
        """Test other enum value."""
        assert GenderEnum.OTHER.value == "other"

    def test_from_string_male(self):
        """Test parsing male from string."""
        assert GenderEnum.from_string("male") == GenderEnum.MALE
        assert GenderEnum.from_string("MALE") == GenderEnum.MALE
        assert GenderEnum.from_string("  Male  ") == GenderEnum.MALE

    def test_from_string_female(self):
        """Test parsing female from string."""
        assert GenderEnum.from_string("female") == GenderEnum.FEMALE
        assert GenderEnum.from_string("FEMALE") == GenderEnum.FEMALE

    def test_from_string_invalid(self):
        """Test that invalid string raises exception."""
        with pytest.raises(ValueError):
            GenderEnum.from_string("unknown")


class TestFourHighsType:
    """Tests for FourHighsType enum."""

    def test_hypertension(self):
        """Test hypertension type."""
        assert FourHighsType.HYPERTENSION.value == "hypertension"
        assert FourHighsType.HYPERTENSION.display_name == "高血压"
        assert FourHighsType.HYPERTENSION.english_name == "Hypertension"

    def test_diabetes(self):
        """Test diabetes type."""
        assert FourHighsType.DIABETES.value == "diabetes"
        assert FourHighsType.DIABETES.display_name == "糖尿病"
        assert FourHighsType.DIABETES.english_name == "Diabetes"

    def test_dyslipidemia(self):
        """Test dyslipidemia type."""
        assert FourHighsType.DYSLIPIDEMIA.value == "dyslipidemia"
        assert FourHighsType.DYSLIPIDEMIA.display_name == "血脂异常"
        assert FourHighsType.DYSLIPIDEMIA.english_name == "Dyslipidemia"

    def test_gout(self):
        """Test gout type."""
        assert FourHighsType.GOUT.value == "gout"
        assert FourHighsType.GOUT.display_name == "痛风"
        assert FourHighsType.GOUT.english_name == "Gout"

    def test_from_string_valid(self):
        """Test parsing from valid string."""
        assert FourHighsType.from_string("hypertension") == FourHighsType.HYPERTENSION
        assert FourHighsType.from_string("HYPERTENSION") == FourHighsType.HYPERTENSION
        assert FourHighsType.from_string("  diabetes  ") == FourHighsType.DIABETES

    def test_from_string_invalid(self):
        """Test that invalid string raises exception."""
        with pytest.raises(ValueError):
            FourHighsType.from_string("asthma")


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_low(self):
        """Test low risk level."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.LOW.display_name == "低风险"
        assert RiskLevel.LOW.numeric_value == 0

    def test_medium(self):
        """Test medium risk level."""
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.MEDIUM.display_name == "中风险"
        assert RiskLevel.MEDIUM.numeric_value == 1

    def test_high(self):
        """Test high risk level."""
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.HIGH.display_name == "高风险"
        assert RiskLevel.HIGH.numeric_value == 2

    def test_very_high(self):
        """Test very high risk level."""
        assert RiskLevel.VERY_HIGH.value == "very_high"
        assert RiskLevel.VERY_HIGH.display_name == "极高风险"
        assert RiskLevel.VERY_HIGH.numeric_value == 3

    def test_from_string_valid(self):
        """Test parsing from valid string."""
        assert RiskLevel.from_string("low") == RiskLevel.LOW
        assert RiskLevel.from_string("LOW") == RiskLevel.LOW
        assert RiskLevel.from_string("very high") == RiskLevel.VERY_HIGH
        assert RiskLevel.from_string("very-high") == RiskLevel.VERY_HIGH

    def test_from_string_invalid(self):
        """Test that invalid string raises exception."""
        with pytest.raises(ValueError):
            RiskLevel.from_string("extreme")

    def test_numeric_comparison(self):
        """Test that numeric_value allows comparison."""
        assert RiskLevel.LOW.numeric_value < RiskLevel.MEDIUM.numeric_value
        assert RiskLevel.MEDIUM.numeric_value < RiskLevel.HIGH.numeric_value
        assert RiskLevel.HIGH.numeric_value < RiskLevel.VERY_HIGH.numeric_value
