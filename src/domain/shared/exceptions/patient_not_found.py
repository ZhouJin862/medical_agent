"""Patient not found exception."""

from .domain_exception import DomainException


class PatientNotFoundException(DomainException):
    """Exception raised when a patient cannot be found."""

    def __init__(self, patient_id: str) -> None:
        self.patient_id = patient_id
        super().__init__(f"Patient with ID '{patient_id}' not found")
