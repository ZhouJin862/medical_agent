"""Unit tests for domain exceptions."""

import pytest

from src.domain.shared.exceptions.domain_exception import DomainException
from src.domain.shared.exceptions.patient_not_found import PatientNotFoundException
from src.domain.shared.exceptions.invalid_vital_signs import (
    InvalidVitalSignsException,
)


class TestDomainException:
    """Tests for DomainException base class."""

    def test_create_domain_exception(self):
        """Test creating a domain exception."""
        exc = DomainException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"

    def test_domain_exception_is_exception(self):
        """Test that DomainException inherits from Exception."""
        exc = DomainException("Test")
        assert isinstance(exc, Exception)


class TestPatientNotFoundException:
    """Tests for PatientNotFoundException."""

    def test_create_patient_not_found_exception(self):
        """Test creating patient not found exception."""
        exc = PatientNotFoundException("P123")
        assert "P123" in str(exc)
        assert "P123" in exc.message
        assert exc.patient_id == "P123"

    def test_is_domain_exception(self):
        """Test that PatientNotFoundException inherits from DomainException."""
        exc = PatientNotFoundException("P123")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)


class TestInvalidVitalSignsException:
    """Tests for InvalidVitalSignsException."""

    def test_create_invalid_vital_signs_exception(self):
        """Test creating invalid vital signs exception."""
        exc = InvalidVitalSignsException("Invalid blood pressure")
        assert "Invalid vital signs" in str(exc)
        assert "Invalid blood pressure" in str(exc)

    def test_is_domain_exception(self):
        """Test that InvalidVitalSignsException inherits from DomainException."""
        exc = InvalidVitalSignsException("Test error")
        assert isinstance(exc, DomainException)
        assert isinstance(exc, Exception)
