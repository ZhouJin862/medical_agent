"""Unit tests for DiseaseType value object."""

import pytest
from datetime import datetime

from src.domain.shared.value_objects.disease_type import DiseaseType
from src.domain.shared.enums.four_highs_type import FourHighsType


class TestDiseaseType:
    """Tests for DiseaseType value object."""

    def test_create_hypertension(self):
        """Test creating hypertension disease type."""
        disease = DiseaseType(
            disease=FourHighsType.HYPERTENSION,
            diagnosed_at=datetime.now(),
        )
        assert disease.disease == FourHighsType.HYPERTENSION

    def test_create_diabetes(self):
        """Test creating diabetes disease type."""
        disease = DiseaseType(
            disease=FourHighsType.DIABETES,
            diagnosed_at=datetime.now(),
        )
        assert disease.disease == FourHighsType.DIABETES

    def test_create_dyslipidemia(self):
        """Test creating dyslipidemia disease type."""
        disease = DiseaseType(
            disease=FourHighsType.DYSLIPIDEMIA,
            diagnosed_at=datetime.now(),
        )
        assert disease.disease == FourHighsType.DYSLIPIDEMIA

    def test_create_gout(self):
        """Test creating gout disease type."""
        disease = DiseaseType(
            disease=FourHighsType.GOUT,
            diagnosed_at=datetime.now(),
        )
        assert disease.disease == FourHighsType.GOUT

    def test_is_normal_always_false(self):
        """Test that is_normal always returns False for diseases."""
        disease = DiseaseType(
            disease=FourHighsType.HYPERTENSION,
            diagnosed_at=datetime.now(),
        )
        assert not disease.is_normal()

    def test_get_classification_hypertension(self):
        """Test get_classification for hypertension."""
        disease = DiseaseType(
            disease=FourHighsType.HYPERTENSION,
            diagnosed_at=datetime.now(),
        )
        assert disease.get_classification() == "高血压"

    def test_get_classification_diabetes(self):
        """Test get_classification for diabetes."""
        disease = DiseaseType(
            disease=FourHighsType.DIABETES,
            diagnosed_at=datetime.now(),
        )
        assert disease.get_classification() == "糖尿病"

    def test_get_classification_dyslipidemia(self):
        """Test get_classification for dyslipidemia."""
        disease = DiseaseType(
            disease=FourHighsType.DYSLIPIDEMIA,
            diagnosed_at=datetime.now(),
        )
        assert disease.get_classification() == "血脂异常"

    def test_get_classification_gout(self):
        """Test get_classification for gout."""
        disease = DiseaseType(
            disease=FourHighsType.GOUT,
            diagnosed_at=datetime.now(),
        )
        assert disease.get_classification() == "痛风"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime.now()
        disease = DiseaseType(
            disease=FourHighsType.HYPERTENSION,
            diagnosed_at=now,
            source="hospital",
            notes="Mild case",
        )
        result = disease.to_dict()
        assert result["disease"] == "hypertension"
        assert result["disease_name_cn"] == "高血压"
        assert result["disease_name_en"] == "Hypertension"
        assert result["source"] == "hospital"
        assert result["notes"] == "Mild case"

    def test_from_dict(self):
        """Test creation from dictionary."""
        now = datetime.now()
        data = {
            "disease": "diabetes",
            "diagnosed_at": now.isoformat(),
            "source": "clinic",
            "notes": "Type 2",
        }
        disease = DiseaseType.from_dict(data)
        assert disease.disease == FourHighsType.DIABETES
        assert disease.source == "clinic"
        assert disease.notes == "Type 2"

    def test_measured_at_property(self):
        """Test measured_at property returns diagnosed_at."""
        now = datetime.now()
        disease = DiseaseType(
            disease=FourHighsType.HYPERTENSION,
            diagnosed_at=now,
        )
        assert disease.measured_at == now
