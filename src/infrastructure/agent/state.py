"""
Agent State - State management for LangGraph workflow.

Defines the state that flows through the agent graph.
"""

from typing import Optional, Dict, List, Any, Literal, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass
import json


class IntentType(str, Enum):
    """Types of intents that can be classified."""

    HEALTH_ASSESSMENT = "health_assessment"
    RISK_PREDICTION = "risk_prediction"
    HEALTH_PLAN = "health_plan"
    TRIAGE = "triage"
    MEDICATION_CHECK = "medication_check"
    SERVICE_RECOMMENDATION = "service_recommendation"
    GENERAL_CHAT = "general_chat"


class AgentStatus(str, Enum):
    """Agent processing status."""

    IDLE = "idle"
    LOADING_PATIENT = "loading_patient"
    RETRIEVING_MEMORY = "retrieving_memory"
    CLASSIFYING_INTENT = "classifying_intent"
    EXECUTING_SKILL = "executing_skill"
    AGGREGATING_RESULTS = "aggregating_results"
    SAVING_MEMORY = "saving_memory"
    COMPLETED = "completed"
    ERROR = "error"


class PatientContext(BaseModel):
    """
    Patient context information.

    Attributes:
        patient_id: Unique patient identifier
        basic_info: Basic patient information (name, age, gender, etc.)
        vital_signs: Current vital signs data
        medical_history: Medical history and conditions
        last_updated: When this context was last updated
    """

    patient_id: str
    basic_info: Dict[str, Any] = Field(default_factory=dict)
    vital_signs: Dict[str, Any] = Field(default_factory=dict)
    medical_history: Dict[str, Any] = Field(default_factory=dict)
    last_updated: Optional[datetime] = None


class ConversationMemory(BaseModel):
    """
    Conversation memory context.

    Attributes:
        conversation_id: Conversation/session identifier
        messages: List of messages in this conversation
        context_summary: Summary of conversation context
        previous_assessments: Previous health assessment results
    """

    conversation_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    context_summary: Optional[str] = None
    previous_assessments: List[Dict[str, Any]] = Field(default_factory=list)


class SkillExecutionResult(BaseModel):
    """
    Result from executing a skill.

    Attributes:
        skill_name: Name of the skill that was executed
        success: Whether execution was successful
        result_data: Result data from the skill (legacy field)
        structured_output: Structured output from skill execution
        response: Text response from skill execution
        error: Error message if execution failed
        execution_time: Time taken to execute (milliseconds)
    """

    skill_name: str
    success: bool
    result_data: Optional[Union[str, Dict[str, Any]]] = None
    structured_output: Optional[Dict[str, Any]] = None
    response: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[int] = None


class AgentState(BaseModel):
    """
    State that flows through the LangGraph workflow.

    This state is updated at each node in the graph and contains
    all information needed for processing the user request.
    """

    # Input
    user_input: str
    patient_id: str

    # Ping An health archive
    party_id: Optional[str] = Field(default=None, description="Customer ID from Ping An health archive (客户号)")
    ping_an_health_data: Optional[Dict[str, Any]] = Field(default=None, description="Raw health data from Ping An API (for load_patient_node to use)")
    previous_patient_context: Optional[Dict[str, Any]] = Field(default=None, description="Previous patient context from session (for merging with new data)")

    # Processing status
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    current_step: str = Field(default="")

    # Context
    patient_context: Optional[PatientContext] = None
    conversation_memory: Optional[ConversationMemory] = None

    # Intent classification
    intent: Optional[IntentType] = None
    confidence: float = Field(default=0.0)
    suggested_skill: Optional[str] = None

    # Multi-skill selection and orchestration (P1 integration)
    multi_skill_selection: Optional[Dict[str, Any]] = Field(default=None, description="Multi-skill selection result from EnhancedLLMSkillSelector")
    execution_plan: Optional[Dict[str, Any]] = Field(default=None, description="Execution plan for multi-skill orchestration")
    multi_skill_result: Optional[Dict[str, Any]] = Field(default=None, description="Result from multi-skill execution")

    # Skill execution
    executed_skills: List[SkillExecutionResult] = Field(default_factory=list)
    current_skill_result: Optional[SkillExecutionResult] = None

    # Aggregated results
    health_assessment: Optional[Dict[str, Any]] = None
    risk_prediction: Optional[Dict[str, Any]] = None
    health_plan: Optional[Dict[str, Any]] = None
    triage_recommendation: Optional[Dict[str, Any]] = None
    medication_recommendation: Optional[Dict[str, Any]] = None
    service_recommendation: Optional[Dict[str, Any]] = None

    # Output
    final_response: Optional[str] = None
    structured_output: Optional[Dict[str, Any]] = None

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)

    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    model_used: Optional[str] = None
    tokens_used: int = Field(default=0)
    selection_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from skill selection process")

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary representation."""
        return {
            "user_input": self.user_input,
            "patient_id": self.patient_id,
            "status": self.status.value if self.status else None,
            "current_step": self.current_step,
            "intent": self.intent.value if self.intent else None,
            "confidence": self.confidence,
            "suggested_skill": self.suggested_skill,
            "executed_skills": [
                {
                    "skill_name": s.skill_name,
                    "success": s.success,
                    "error": s.error,
                    "execution_time": s.execution_time,
                }
                for s in self.executed_skills
            ],
            "final_response": self.final_response,
            "structured_output": self.structured_output,
            "error_message": self.error_message,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
        }

    def add_skill_result(self, result: SkillExecutionResult) -> None:
        """Add a skill execution result to the state."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG add_skill_result: Adding skill_result - success={result.success}, result_data={result.result_data is not None}, skill_name={result.skill_name}")
        self.executed_skills.append(result)
        self.current_skill_result = result

    def get_all_results(self) -> Dict[str, Any]:
        """Get all aggregated results."""
        return {
            "health_assessment": self.health_assessment,
            "risk_prediction": self.risk_prediction,
            "health_plan": self.health_plan,
            "triage_recommendation": self.triage_recommendation,
            "medication_recommendation": self.medication_recommendation,
            "service_recommendation": self.service_recommendation,
        }


def create_initial_state(user_input: str, patient_id: str) -> AgentState:
    """
    Create an initial agent state.

    Args:
        user_input: User's input message
        patient_id: Patient identifier

    Returns:
        New AgentState instance
    """
    return AgentState(
        user_input=user_input,
        patient_id=patient_id,
        status=AgentStatus.IDLE,
        start_time=datetime.now(),
    )
