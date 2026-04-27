"""Domain exception base class."""


class DomainException(Exception):
    """Base exception for domain-specific errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)
