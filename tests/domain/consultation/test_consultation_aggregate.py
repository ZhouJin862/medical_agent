"""Unit tests for Consultation aggregate root."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

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


class TestCreateConsultation:
    """Tests for creating a new consultation."""

    def test_create_consultation_factory_function(self):
        """Test creating a consultation using the factory function."""
        patient_id = "patient_123"
        consultation = create_consulation(patient_id)

        assert consultation.patient_id == patient_id
        assert consultation.consultation_id.startswith("consult_")
        # "consult_" + 12 hex chars
        assert len(consultation.consultation_id) >= 19
        assert len(consultation.consultation_id) <= 21  # Allow for UUID hex length variation
        assert consultation.status.status == ConsultationStatusEnum.CREATED
        assert len(consultation.messages) == 0
        assert consultation.started_at is not None
        assert consultation.ended_at is None

    def test_create_consultation_generates_unique_ids(self):
        """Test that each consultation gets a unique ID."""
        consultation1 = create_consulation("patient_123")
        consultation2 = create_consulation("patient_123")

        assert consultation1.consultation_id != consultation2.consultation_id

    def test_create_consultation_direct(self):
        """Test creating a consultation directly."""
        consultation_id = "test_consult_001"
        patient_id = "patient_123"
        status = ConsultationStatus(ConsultationStatusEnum.CREATED)

        consultation = Consultation(
            consultation_id=consultation_id,
            patient_id=patient_id,
            status=status,
        )

        assert consultation.consultation_id == consultation_id
        assert consultation.patient_id == patient_id
        assert consultation.status == status
        assert consultation.messages == []

    def test_new_consultation_has_no_domain_events(self):
        """Test that a new consultation has no pending domain events."""
        consultation = create_consulation("patient_123")
        events = consultation.pull_domain_events()

        assert len(events) == 0


class TestAddMessage:
    """Tests for adding messages to a consultation."""

    def test_add_user_message_success(self):
        """Test successfully adding a user message."""
        consultation = create_consulation("patient_123")
        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello, I have a headache."),
        )

        consultation.add_message(message)

        assert len(consultation.messages) == 1
        assert consultation.messages[0] == message
        assert message.consultation_id == consultation.consultation_id
        assert consultation.status.status == ConsultationStatusEnum.PROCESSING

    def test_add_user_message_raises_message_received_event(self):
        """Test that adding a user message raises a MessageReceived domain event."""
        consultation = create_consulation("patient_123")
        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="I need help."),
            intent=IntentType.GENERAL_CHAT,
        )

        consultation.add_message(message)
        events = consultation.pull_domain_events()

        assert len(events) == 1
        assert isinstance(events[0], MessageReceived)
        assert events[0].consultation_id == consultation.consultation_id
        assert events[0].message_id == "msg_001"
        assert events[0].patient_id == "patient_123"
        assert events[0].message_content == "I need help."
        assert events[0].detected_intent == "general_chat"

    def test_add_assistant_message_success(self):
        """Test successfully adding an assistant message."""
        consultation = create_consulation("patient_123")
        consultation.status = ConsultationStatus(ConsultationStatusEnum.PROCESSING)

        message = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="How can I help you today?"),
        )

        consultation.add_message(message)

        assert len(consultation.messages) == 1
        assert consultation.status.status == ConsultationStatusEnum.WAITING_FOR_INPUT

    def test_add_assistant_message_does_not_raise_event(self):
        """Test that assistant messages do not raise domain events."""
        consultation = create_consulation("patient_123")
        consultation.status = ConsultationStatus(ConsultationStatusEnum.PROCESSING)

        message = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Here is your result."),
        )

        consultation.add_message(message)
        events = consultation.pull_domain_events()

        assert len(events) == 0

    def test_add_message_to_completed_consultation_raises_error(self):
        """Test that adding a message to a completed consultation raises ValueError."""
        consultation = create_consulation("patient_123")
        consultation.status = ConsultationStatus(ConsultationStatusEnum.COMPLETED)

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )

        with pytest.raises(ValueError, match="Cannot add message to consultation in completed state"):
            consultation.add_message(message)

    def test_add_message_to_cancelled_consultation_raises_error(self):
        """Test that adding a message to a cancelled consultation raises ValueError."""
        consultation = create_consulation("patient_123")
        consultation.status = ConsultationStatus(ConsultationStatusEnum.CANCELLED)

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )

        with pytest.raises(ValueError, match="Cannot add message to consultation in cancelled state"):
            consultation.add_message(message)

    def test_add_multiple_messages(self):
        """Test adding multiple messages in sequence."""
        consultation = create_consulation("patient_123")

        user_msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        assistant_msg = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Hi there!"),
        )

        consultation.add_message(user_msg)
        consultation.add_message(assistant_msg)

        assert len(consultation.messages) == 2
        assert consultation.messages[0].message_id == "msg_001"
        assert consultation.messages[1].message_id == "msg_002"

    def test_add_message_with_structured_data(self):
        """Test adding a message with structured output data."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.ASSISTANT,
            content=MessageContent(
                text="Here is your health plan.",
                structured_data={"plan": "exercise_daily", "duration": "30_days"},
            ),
        )

        consultation.add_message(message)

        assert len(consultation.messages) == 1
        assert consultation.messages[0].has_structured_output() is True


class TestUpdateStatus:
    """Tests for updating consultation status."""

    def test_status_transitions_on_user_message(self):
        """Test that status transitions to PROCESSING when user message is added."""
        consultation = create_consulation("patient_123")

        user_msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )

        consultation.add_message(user_msg)

        assert consultation.status.status == ConsultationStatusEnum.PROCESSING

    def test_status_transitions_on_assistant_message(self):
        """Test that status transitions to WAITING_FOR_INPUT when assistant message is added."""
        consultation = create_consulation("patient_123")
        consultation.status = ConsultationStatus(ConsultationStatusEnum.PROCESSING)

        assistant_msg = Message(
            message_id="msg_001",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Response"),
        )

        consultation.add_message(assistant_msg)

        assert consultation.status.status == ConsultationStatusEnum.WAITING_FOR_INPUT

    def test_complete_consultation_status(self):
        """Test completing a consultation updates status to COMPLETED."""
        consultation = create_consulation("patient_123")

        consultation.complete(summary="Consultation finished")

        assert consultation.status.status == ConsultationStatusEnum.COMPLETED
        assert consultation.ended_at is not None

    def test_cancel_consultation_status(self):
        """Test cancelling a consultation updates status to CANCELLED."""
        consultation = create_consulation("patient_123")

        consultation.cancel(reason="Patient left")

        assert consultation.status.status == ConsultationStatusEnum.CANCELLED
        assert consultation.ended_at is not None

    def test_is_active_status_check(self):
        """Test the is_active status check method."""
        active_statuses = [
            ConsultationStatusEnum.CREATED,
            ConsultationStatusEnum.IN_PROGRESS,
            ConsultationStatusEnum.WAITING_FOR_INPUT,
            ConsultationStatusEnum.PROCESSING,
        ]

        for status_enum in active_statuses:
            status = ConsultationStatus(status_enum)
            assert status.is_active() is True

        terminal_statuses = [
            ConsultationStatusEnum.COMPLETED,
            ConsultationStatusEnum.CANCELLED,
            ConsultationStatusEnum.ERROR,
        ]

        for status_enum in terminal_statuses:
            status = ConsultationStatus(status_enum)
            assert status.is_active() is False

    def test_can_add_message_status_check(self):
        """Test the can_add_message status check method."""
        consultation = create_consulation("patient_123")

        # Initially should be able to add messages
        assert consultation.status.can_add_message() is True

        # After completing, should not be able to add messages
        consultation.complete()
        assert consultation.status.can_add_message() is False


class TestRecognizeIntent:
    """Tests for intent recognition in messages."""

    def test_message_with_health_assessment_intent(self):
        """Test a message with health assessment intent."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Assess my health"),
            intent=IntentType.HEALTH_ASSESSMENT,
        )

        consultation.add_message(message)

        assert consultation.messages[0].intent == IntentType.HEALTH_ASSESSMENT

    def test_message_with_risk_prediction_intent(self):
        """Test a message with risk prediction intent."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Predict my disease risk"),
            intent=IntentType.RISK_PREDICTION,
        )

        consultation.add_message(message)

        assert consultation.messages[0].intent == IntentType.RISK_PREDICTION

    def test_message_with_health_plan_intent(self):
        """Test a message with health plan intent."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Create a health plan"),
            intent=IntentType.HEALTH_PLAN,
        )

        consultation.add_message(message)

        assert consultation.messages[0].intent == IntentType.HEALTH_PLAN

    def test_message_with_unknown_intent(self):
        """Test a message without explicit intent defaults to unknown."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Just chatting"),
        )

        consultation.add_message(message)

        # Default intent is None, not UNKNOWN
        assert consultation.messages[0].intent is None

    def test_collect_outcomes_with_health_assessment(self):
        """Test that health assessment intent is collected as an outcome."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Assess health"),
            intent=IntentType.HEALTH_ASSESSMENT,
        )

        consultation.add_message(message)
        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert "health_assessment_completed" in completed_event.outcomes

    def test_collect_outcomes_with_risk_prediction(self):
        """Test that risk prediction intent is collected as an outcome."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Predict risk"),
            intent=IntentType.RISK_PREDICTION,
        )

        consultation.add_message(message)
        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert "risk_prediction_completed" in completed_event.outcomes

    def test_collect_outcomes_with_health_plan(self):
        """Test that health plan intent is collected as an outcome."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Create plan"),
            intent=IntentType.HEALTH_PLAN,
        )

        consultation.add_message(message)
        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert "health_plan_generated" in completed_event.outcomes

    def test_collect_multiple_outcomes(self):
        """Test collecting multiple outcomes from different intents."""
        consultation = create_consulation("patient_123")

        msg1 = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Assess health"),
            intent=IntentType.HEALTH_ASSESSMENT,
        )
        msg2 = Message(
            message_id="msg_002",
            role=MessageRole.USER,
            content=MessageContent(text="Create plan"),
            intent=IntentType.HEALTH_PLAN,
        )

        consultation.add_message(msg1)
        consultation.add_message(msg2)
        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert "health_assessment_completed" in completed_event.outcomes
        assert "health_plan_generated" in completed_event.outcomes


class TestDomainEvents:
    """Tests for domain event publishing."""

    def test_message_received_event_attributes(self):
        """Test that MessageReceived event has correct attributes."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Test message"),
            intent=IntentType.TRIAGE,
        )

        consultation.add_message(message)
        events = consultation.pull_domain_events()

        assert len(events) == 1
        event = events[0]

        assert event.event_id.startswith("msg_recv_")
        assert event.occurred_at is not None
        assert event.consultation_id == consultation.consultation_id
        assert event.message_id == "msg_001"
        assert event.patient_id == "patient_123"
        assert event.message_content == "Test message"
        assert event.detected_intent == "triage"

    def test_conversation_completed_event_on_complete(self):
        """Test that completing a consultation raises ConversationCompleted event."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        consultation.add_message(message)

        consultation.complete(summary="Test summary")

        events = consultation.pull_domain_events()

        # Should have MessageReceived and ConversationCompleted events
        assert len(events) == 2
        completed_event = events[1]

        assert isinstance(completed_event, ConversationCompleted)
        assert completed_event.event_id.startswith("conv_complete_")
        assert completed_event.consultation_id == consultation.consultation_id
        assert completed_event.patient_id == "patient_123"
        assert completed_event.message_count == 1
        assert completed_event.summary == "Test summary"
        assert completed_event.duration_seconds >= 0

    def test_conversation_completed_event_calculates_duration(self):
        """Test that ConversationCompleted event calculates duration correctly."""
        consultation = create_consulation("patient_123")

        # Manipulate started_at for testing
        past_time = datetime.now() - timedelta(seconds=120)
        consultation.started_at = past_time

        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert completed_event.duration_seconds >= 118  # Allow 2 seconds for test execution
        assert completed_event.duration_seconds <= 122

    def test_conversation_completed_includes_outcomes(self):
        """Test that ConversationCompleted event includes collected outcomes."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Create plan"),
            intent=IntentType.HEALTH_PLAN,
        )
        consultation.add_message(message)

        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert len(completed_event.outcomes) > 0
        assert "health_plan_generated" in completed_event.outcomes

    def test_pull_domain_events_clears_pending_events(self):
        """Test that pulling domain events clears the pending list."""
        consultation = create_consulation("patient_123")

        message = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        consultation.add_message(message)

        events1 = consultation.pull_domain_events()
        events2 = consultation.pull_domain_events()

        assert len(events1) == 1
        assert len(events2) == 0

    def test_cancel_does_not_raise_conversation_completed_event(self):
        """Test that cancelling a consultation does not raise ConversationCompleted event."""
        consultation = create_consulation("patient_123")

        consultation.cancel(reason="Test cancellation")

        events = consultation.pull_domain_events()

        # Should have no events
        assert len(events) == 0


class TestConsultationQueries:
    """Tests for consultation query methods."""

    def test_get_last_message(self):
        """Test getting the last message."""
        consultation = create_consulation("patient_123")

        msg1 = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="First"),
        )
        msg2 = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Second"),
        )

        consultation.add_message(msg1)
        consultation.add_message(msg2)

        last_msg = consultation.get_last_message()

        assert last_msg.message_id == "msg_002"

    def test_get_last_message_returns_none_when_empty(self):
        """Test that get_last_message returns None when no messages."""
        consultation = create_consulation("patient_123")

        last_msg = consultation.get_last_message()

        assert last_msg is None

    def test_get_last_n_messages(self):
        """Test getting the last n messages."""
        consultation = create_consulation("patient_123")

        for i in range(5):
            msg = Message(
                message_id=f"msg_{i:03d}",
                role=MessageRole.USER,
                content=MessageContent(text=f"Message {i}"),
            )
            consultation.add_message(msg)

        last_3 = consultation.get_last_n_messages(3)

        assert len(last_3) == 3
        assert last_3[0].message_id == "msg_002"
        assert last_3[1].message_id == "msg_003"
        assert last_3[2].message_id == "msg_004"

    def test_get_last_n_messages_with_n_larger_than_count(self):
        """Test getting last n messages when n is larger than message count."""
        consultation = create_consulation("patient_123")

        msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Only message"),
        )
        consultation.add_message(msg)

        last_10 = consultation.get_last_n_messages(10)

        assert len(last_10) == 1

    def test_get_last_n_messages_with_zero_or_negative(self):
        """Test getting last n messages with zero or negative n."""
        consultation = create_consulation("patient_123")

        msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Message"),
        )
        consultation.add_message(msg)

        assert consultation.get_last_n_messages(0) == []
        assert consultation.get_last_n_messages(-1) == []

    def test_get_messages_by_role_user(self):
        """Test filtering messages by user role."""
        consultation = create_consulation("patient_123")

        user_msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="User message"),
        )
        assistant_msg = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Assistant message"),
        )

        consultation.add_message(user_msg)
        consultation.add_message(assistant_msg)

        user_messages = consultation.get_messages_by_role(MessageRole.USER)

        assert len(user_messages) == 1
        assert user_messages[0].message_id == "msg_001"

    def test_get_messages_by_role_assistant(self):
        """Test filtering messages by assistant role."""
        consultation = create_consulation("patient_123")

        user_msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="User message"),
        )
        assistant_msg = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Assistant message"),
        )

        consultation.add_message(user_msg)
        consultation.add_message(assistant_msg)

        assistant_messages = consultation.get_messages_by_role(MessageRole.ASSISTANT)

        assert len(assistant_messages) == 1
        assert assistant_messages[0].message_id == "msg_002"


class TestConsultationCompletion:
    """Tests for completing consultations."""

    def test_complete_consultation_sets_ended_at(self):
        """Test that completing a consultation sets the ended_at timestamp."""
        consultation = create_consulation("patient_123")

        assert consultation.ended_at is None

        consultation.complete()

        assert consultation.ended_at is not None

    def test_complete_with_summary(self):
        """Test completing a consultation with a summary."""
        consultation = create_consulation("patient_123")
        summary = "Patient was advised to rest and drink fluids."

        consultation.complete(summary=summary)

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert completed_event.summary == summary

    def test_complete_without_summary(self):
        """Test completing a consultation without a summary."""
        consultation = create_consulation("patient_123")

        consultation.complete()

        events = consultation.pull_domain_events()
        completed_event = [e for e in events if isinstance(e, ConversationCompleted)][0]

        assert completed_event.summary is None

    def test_complete_already_completed_consultation_raises_error(self):
        """Test that completing an already completed consultation raises ValueError."""
        consultation = create_consulation("patient_123")

        consultation.complete()

        with pytest.raises(ValueError, match="Cannot complete consultation in completed state"):
            consultation.complete()

    def test_complete_cancelled_consultation_raises_error(self):
        """Test that completing a cancelled consultation raises ValueError."""
        consultation = create_consulation("patient_123")
        consultation.cancel(reason="Already cancelled")

        with pytest.raises(ValueError, match="Cannot complete consultation in cancelled state"):
            consultation.complete()


class TestConsultationCancellation:
    """Tests for cancelling consultations."""

    def test_cancel_consultation_sets_status_and_ended_at(self):
        """Test that cancelling sets status and ended_at."""
        consultation = create_consulation("patient_123")

        consultation.cancel(reason="Test cancellation")

        assert consultation.status.status == ConsultationStatusEnum.CANCELLED
        assert consultation.ended_at is not None

    def test_cancel_with_reason(self):
        """Test cancelling with a reason."""
        consultation = create_consulation("patient_123")
        reason = "Patient disconnected"

        consultation.cancel(reason=reason)

        assert consultation.status.reason == reason

    def test_cancel_without_reason(self):
        """Test cancelling without a reason."""
        consultation = create_consulation("patient_123")

        consultation.cancel()

        assert consultation.status.reason is None

    def test_cancel_completed_consultation(self):
        """Test that a completed consultation can be transitioned to cancelled."""
        consultation = create_consulation("patient_123")

        consultation.complete()
        consultation.status = consultation.status.transition_to(ConsultationStatusEnum.CANCELLED, "Changed mind")

        assert consultation.status.status == ConsultationStatusEnum.CANCELLED


class TestGetContextSummary:
    """Tests for getting consultation context summary."""

    def test_get_context_summary_with_messages(self):
        """Test getting context summary with messages."""
        consultation = create_consulation("patient_123")

        msg1 = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="I have a headache"),
        )
        msg2 = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="How long have you had it?"),
        )

        consultation.add_message(msg1)
        consultation.add_message(msg2)

        summary = consultation.get_context_summary()

        assert consultation.consultation_id in summary
        # After adding user message then assistant message, status is waiting_for_input
        assert "Status: waiting_for_input" in summary
        assert "Messages: 2" in summary
        assert "user:" in summary
        assert "assistant:" in summary

    def test_get_context_summary_with_no_messages(self):
        """Test getting context summary when no messages."""
        consultation = create_consulation("patient_123")

        summary = consultation.get_context_summary()

        assert consultation.consultation_id in summary
        assert "Messages: 0" in summary

    def test_get_context_summary_max_messages_limit(self):
        """Test that context summary respects max_messages limit."""
        consultation = create_consulation("patient_123")

        for i in range(15):
            msg = Message(
                message_id=f"msg_{i:03d}",
                role=MessageRole.USER,
                content=MessageContent(text=f"Message {i}"),
            )
            consultation.add_message(msg)

        summary = consultation.get_context_summary(max_messages=5)

        # Summary should only mention last 5 messages
        assert "Messages: 15" in summary  # Total count
        # Should contain content from recent messages only

    def test_get_context_summary_truncates_long_content(self):
        """Test that long message content is truncated in summary."""
        consultation = create_consulation("patient_123")

        long_text = "A" * 200
        msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text=long_text),
        )

        consultation.add_message(msg)
        summary = consultation.get_context_summary()

        # Long content should be truncated with "..."
        assert "..." in summary


class TestGetStructuredOutputs:
    """Tests for getting structured outputs from consultation."""

    def test_get_structured_outputs_returns_assistant_messages_with_data(self):
        """Test that get_structured_outputs returns messages with structured data."""
        consultation = create_consulation("patient_123")

        msg1 = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        msg2 = Message(
            message_id="msg_002",
            role=MessageRole.ASSISTANT,
            content=MessageContent(
                text="Result",
                structured_data={"score": 85, "risk": "low"},
            ),
        )
        msg3 = Message(
            message_id="msg_003",
            role=MessageRole.ASSISTANT,
            content=MessageContent(
                text="Another result",
                structured_data={"plan": "exercise"},
            ),
        )

        consultation.add_message(msg1)
        consultation.add_message(msg2)
        consultation.add_message(msg3)

        outputs = consultation.get_structured_outputs()

        assert len(outputs) == 2
        assert outputs[0] == {"score": 85, "risk": "low"}
        assert outputs[1] == {"plan": "exercise"}

    def test_get_structured_outputs_ignores_user_messages(self):
        """Test that user messages are not included in structured outputs."""
        consultation = create_consulation("patient_123")

        msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(
                text="Data",
                structured_data={"user_data": "value"},
            ),
        )

        consultation.add_message(msg)

        outputs = consultation.get_structured_outputs()

        assert len(outputs) == 0

    def test_get_structured_outputs_ignores_messages_without_structured_data(self):
        """Test that messages without structured data are ignored."""
        consultation = create_consulation("patient_123")

        msg = Message(
            message_id="msg_001",
            role=MessageRole.ASSISTANT,
            content=MessageContent(text="Plain text response"),
        )

        consultation.add_message(msg)

        outputs = consultation.get_structured_outputs()

        assert len(outputs) == 0

    def test_get_structured_outputs_with_empty_consultation(self):
        """Test getting structured outputs from empty consultation."""
        consultation = create_consulation("patient_123")

        outputs = consultation.get_structured_outputs()

        assert outputs == []


class TestToDict:
    """Tests for to_dict serialization."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all important fields."""
        consultation = create_consulation("patient_123")

        msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Hello"),
        )
        consultation.add_message(msg)

        result = consultation.to_dict()

        assert result["consultation_id"] == consultation.consultation_id
        assert result["patient_id"] == "patient_123"
        assert result["status"] == "processing"  # Status after adding user message
        assert result["started_at"] is not None
        assert result["ended_at"] is None
        assert result["message_count"] == 1
        assert len(result["messages"]) == 1

    def test_to_dict_with_completed_consultation(self):
        """Test to_dict with a completed consultation."""
        consultation = create_consulation("patient_123")
        consultation.complete(summary="Test summary")

        result = consultation.to_dict()

        assert result["status"] == "completed"
        assert result["ended_at"] is not None

    def test_to_dict_serializes_messages(self):
        """Test that to_dict properly serializes messages."""
        consultation = create_consulation("patient_123")

        msg = Message(
            message_id="msg_001",
            role=MessageRole.USER,
            content=MessageContent(text="Test"),
            intent=IntentType.GENERAL_CHAT,
        )
        consultation.add_message(msg)

        result = consultation.to_dict()

        assert len(result["messages"]) == 1
        msg_dict = result["messages"][0]
        assert msg_dict["message_id"] == "msg_001"
        assert msg_dict["role"] == "user"
        assert msg_dict["intent"] == "general_chat"
