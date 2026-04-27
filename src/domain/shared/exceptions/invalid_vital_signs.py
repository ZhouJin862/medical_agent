"""Invalid vital signs exception."""

from .domain_exception import DomainException


class InvalidVitalSignsException(DomainException):
    """Exception raised when vital signs data is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid vital signs: {message}")
