"""Domain exceptions module."""

from .domain_exception import DomainException
from .patient_not_found import PatientNotFoundException
from .invalid_vital_signs import InvalidVitalSignsException

__all__ = [
    "DomainException",
    "PatientNotFoundException",
    "InvalidVitalSignsException",
]
