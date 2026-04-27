"""
TriageRecommendation Value Object - Hospital/doctor triage recommendations.

Encapsulates recommendations for:
- Hospitals
- Departments
- Doctors
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class Priority(Enum):
    """Priority level for triage."""

    URGENT = "urgent"  # 立即就医
    SOON = "soon"  # 尽快就医
    ROUTINE = "routine"  # 常规就诊
    OPTIONAL = "optional"  # 可选


@dataclass
class Hospital:
    """
    Hospital recommendation.

    Attributes:
        hospital_id: Hospital identifier
        name: Hospital name
        distance_km: Distance in kilometers
        rating: Hospital rating (1-5)
        address: Hospital address
        phone: Contact phone
        departments: Available departments
        specialties: Medical specialties
    """

    hospital_id: str
    name: str
    distance_km: float
    rating: float
    address: str
    phone: Optional[str] = None
    departments: List[str] = field(default_factory=list)
    specialties: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hospital_id": self.hospital_id,
            "name": self.name,
            "distance_km": self.distance_km,
            "rating": self.rating,
            "address": self.address,
            "phone": self.phone,
            "departments": self.departments,
            "specialties": self.specialties,
        }


@dataclass
class Department:
    """
    Department recommendation.

    Attributes:
        department_id: Department identifier
        name: Department name
        description: Department description
        typical_conditions: Typical conditions treated
    """

    department_id: str
    name: str
    description: str
    typical_conditions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "department_id": self.department_id,
            "name": self.name,
            "description": self.description,
            "typical_conditions": self.typical_conditions,
        }


@dataclass
class Doctor:
    """
    Doctor recommendation.

    Attributes:
        doctor_id: Doctor identifier
        name: Doctor name
        title: Professional title
        specialty: Medical specialty
        department: Department name
        schedule: Available schedule
        rating: Doctor rating (1-5)
    """

    doctor_id: str
    name: str
    title: str
    specialty: str
    department: str
    schedule: Dict[str, str] = field(default_factory=dict)
    rating: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doctor_id": self.doctor_id,
            "name": self.name,
            "title": self.title,
            "specialty": self.specialty,
            "department": self.department,
            "schedule": self.schedule,
            "rating": self.rating,
        }


@dataclass
class TriageRecommendation:
    """
    Complete triage recommendation.

    Attributes:
        priority: Urgency level
        reason: Reason for this priority level
        hospitals: Recommended hospitals
        departments: Recommended departments
        doctors: Recommended doctors
        additional_notes: Additional recommendations
    """

    priority: Priority
    reason: str
    hospitals: List[Hospital] = field(default_factory=list)
    departments: List[Department] = field(default_factory=list)
    doctors: List[Doctor] = field(default_factory=list)
    additional_notes: List[str] = field(default_factory=list)

    def get_primary_hospital(self) -> Optional[Hospital]:
        """Get the primary (first) hospital recommendation."""
        return self.hospitals[0] if self.hospitals else None

    def get_primary_department(self) -> Optional[Department]:
        """Get the primary (first) department recommendation."""
        return self.departments[0] if self.departments else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "priority": self.priority.value,
            "reason": self.reason,
            "hospitals": [h.to_dict() for h in self.hospitals],
            "departments": [d.to_dict() for d in self.departments],
            "doctors": [d.to_dict() for d in self.doctors],
            "additional_notes": self.additional_notes,
        }
