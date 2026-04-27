"""
ConversationCompleted Domain Event - Raised when a consultation completes.

This event can trigger:
- Health plan generation
- Summary generation
- Analytics updates
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ConversationCompleted:
    """
    Domain event raised when a consultation is completed.

    Attributes:
        event_id: Unique event identifier
        occurred_at: When the event occurred
        consultation_id: Associated consultation ID
        patient_id: Patient/user ID
        message_count: Number of messages in the conversation
        duration_seconds: Duration of the consultation
        summary: Optional summary of the consultation
        outcomes: List of outcomes from the consultation
    """

    event_id: str
    occurred_at: datetime
    consultation_id: str
    patient_id: str
    message_count: int
    duration_seconds: int
    summary: str | None = None
    outcomes: List[str] | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": "conversation_completed",
            "occurred_at": self.occurred_at.isoformat(),
            "consultation_id": self.consultation_id,
            "patient_id": self.patient_id,
            "message_count": self.message_count,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "outcomes": self.outcomes or [],
        }
