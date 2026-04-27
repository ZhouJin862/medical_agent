"""
Consultation Aggregate Root - Root of the consultation bounded context.

Manages:
- Conversation state
- Message lifecycle
- Intent tracking
- Domain events
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import uuid4

from .message import Message, MessageRole, MessageContent
from ..value_objects.consultation_status import (
    ConsultationStatus,
    ConsultationStatusEnum,
)
from ..events.message_received import MessageReceived
from ..events.conversation_completed import ConversationCompleted


@dataclass
class Consultation:
    """
    Aggregate root for a consultation session.

    A consultation represents a single health consultation session
    with a patient, containing all messages and state.

    Attributes:
        consultation_id: Unique consultation identifier
        patient_id: Patient/user identifier
        status: Current consultation status
        messages: List of messages in this consultation
        started_at: When the consultation started
        ended_at: When the consultation ended (if completed)
        _domain_events: Pending domain events to be published
    """

    consultation_id: str
    patient_id: str
    status: ConsultationStatus
    messages: List[Message] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    _domain_events: List[Any] = field(default_factory=list, repr=False)

    def add_message(self, message: Message) -> None:
        """
        Add a message to the consultation.

        Args:
            message: Message to add

        Raises:
            ValueError: If message cannot be added in current state
        """
        if not self.status.can_add_message():
            raise ValueError(
                f"Cannot add message to consultation in {self.status.status.value} state"
            )

        message.consultation_id = self.consultation_id
        self.messages.append(message)

        # Update status based on message role
        if message.is_from_user():
            self.status = self.status.transition_to(ConsultationStatusEnum.PROCESSING)

            # Raise domain event
            self._add_domain_event(
                MessageReceived(
                    event_id=f"msg_recv_{uuid4().hex[:8]}",
                    occurred_at=datetime.now(),
                    consultation_id=self.consultation_id,
                    message_id=message.message_id,
                    patient_id=self.patient_id,
                    message_content=message.content.text,
                    detected_intent=message.intent.value if message.intent else None,
                )
            )
        elif message.is_from_assistant():
            self.status = self.status.transition_to(
                ConsultationStatusEnum.WAITING_FOR_INPUT
            )

    def get_last_message(self) -> Optional[Message]:
        """Get the most recent message."""
        return self.messages[-1] if self.messages else None

    def get_last_n_messages(self, n: int) -> List[Message]:
        """Get the last n messages."""
        return self.messages[-n:] if n > 0 else []

    def get_messages_by_role(self, role: MessageRole) -> List[Message]:
        """Get all messages with a specific role."""
        return [m for m in self.messages if m.role == role]

    def complete(self, summary: Optional[str] = None) -> None:
        """
        Mark the consultation as completed.

        Args:
            summary: Optional summary of the consultation
        """
        if not self.status.is_active():
            raise ValueError(
                f"Cannot complete consultation in {self.status.status.value} state"
            )

        self.status = self.status.transition_to(ConsultationStatusEnum.COMPLETED)
        self.ended_at = datetime.now()

        # Calculate duration
        duration = int((self.ended_at - self.started_at).total_seconds())

        # Collect outcomes
        outcomes = self._collect_outcomes()

        # Raise domain event
        self._add_domain_event(
            ConversationCompleted(
                event_id=f"conv_complete_{uuid4().hex[:8]}",
                occurred_at=datetime.now(),
                consultation_id=self.consultation_id,
                patient_id=self.patient_id,
                message_count=len(self.messages),
                duration_seconds=duration,
                summary=summary,
                outcomes=outcomes,
            )
        )

    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Cancel the consultation.

        Args:
            reason: Optional reason for cancellation
        """
        self.status = self.status.transition_to(
            ConsultationStatusEnum.CANCELLED, reason
        )
        self.ended_at = datetime.now()

    def get_context_summary(self, max_messages: int = 10) -> str:
        """
        Get a summary of the consultation context.

        Args:
            max_messages: Maximum number of recent messages to include

        Returns:
            Summary string for context
        """
        recent_messages = self.get_last_n_messages(max_messages)

        summary_parts = [
            f"Consultation {self.consultation_id}",
            f"Status: {self.status.status.value}",
            f"Messages: {len(self.messages)}",
            "",
            "Recent messages:",
        ]

        for msg in recent_messages:
            role = msg.role.value
            content = msg.get_display_text()[:100]
            if len(msg.get_display_text()) > 100:
                content += "..."
            summary_parts.append(f"{role}: {content}")

        return "\n".join(summary_parts)

    def get_structured_outputs(self) -> List[Dict[str, Any]]:
        """
        Get all structured outputs from assistant messages.

        Returns:
            List of structured output dictionaries
        """
        return [
            msg.content.structured_data
            for msg in self.messages
            if msg.is_from_assistant() and msg.has_structured_output()
        ]

    def pull_domain_events(self) -> List[Any]:
        """
        Pull all pending domain events.

        Returns:
            List of domain events and clears the pending list
        """
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    def _add_domain_event(self, event: Any) -> None:
        """Add a domain event to the pending list."""
        self._domain_events.append(event)

    def _collect_outcomes(self) -> List[str]:
        """Collect outcomes from the consultation."""
        outcomes = []

        # Check for health assessment
        if any(
            msg.intent.value == "health_assessment"
            for msg in self.messages
            if msg.intent
        ):
            outcomes.append("health_assessment_completed")

        # Check for risk prediction
        if any(
            msg.intent.value == "risk_prediction"
            for msg in self.messages
            if msg.intent
        ):
            outcomes.append("risk_prediction_completed")

        # Check for health plan
        if any(
            msg.intent.value == "health_plan"
            for msg in self.messages
            if msg.intent
        ):
            outcomes.append("health_plan_generated")

        return outcomes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "consultation_id": self.consultation_id,
            "patient_id": self.patient_id,
            "status": self.status.status.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "message_count": len(self.messages),
            "messages": [msg.to_dict() for msg in self.messages],
        }


def create_consulation(patient_id: str) -> Consultation:
    """
    Create a new consultation.

    Args:
        patient_id: Patient/user identifier

    Returns:
        New Consultation instance
    """
    return Consultation(
        consultation_id=f"consult_{uuid4().hex[:12]}",
        patient_id=patient_id,
        status=ConsultationStatus(ConsultationStatusEnum.CREATED),
    )
