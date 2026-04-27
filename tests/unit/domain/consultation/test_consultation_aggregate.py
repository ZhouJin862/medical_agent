"""
Unit tests for Consultation aggregate root.

Tests for:
- Creating a new consultation (create_consultation)
- Adding messages (add_message)
- Updating status (update_status/complete/cancel)
- Intent recognition context
- Domain event publishing (MessageReceived, ConversationCompleted)
- Message retrieval methods
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

from src.domain.consultation.entities.consultation import (
    Consultation,
    create_consulation,
)
from src.domain.consultation.entities.message import (
    Message,
    MessageRole,
    MessageContent,
    IntentType,
)
from src.domain.consultation.value_objects.consultation_status import (
    ConsultationStatus,
    ConsultationStatusEnum,
)
from src.domain.consultation.events.message_received import MessageReceived
from src.domain.consultation.events.conversation_completed import ConversationCompleted


# ===== Fixtures =====


@pytest.fixture
def sample_patient_id():
    """Sample patient ID."""
    return "patient_12345"


@pytest.fixture
def sample_consultation_id():
    """Sample consultation ID."""
    return f"consult_{uuid4().hex[:12]}"


@pytest.fixture
def sample_consultation(sample_patient_id):
    """Create a sample consultation."""
    status = ConsultationStatus(ConsultationStatusEnum.CREATED)
    return Consultation(
        consultation_id=f"consult_{uuid4().hex[:12]}",
        patient_id=sample_patient_id,
        status=status,
    )


@pytest.fixture
def sample_user_message():
    """Create a sample user message."""
    return Message(
        message_id=f"msg_{uuid4().hex[:12]}",
        role=MessageRole.USER,
        content=MessageContent(text="I have a headache"),
    )


@pytest.fixture
def sample_assistant_message():
    """Create a sample assistant message."""
    return Message(
        message_id=f"msg_{uuid4().hex[:12]}",
        role=MessageRole.ASSISTANT,
        content=MessageContent(text="I can help with that"),
    )


@pytest.fixture
def sample_structured_message():
    """Create a message with structured output."""
    content = MessageContent(
        text="Health assessment complete",
        structured_data={
            "health_score": 75,
            "risk_factors": ["hypertension", "obesity"]
        }
    )
    return Message(
        message_id=f"msg_{uuid4().hex[:12]}",
        role=MessageRole.ASSISTANT,
        content=content,
    )


# ===== Consultation Creation Tests =====


class TestConsultationCreation:
    """Tests for creating consultations."""

    def test_create_consultation_with_minimal_args(self):
        """Test creating a consultation with minimal arguments."""
        consultation_id = f"consult_{uuid4().hex[:12]}"
        patient_id = "patient_123"
        status = ConsultationStatus(ConsultationStatusEnum.CREATED)

        consultation = Consultation(
            consultation_id=consultation_id,
            patient_id=patient_id,
            status=status,
        )

        assert consultation.consultation_id == consultation_id
        assert consultation.patient_id == patient_id
        assert consultation.status.status == ConsultationStatusEnum.CREATED
        assert len(consultation.messages) == 0
        assert consultation.ended_at is None
        assert len(consultation.pull_domain_events()) == 0

    def test_create_consultation_with_messages(self):
        """Test creating a consultation with initial messages."""
        messages = [
            Message(
                message_id=f"msg_{uuid4().hex[:12]}",
                role=MessageRole.USER,
                content=MessageContent(text="Hello"),
            )
        ]
        consultation = Consultation(
            consultation_id=f"consult_{uuid4().hex[:12]}",
            patient_id="patient_123",
            status=ConsultationStatus(ConsultationStatusEnum.CREATED),
            messages=messages,
        )

        assert len(consultation.messages) == 1
        assert consultation.messages[0].content.text == "Hello"

    def test_factory_function_create_consultation(self, sample_patient_id):
        """Test the factory function for creating consultations."""
        consultation = create_consulation(sample_patient_id)

        assert consultation.patient_id == sample_patient_id
        assert consultation.status.status == ConsultationStatusEnum.CREATED
        assert consultation.consultation_id.startswith("consult_")
        assert consultation.started_at is not None
        assert len(consultation.messages) == 0


# ===== Message Management Tests =====


class TestMessageManagement:
    """Tests for adding and managing messages."""

    def test_add_user_message_in_created_state(
        self, sample_consultation, sample_user_message
    ):
        """Test adding a user message when consultation is in CREATED state."""
        sample_consultation.add_message(sample_user_message)

        assert len(sample_consultation.messages) == 1
        assert sample_consultation.messages[0] == sample_user_message
        assert sample_consultation.messages[0].consultation_id == sample_consultation.consultation_id
        assert sample_consultation.status.status == ConsultationStatusEnum.PROCESSING

    def test_add_user_message_raises_message_received_event(
        self, sample_consultation, sample_user_message
    ):
        """Test that adding a user message raises MessageReceived event."""
        sample_consultation.add_message(sample_user_message)

        events = sample_consultation.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], MessageReceived)
        assert events[0].consultation_id == sample_consultation.consultation_id
        assert events[0].patient_id == sample_consultation.patient_id

    def test_add_assistant_message_changes_status(
        self, sample_consultation, sample_assistant_message
    ):
        """Test adding an assistant message changes status to WAITING_FOR_INPUT."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.PROCESSING)
        sample_consultation.add_message(sample_assistant_message)

        assert sample_consultation.status.status == ConsultationStatusEnum.WAITING_FOR_INPUT

    def test_add_message_to_completed_consultation_fails(
        self, sample_consultation, sample_user_message
    ):
        """Test that adding a message to a completed consultation fails."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.COMPLETED)

        with pytest.raises(ValueError, match="Cannot add message"):
            sample_consultation.add_message(sample_user_message)

    def test_add_message_to_cancelled_consultation_fails(
        self, sample_consultation, sample_user_message
    ):
        """Test that adding a message to a cancelled consultation fails."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.CANCELLED)

        with pytest.raises(ValueError, match="Cannot add message"):
            sample_consultation.add_message(sample_user_message)

    def test_add_multiple_messages(self, sample_consultation):
        """Test adding multiple messages in sequence."""
        user_msg = Message(
            message_id=f"msg_{uuid4().hex[:12]}",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        assistant_msg = Message(
            message_id=f"msg_{uuid4().hex[:12]}",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Hi there"),
        )

        sample_consultation.add_message(user_msg)
        sample_consultation.add_message(assistant_msg)

        assert len(sample_consultation.messages) == 2


# ===== Message Retrieval Tests =====


class TestMessageRetrieval:
    """Tests for retrieving messages."""

    def test_get_last_message_returns_most_recent(self, sample_consultation):
        """Test get_last_message returns the most recent message."""
        msg1 = Message(
            message_id=f"msg_{uuid4().hex[:12]}",
            role=MessageRole.USER,
            content=MessageContent(text="First"),
        )
        msg2 = Message(
            message_id=f"msg_{uuid4().hex[:12]}",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Second"),
        )

        sample_consultation.add_message(msg1)
        sample_consultation.add_message(msg2)

        last = sample_consultation.get_last_message()
        assert last == msg2

    def test_get_last_message_returns_none_when_empty(self, sample_consultation):
        """Test get_last_message returns None when no messages."""
        assert sample_consultation.get_last_message() is None

    def test_get_last_n_messages(self, sample_consultation):
        """Test getting the last n messages."""
        for i in range(5):
            msg = Message(
                message_id=f"msg_{i}",
                role=MessageRole.USER,
                content=MessageContent(text=f"Message {i}"),
            )
            sample_consultation.add_message(msg)

        last_3 = sample_consultation.get_last_n_messages(3)
        assert len(last_3) == 3
        assert last_3[0].content.text == "Message 2"

    def test_get_last_n_messages_with_zero_returns_empty(self, sample_consultation):
        """Test get_last_n_messages with n=0 returns empty list."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text="Test"),
        )
        sample_consultation.add_message(msg)

        result = sample_consultation.get_last_n_messages(0)
        assert result == []

    def test_get_last_n_messages_exceeds_count(self, sample_consultation):
        """Test get_last_n_messages when n exceeds message count."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text="Test"),
        )
        sample_consultation.add_message(msg)

        result = sample_consultation.get_last_n_messages(10)
        assert len(result) == 1

    def test_get_messages_by_role(self, sample_consultation):
        """Test filtering messages by role."""
        user_msg1 = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text="User 1"),
        )
        assistant_msg = Message(
            message_id="msg_2",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Assistant"),
        )
        user_msg2 = Message(
            message_id="msg_3",
            role=MessageRole.USER,
            content=MessageContent(text="User 2"),
        )

        sample_consultation.add_message(user_msg1)
        sample_consultation.add_message(assistant_msg)
        sample_consultation.add_message(user_msg2)

        user_messages = sample_consultation.get_messages_by_role(MessageRole.USER)
        assistant_messages = sample_consultation.get_messages_by_role(MessageRole.ASSISTANT)

        assert len(user_messages) == 2
        assert len(assistant_messages) == 1


# ===== Consultation Completion Tests =====


class TestConsultationCompletion:
    """Tests for completing consultations."""

    def test_complete_consultation(self, sample_consultation):
        """Test marking a consultation as completed."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)

        sample_consultation.complete(summary="Consultation finished")

        assert sample_consultation.status.status == ConsultationStatusEnum.COMPLETED
        assert sample_consultation.ended_at is not None

    def test_complete_consultation_raises_conversation_completed_event(
        self, sample_consultation
    ):
        """Test completing raises ConversationCompleted event."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)
        sample_consultation.complete(summary="Done")

        events = sample_consultation.pull_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], ConversationCompleted)
        assert events[0].consultation_id == sample_consultation.consultation_id
        assert events[0].summary == "Done"

    def test_complete_consultation_calculates_duration(self, sample_consultation):
        """Test completion calculates duration correctly."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)
        # Manually set started_at to a known time
        past_time = datetime.now() - timedelta(seconds=120)
        sample_consultation.started_at = past_time

        sample_consultation.complete()

        events = sample_consultation.pull_domain_events()
        assert events[0].duration_seconds >= 118  # Allow some time for execution

    def test_complete_consultation_with_summary(self, sample_consultation):
        """Test completing with a summary."""
        summary = "Patient diagnosed with hypertension"
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)

        sample_consultation.complete(summary=summary)

        events = sample_consultation.pull_domain_events()
        assert events[0].summary == summary

    def test_complete_inactive_consultation_fails(self, sample_consultation):
        """Test completing an already completed consultation fails."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.COMPLETED)

        with pytest.raises(ValueError, match="Cannot complete consultation"):
            sample_consultation.complete()

    def test_complete_cancelled_consultation_fails(self, sample_consultation):
        """Test completing a cancelled consultation fails."""
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.CANCELLED)

        with pytest.raises(ValueError, match="Cannot complete consultation"):
            sample_consultation.complete()


# ===== Consultation Cancellation Tests =====


class TestConsultationCancellation:
    """Tests for cancelling consultations."""

    def test_cancel_consultation(self, sample_consultation):
        """Test cancelling a consultation."""
        sample_consultation.cancel(reason="Patient left")

        assert sample_consultation.status.status == ConsultationStatusEnum.CANCELLED
        assert sample_consultation.ended_at is not None

    def test_cancel_with_reason(self, sample_consultation):
        """Test cancelling with a reason."""
        reason = "No longer needed"
        sample_consultation.cancel(reason=reason)

        assert sample_consultation.status.status == ConsultationStatusEnum.CANCELLED


# ===== Context Summary Tests =====


class TestContextSummary:
    """Tests for getting consultation context summary."""

    def test_get_context_summary_with_messages(self, sample_consultation):
        """Test getting context summary with recent messages."""
        user_msg = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text="I have a headache and fever"),
        )
        sample_consultation.add_message(user_msg)

        summary = sample_consultation.get_context_summary(max_messages=5)

        assert "Consultation" in summary
        assert sample_consultation.consultation_id in summary
        assert "Messages: 1" in summary
        assert "headache" in summary

    def test_get_context_summary_limits_messages(self, sample_consultation):
        """Test get_context_summary limits number of messages."""
        for i in range(10):
            msg = Message(
                message_id=f"msg_{i}",
                role=MessageRole.USER,
                content=MessageContent(text=f"Message {i}"),
            )
            sample_consultation.add_message(msg)

        summary = sample_consultation.get_context_summary(max_messages=3)

        # Should only include last 3 messages
        assert "Message 7" in summary
        assert "Message 9" in summary
        assert "Message 0" not in summary

    def test_get_context_summary_truncates_long_content(self, sample_consultation):
        """Test long content is truncated in summary."""
        long_text = "A" * 200
        msg = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text=long_text),
        )
        sample_consultation.add_message(msg)

        summary = sample_consultation.get_context_summary()

        assert "..." in summary  # Content was truncated


# ===== Structured Output Tests =====


class TestStructuredOutputs:
    """Tests for retrieving structured outputs."""

    def test_get_structured_outputs_from_assistant_messages(
        self, sample_consultation, sample_structured_message
    ):
        """Test getting structured outputs from assistant messages."""
        sample_consultation.add_message(sample_structured_message)

        outputs = sample_consultation.get_structured_outputs()

        assert len(outputs) == 1
        assert outputs[0]["health_score"] == 75
        assert "risk_factors" in outputs[0]

    def test_get_structured_outputs_ignores_user_messages(
        self, sample_consultation, sample_user_message
    ):
        """Test user messages are ignored in structured outputs."""
        content = MessageContent(
            text="Data",
            structured_data={"key": "value"}
        )
        user_msg_with_structured = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=content,
        )
        sample_consultation.add_message(user_msg_with_structured)

        outputs = sample_consultation.get_structured_outputs()

        assert len(outputs) == 0

    def test_get_structured_outputs_ignores_messages_without_structure(
        self, sample_consultation, sample_assistant_message
    ):
        """Test messages without structured data are ignored."""
        sample_consultation.add_message(sample_assistant_message)

        outputs = sample_consultation.get_structured_outputs()

        assert len(outputs) == 0


# ===== Domain Events Tests =====


class TestDomainEvents:
    """Tests for domain event handling."""

    def test_pull_domain_events_clears_pending_events(
        self, sample_consultation, sample_user_message
    ):
        """Test pull_domain_events clears the pending events list."""
        sample_consultation.add_message(sample_user_message)

        events = sample_consultation.pull_domain_events()
        assert len(events) == 1

        # Second pull should return empty
        more_events = sample_consultation.pull_domain_events()
        assert len(more_events) == 0

    def test_multiple_user_messages_generate_multiple_events(
        self, sample_consultation
    ):
        """Test multiple user messages generate multiple events."""
        for i in range(3):
            msg = Message(
                message_id=f"msg_{i}",
                role=MessageRole.USER,
                content=MessageContent(text=f"Message {i}"),
            )
            sample_consultation.add_message(msg)

        events = sample_consultation.pull_domain_events()
        assert len(events) == 3
        assert all(isinstance(e, MessageReceived) for e in events)


# ===== Dictionary Conversion Tests =====


class TestDictionaryConversion:
    """Tests for converting to dictionary."""

    def test_to_dict_includes_all_fields(self, sample_consultation):
        """Test to_dict includes all relevant fields."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text="Test"),
        )
        sample_consultation.add_message(msg)

        result = sample_consultation.to_dict()

        assert result["consultation_id"] == sample_consultation.consultation_id
        assert result["patient_id"] == sample_consultation.patient_id
        assert result["status"] == "processing"  # Status changes after adding user message
        assert result["message_count"] == 1
        assert "started_at" in result
        assert result["ended_at"] is None

    def test_to_dict_includes_messages(self, sample_consultation):
        """Test to_dict includes message list."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        sample_consultation.add_message(msg)

        result = sample_consultation.to_dict()

        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"]["text"] == "Hello"


# ===== Outcome Collection Tests =====


class TestOutcomeCollection:
    """Tests for _collect_outcomes method."""

    def test_collect_outcomes_detects_health_assessment(self, sample_consultation):
        """Test outcome collection detects health assessment intent."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Assessment done"),
            intent=IntentType("health_assessment"),
        )
        sample_consultation.add_message(msg)

        # Complete to trigger outcome collection
        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)
        sample_consultation.complete()

        events = sample_consultation.pull_domain_events()
        assert "health_assessment_completed" in events[0].outcomes

    def test_collect_outcomes_detects_risk_prediction(self, sample_consultation):
        """Test outcome collection detects risk prediction intent."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Risk calculated"),
            intent=IntentType("risk_prediction"),
        )
        sample_consultation.add_message(msg)

        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)
        sample_consultation.complete()

        events = sample_consultation.pull_domain_events()
        assert "risk_prediction_completed" in events[0].outcomes

    def test_collect_outcomes_detects_health_plan(self, sample_consultation):
        """Test outcome collection detects health plan intent."""
        msg = Message(
            message_id="msg_1",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Plan generated"),
            intent=IntentType("health_plan"),
        )
        sample_consultation.add_message(msg)

        sample_consultation.status = ConsultationStatus(ConsultationStatusEnum.WAITING_FOR_INPUT)
        sample_consultation.complete()

        events = sample_consultation.pull_domain_events()
        assert "health_plan_generated" in events[0].outcomes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
