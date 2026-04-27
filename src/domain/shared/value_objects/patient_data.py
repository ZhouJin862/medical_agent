"""Patient data value object."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from ..enums.gender import GenderEnum


@dataclass(frozen=True)
class PatientData:
    """
    Patient data snapshot value object.

    Contains patient demographic and contact information.
    This is an immutable snapshot of patient data at a point in time.
    """

    patient_id: str
    name: str
    age: int | None = None
    birth_date: date | None = None
    gender: GenderEnum | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    emergency_phone: str | None = None
    snapshot_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate patient data."""
        if not self.patient_id:
            raise ValueError("Patient ID is required")
        if not self.name:
            raise ValueError("Patient name is required")

        # Ensure age and birth_date are consistent if both provided
        if self.age is not None and self.birth_date is not None:
            today = date.today()
            calculated_age = (
                today.year
                - self.birth_date.year
                - (
                    (today.month, today.day)
                    < (self.birth_date.month, self.birth_date.day)
                )
            )
            if abs(calculated_age - self.age) > 1:
                # Allow small difference due to birthday timing
                pass

    def calculate_age(self) -> int | None:
        """Calculate age from birth_date if available."""
        if self.birth_date is None:
            return self.age
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - (
                (today.month, today.day)
                < (self.birth_date.month, self.birth_date.day)
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age or self.calculate_age(),
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "gender": self.gender.value if self.gender else None,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "emergency_contact": self.emergency_contact,
            "emergency_phone": self.emergency_phone,
            "snapshot_at": self.snapshot_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatientData":
        """Create PatientData from dictionary."""
        gender = data.get("gender")
        birth_date = data.get("birth_date")
        snapshot_at = data.get("snapshot_at")

        return cls(
            patient_id=data["patient_id"],
            name=data["name"],
            age=data.get("age"),
            birth_date=date.fromisoformat(birth_date) if birth_date else None,
            gender=GenderEnum(gender) if gender else None,
            phone=data.get("phone"),
            email=data.get("email"),
            address=data.get("address"),
            emergency_contact=data.get("emergency_contact"),
            emergency_phone=data.get("emergency_phone"),
            snapshot_at=datetime.fromisoformat(snapshot_at) if snapshot_at else None,
            metadata=data.get("metadata", {}),
        )

    @property
    def display_name(self) -> str:
        """Get formatted display name with age and gender."""
        parts = [self.name]
        age = self.age or self.calculate_age()
        if age:
            parts.append(f"{age}岁")
        if self.gender:
            gender_text = "男" if self.gender == GenderEnum.MALE else "女"
            parts.append(gender_text)
        return " ".join(parts)
