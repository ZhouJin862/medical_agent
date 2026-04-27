"""
MessageReceived Domain Event - Raised when a new message is received.

This event can trigger:
- Message processing workflows
- Memory updates
- Analytics tracking
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class MessageReceived:
    """
    Domain event raised when a message is received in a consultation.

    Attributes:
        event_id: Unique event identifier
        occurred_at: When the event occurred
        consultation_id: Associated consultation ID
        message_id: ID of the received message
        patient_id: Patient/user ID
        message_content: Content of the message
        detected_intent: Detected intent for the message
    """

    event_id: str
    occurred_at: datetime
    consultation_id: str
    message_id: str
    patient_id: str
    message_content: str
    detected_intent: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": "message_received",
            "occurred_at": self.occurred_at.isoformat(),
            "consultation_id": self.consultation_id,
            "message_id": self.message_id,
            "patient_id": self.patient_id,
            "message_content": self.message_content,
            "detected_intent": self.detected_intent,
        }
