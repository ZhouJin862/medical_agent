"""
Pytest configuration and shared fixtures.

This file contains fixtures that are shared across all tests.
"""
import pytest
import sys
from pathlib import Path
from datetime import date, datetime

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========== Domain Layer Fixtures ==========

@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing."""
    from src.domain.shared.value_objects.patient_data import PatientData
    from src.domain.shared.enums.gender import GenderEnum

    return PatientData(
        patient_id="test_patient_001",
        name="测试用户",
        age=45,
        birth_date=date(1979, 1, 1),
        gender=GenderEnum.MALE,
        phone="13800138000",
        email="test@example.com",
    )


@pytest.fixture
def sample_blood_pressure():
    """Sample blood pressure data."""
    from src.domain.shared.value_objects.blood_pressure import BloodPressure

    return BloodPressure(systolic=120, diastolic=80)


@pytest.fixture
def sample_blood_glucose():
    """Sample blood glucose data."""
    from src.domain.shared.value_objects.blood_glucose import BloodGlucose

    return BloodGlucose(fasting_glucose=5.5)


@pytest.fixture
def sample_lipid_profile():
    """Sample lipid profile data."""
    from src.domain.shared.value_objects.lipid_profile import LipidProfile

    return LipidProfile(
        total_cholesterol=5.2,
        ldl_cholesterol=3.0,
        hdl_cholesterol=1.2,
        triglycerides=1.8
    )


@pytest.fixture
def sample_bmi():
    """Sample BMI data."""
    from src.domain.shared.value_objects.bmi import BMI

    return BMI(height_cm=175, weight_kg=70)


@pytest.fixture
def sample_uric_acid():
    """Sample uric acid data."""
    from src.domain.shared.value_objects.uric_acid import UricAcid

    return UricAcid(value=380)


@pytest.fixture
def normal_vital_signs():
    """All normal vital signs for testing."""
    from src.domain.shared.value_objects.blood_pressure import BloodPressure
    from src.domain.shared.value_objects.blood_glucose import BloodGlucose
    from src.domain.shared.value_objects.lipid_profile import LipidProfile
    from src.domain.shared.value_objects.uric_acid import UricAcid
    from src.domain.shared.value_objects.bmi import BMI

    return {
        "blood_pressure": BloodPressure(systolic=120, diastolic=80),
        "blood_glucose": BloodGlucose(fasting_glucose=5.5),
        "lipid_profile": LipidProfile(
            total_cholesterol=5.2,
            ldl_cholesterol=3.0,
            hdl_cholesterol=1.2,
            triglycerides=1.8
        ),
        "uric_acid": UricAcid(value=380),
        "bmi": BMI(height_cm=175, weight_kg=70),
    }


@pytest.fixture
def abnormal_vital_signs():
    """All abnormal vital signs for testing risk assessment."""
    from src.domain.shared.value_objects.blood_pressure import BloodPressure
    from src.domain.shared.value_objects.blood_glucose import BloodGlucose
    from src.domain.shared.value_objects.lipid_profile import LipidProfile
    from src.domain.shared.value_objects.uric_acid import UricAcid
    from src.domain.shared.value_objects.bmi import BMI

    return {
        "blood_pressure": BloodPressure(systolic=150, diastolic=95),  # High
        "blood_glucose": BloodGlucose(fasting_glucose=7.5),  # High
        "lipid_profile": LipidProfile(
            total_cholesterol=6.5,
            ldl_cholesterol=4.5,
            hdl_cholesterol=0.8,
            triglycerides=2.5
        ),  # Abnormal
        "uric_acid": UricAcid(value=480),  # High
        "bmi": BMI(height_cm=175, weight_kg=90),  # Overweight
    }


# ========== Enum Fixtures ==========

@pytest.fixture(params=["male", "female", "other"])
def gender_enum(request):
    """Parametrized gender enum fixture."""
    from src.domain.shared.enums.gender import GenderEnum

    mapping = {
        "male": GenderEnum.MALE,
        "female": GenderEnum.FEMALE,
        "other": GenderEnum.OTHER,
    }
    return mapping[request.param]


@pytest.fixture(params=[
    "hypertension", "diabetes", "dyslipidemia", "gout"
])
def four_highs_type(request):
    """Parametrized four highs type enum fixture."""
    from src.domain.shared.enums.four_highs_type import FourHighsType

    mapping = {
        "hypertension": FourHighsType.HYPERTENSION,
        "diabetes": FourHighsType.DIABETES,
        "dyslipidemia": FourHighsType.DYSLIPIDEMIA,
        "gout": FourHighsType.GOUT,
    }
    return mapping[request.param]


@pytest.fixture(params=["low", "medium", "high", "very_high"])
def risk_level(request):
    """Parametrized risk level enum fixture."""
    from src.domain.shared.enums.risk_level import RiskLevel

    mapping = {
        "low": RiskLevel.LOW,
        "medium": RiskLevel.MEDIUM,
        "high": RiskLevel.HIGH,
        "very_high": RiskLevel.VERY_HIGH,
    }
    return mapping[request.param]


# ========== Database Session Fixture (for tests that need DB) ==========

@pytest.fixture
def db_session():
    """
    Database session fixture for tests that require database access.

    This fixture creates a new database session for each test
    and rolls back changes after the test completes.

    Usage:
        @pytest.mark.requires_db
        def test_with_db(db_session):
            # Your test code here
            pass
    """
    # TODO: Implement when database is properly configured
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    #
    # engine = create_engine("sqlite:///:memory:")
    # Session = sessionmaker(bind=engine)
    #
    # from src.infrastructure.persistence.models.base import Base
    # Base.metadata.create_all(engine)
    #
    # session = Session()
    # yield session
    # session.close()
    pass


# ========== Test Utilities ==========

@pytest.fixture
def assert_valid_domain_object():
    """Fixture that provides a helper function to validate domain objects."""
    def _assert_valid(obj, required_fields=None):
        """Assert that a domain object is valid."""
        assert obj is not None
        if required_fields:
            for field in required_fields:
                assert hasattr(obj, field), f"Missing required field: {field}"
                value = getattr(obj, field)
                assert value is not None, f"Field {field} cannot be None"

    return _assert_valid


@pytest.fixture
def assert_domain_exception():
    """Fixture that provides a helper to test domain exceptions."""
    def _assert_raises(exception_class, message_pattern=None):
        """Assert that calling a function raises a specific exception."""
        def _check(func):
            with pytest.raises(exception_class) as exc_info:
                if message_pattern:
                    assert message_pattern in str(exc_info.value)
            return func
        return _check

    return _assert_raises
