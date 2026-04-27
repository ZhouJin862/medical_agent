"""
Message Entity - Represents a single message in a consultation.

A message can be from the user or the assistant, and may contain
structured metadata from skill execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict


class MessageRole(Enum):
    """Role of the message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(Enum):
    """Intent types for messages."""

    UNKNOWN = "unknown"
    HEALTH_ASSESSMENT = "health_assessment"
    RISK_PREDICTION = "risk_prediction"
    HEALTH_PLAN = "health_plan"
    TRIAGE = "triage"
    MEDICATION_CHECK = "medication_check"
    SERVICE_RECOMMENDATION = "service_recommendation"
    GENERAL_CHAT = "general_chat"


@dataclass
class MessageContent:
    """
    Content of a message.

    Attributes:
        text: Plain text content
        structured_data: Optional structured data from skills
        metadata: Additional metadata
    """

    text: str
    structured_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """
    Message entity in a consultation.

    Attributes:
        message_id: Unique message identifier
        role: Role of the sender
        content: Message content
        intent: Detected intent (for user messages)
        timestamp: When the message was created
        consultation_id: Parent consultation ID
    """

    message_id: str
    role: MessageRole
    content: MessageContent
    timestamp: datetime = field(default_factory=datetime.now)
    consultation_id: Optional[str] = None
    intent: Optional[IntentType] = None
    confidence: float = 0.0

    def is_from_user(self) -> bool:
        """Check if message is from user."""
        return self.role == MessageRole.USER

    def is_from_assistant(self) -> bool:
        """Check if message is from assistant."""
        return self.role == MessageRole.ASSISTANT

    def has_structured_output(self) -> bool:
        """Check if message has structured data."""
        return (
            self.content.structured_data is not None
            and len(self.content.structured_data) > 0
        )

    def get_display_text(self) -> str:
        """Get text suitable for display."""
        return self.content.text

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": {
                "text": self.content.text,
                "structured_data": self.content.structured_data,
                "metadata": self.content.metadata,
            },
            "intent": self.intent.value if self.intent else None,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "consultation_id": self.consultation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create Message from dictionary."""
        content_data = data.get("content", {})
        content = MessageContent(
            text=content_data.get("text", ""),
            structured_data=content_data.get("structured_data"),
            metadata=content_data.get("metadata", {}),
        )

        return cls(
            message_id=data["message_id"],
            role=MessageRole(data["role"]),
            content=content,
            intent=IntentType(data["intent"]) if data.get("intent") else None,
            confidence=data.get("confidence", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            consultation_id=data.get("consultation_id"),
        )
