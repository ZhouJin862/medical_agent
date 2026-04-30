"""
Chat application service.

Orchestrates chat operations between the user and AI assistant.
"""
import logging
from typing import Any
from uuid import uuid4

from src.domain.consultation.repositories.consultation_repository import (
    IConsultationRepository,
)
from src.infrastructure.persistence.models.consultation_models import (
    ConsultationStatus,
    MessageRole,
)
from src.infrastructure.mcp.client_factory import MCPClientFactory

logger = logging.getLogger(__name__)


class ChatApplicationService:
    """
    Application service for chat operations.

    Coordinates between consultation repository, MCP clients,
    and the AI model to handle chat conversations.

    Now uses MedicalAgent for intelligent skill-based processing.
    """

    def __init__(
        self,
        consultation_repository: IConsultationRepository,
        mcp_client_factory: MCPClientFactory,
        agent: Any = None,
    ) -> None:
        """
        Initialize ChatApplicationService.

        Args:
            consultation_repository: Repository for consultation operations
            mcp_client_factory: Factory for creating MCP clients
            agent: Optional MedicalAgent for skill-based processing
        """
        self._consultation_repository = consultation_repository
        self._mcp_client_factory = mcp_client_factory
        self._agent = agent  # MedicalAgent for skill-based processing

    async def send_message(
        self,
        patient_id: str,
        message_content: str,
        consultation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a message and get AI response.

        Args:
            patient_id: Patient identifier
            message_content: User message content
            consultation_id: Existing consultation ID (optional)

        Returns:
            Dictionary with consultation_id, user_message, and ai_response
        """
        # Get or create consultation
        if consultation_id:
            consultation = await self._consultation_repository.get_consultation_by_id(
                consultation_id
            )
            if not consultation or consultation["patient_id"] != patient_id:
                raise ValueError(f"Consultation {consultation_id} not found")
        else:
            # Check for active consultation
            consultation = await self._consultation_repository.get_active_consultation(
                patient_id
            )
            if consultation:
                consultation_id = consultation["consultation_id"]
            else:
                # Create new consultation
                consultation_id = str(uuid4())
                consultation = await self._consultation_repository.create_consultation(
                    consultation_id=consultation_id,
                    patient_id=patient_id,
                    status=ConsultationStatus.ACTIVE,
                )

        # Add user message
        user_message = await self._consultation_repository.add_message(
            consultation_id=consultation_id,
            role=MessageRole.USER,
            content=message_content,
        )

        # Get conversation history for context
        messages = await self._consultation_repository.get_messages(
            consultation_id=consultation_id,
            limit=50,
        )

        # Process message through AI (simplified - in real implementation would use LangGraph)
        ai_response_content = await self._generate_ai_response(
            patient_id=patient_id,
            messages=messages,
            consultation_id=consultation_id,
        )

        # Add AI response
        ai_message = await self._consultation_repository.add_message(
            consultation_id=consultation_id,
            role=MessageRole.ASSISTANT,
            content=ai_response_content,
            intent="chat_response",
        )

        return {
            "consultation_id": consultation_id,
            "user_message": user_message,
            "ai_response": ai_message,
        }

    async def _generate_ai_response(
        self,
        patient_id: str,
        messages: list[dict[str, Any]],
        consultation_id: str | None = None,
    ) -> str:
        """
        Generate AI response using MedicalAgent with skill tracking.

        Args:
            patient_id: Patient identifier
            messages: Conversation history
            consultation_id: Optional consultation ID for memory isolation

        Returns:
            AI-generated response text
        """
        # Use MedicalAgent if available for skill-based processing
        if self._agent:
            try:
                logger.info(f"Using MedicalAgent for processing: {patient_id}")

                # Get the last user message
                user_input = messages[-1]["content"] if messages else "Hello"

                # Process through agent (includes skill tracking)
                result = await self._agent.process(
                    user_input=user_input,
                    patient_id=patient_id,
                    session_id=consultation_id,
                )

                # The agent already saved to memory via save_memory_node
                # Just return the response
                return result.final_response or ""

            except Exception as e:
                logger.warning(f"Agent processing failed: {e}, using fallback")
                # Fall through to simplified response

        # Fallback: Generate response using MCP clients (original implementation)
        # Get patient profile for context
        profile_client = self._mcp_client_factory.get_client("profile")
        if profile_client:
            try:
                profile = await profile_client.get_patient_profile(patient_id)
                logger.info(f"Retrieved profile for patient {patient_id}")
            except Exception as e:
                logger.warning(f"Failed to retrieve profile: {e}")
                profile = None
        else:
            profile = None

        # Build conversation context
        conversation_context = self._build_conversation_context(messages)

        # Generate response using fallback method
        response = self._generate_response_text(
            profile=profile,
            conversation_context=conversation_context,
        )

        return response

    def _build_conversation_context(
        self,
        messages: list[dict[str, Any]],
    ) -> str:
        """Build conversation context from message history."""
        context_parts = []
        for msg in messages[-10:]:  # Last 10 messages for context
            role = msg["role"]
            content = msg["content"]
            role_label = "用户" if role == MessageRole.USER else "助手"
            context_parts.append(f"{role_label}: {content}")
        return "\n".join(context_parts)

    def _generate_response_text(
        self,
        profile: dict[str, Any] | None,
        conversation_context: str,
    ) -> str:
        """
        Generate response text (placeholder implementation).

        In production, this would call the actual LLM with proper prompts.
        """
        # This is a simplified placeholder
        if not conversation_context:
            return "您好！我是您的健康助手，请问有什么可以帮助您的吗？"

        last_message = conversation_context.split("\n")[-1]
        if "用户:" in last_message:
            user_input = last_message.split("用户:")[1].strip()
        else:
            user_input = last_message

        # Simple response generation (in production, use actual LLM)
        responses = {
            "你好": "您好！我是您的健康助手，请问有什么可以帮助您的吗？",
            "help": "我可以帮您进行健康评估、制定健康计划、提供分诊建议等。",
            "症状": "请详细描述您的症状，我会为您进行分析和建议。",
        }

        for key, response in responses.items():
            if key in user_input:
                return response

        return f"感谢您的咨询。针对您的问题：{user_input}，建议您咨询专业医生获取详细诊断。"

    async def get_conversation(
        self,
        consultation_id: str,
    ) -> dict[str, Any]:
        """
        Get full conversation for a consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            Consultation with messages
        """
        consultation = await self._consultation_repository.get_consultation_by_id(
            consultation_id
        )
        if not consultation:
            raise ValueError(f"Consultation {consultation_id} not found")

        messages = await self._consultation_repository.get_messages(
            consultation_id=consultation_id,
            limit=1000,
        )

        return {
            **consultation,
            "messages": messages,
        }

    async def end_consultation(
        self,
        consultation_id: str,
    ) -> bool:
        """
        End an active consultation.

        Args:
            consultation_id: Consultation identifier

        Returns:
            True if consultation was ended
        """
        return await self._consultation_repository.update_consultation_status(
            consultation_id=consultation_id,
            status=ConsultationStatus.COMPLETED,
        )
