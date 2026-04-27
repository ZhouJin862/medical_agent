"""Domain shared kernel module."""

from .value_objects import (
    PatientData,
    VitalSigns,
    BloodPressure,
    BloodGlucose,
    GlucoseMeasurementType,
    LipidProfile,
    UricAcid,
    BMI,
    DiseaseType,
    ContextSnapshot,
)
from .enums import GenderEnum, FourHighsType, RiskLevel
from .exceptions import (
    DomainException,
    PatientNotFoundException,
    InvalidVitalSignsException,
)

__all__ = [
    # Value Objects
    "PatientData",
    "VitalSigns",
    "BloodPressure",
    "BloodGlucose",
    "GlucoseMeasurementType",
    "LipidProfile",
    "UricAcid",
    "BMI",
    "DiseaseType",
    "ContextSnapshot",
    # Enums
    "GenderEnum",
    "FourHighsType",
    "RiskLevel",
    # Exceptions
    "DomainException",
    "PatientNotFoundException",
    "InvalidVitalSignsException",
]
