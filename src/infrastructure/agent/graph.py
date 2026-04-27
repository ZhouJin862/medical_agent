"""
LangGraph - Medical Agent workflow graph.

Constructs the agent workflow using LangGraph's StateGraph.
"""

import logging
from typing import Literal, TypedDict

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    StateGraph = None
    END = None

from .state import AgentState, AgentStatus, IntentType, PatientContext, ConversationMemory, SkillExecutionResult
from .nodes import (
    load_patient_node,
    retrieve_memory_node,
    classify_intent_node,
    route_skill_node,
    skip_skill_node,
    aggregate_results_node,
    save_memory_node,
)

logger = logging.getLogger(__name__)


def should_route_to_skill(state: AgentState) -> Literal["execute_skill", "skip_skill"]:
    """
    Decide whether to execute a skill or skip to aggregation.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.suggested_skill and state.intent:
        return "execute_skill"
    return "skip_skill"


def should_continue(state: AgentState) -> Literal["save_memory", "error"]:
    """
    Decide whether to continue to save memory or handle error.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.error_message:
        return "error"
    return "save_memory"


def create_medical_agent_graph() -> "StateGraph":
    """
    Create the LangGraph workflow for medical agent.

    The workflow consists of:
    1. load_patient - Load patient data from MCP
    2. retrieve_memory - Retrieve conversation history
    3. classify_intent - Classify user intent
    4. route_skill - Decide which skill to use
    5. execute_skill - Execute the selected skill (conditional)
    6. aggregate_results - Aggregate all results
    7. save_memory - Save to conversation memory

    Returns:
        StateGraph instance
    """
    if StateGraph is None:
        raise ImportError(
            "langgraph is required. Install with: pip install langgraph"
        )

    logger.info("Creating medical agent workflow graph")

    # Create the state graph
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("load_patient", load_patient_node)
    workflow.add_node("retrieve_memory", retrieve_memory_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("route_skill", route_skill_node)
    # execute_skill is now a pass-through - skill execution happens in route_skill_node
    workflow.add_node("execute_skill", lambda state: state)
    workflow.add_node("skip_skill", skip_skill_node)
    workflow.add_node("aggregate", aggregate_results_node)
    workflow.add_node("save_memory", save_memory_node)
    workflow.add_node("error", lambda s: s)  # Error passthrough

    # Define the entry point
    workflow.set_entry_point("load_patient")

    # Add edges
    workflow.add_edge("load_patient", "retrieve_memory")
    workflow.add_edge("retrieve_memory", "classify_intent")
    workflow.add_edge("classify_intent", "route_skill")

    # Conditional routing for skill execution
    workflow.add_conditional_edges(
        "route_skill",
        should_route_to_skill,
        {
            "execute_skill": "execute_skill",
            "skip_skill": "aggregate",
        }
    )

    # After skill execution (or skip), go to aggregation
    workflow.add_edge("execute_skill", "aggregate")

    # Conditional routing for error handling
    workflow.add_conditional_edges(
        "aggregate",
        should_continue,
        {
            "save_memory": "save_memory",
            "error": "error",
        }
    )

    # Final step
    workflow.add_edge("save_memory", END)
    workflow.add_edge("error", END)

    # Compile the graph
    app = workflow.compile()

    logger.info("Medical agent workflow graph created successfully")
    return app


class MedicalAgent:
    """
    Medical Agent - Main agent for health assessment.

    Orchestrates the LangGraph workflow for processing
    user health queries and generating personalized responses.
    """

    def __init__(self):
        """Initialize the medical agent."""
        self._graph = None
        logger.info("MedicalAgent initialized")

    @property
    def graph(self) -> "StateGraph":
        """Get or create the workflow graph."""
        if self._graph is None:
            self._graph = create_medical_agent_graph()
        return self._graph

    async def process(
        self,
        user_input: str,
        patient_id: str,
        party_id: str = None,
        ping_an_health_data: dict = None,
        previous_patient_context: dict = None,
    ) -> AgentState:
        """
        Process a user request through the agent workflow.

        Args:
            user_input: User's input message
            patient_id: Patient identifier
            party_id: Optional Ping An customer ID
            ping_an_health_data: Optional health data from Ping An API
            previous_patient_context: Optional previous patient context from session

        Returns:
            Final agent state with results
        """
        from .state import create_initial_state

        # Create initial state with party_id if provided
        initial_state = create_initial_state(user_input, patient_id)
        if party_id:
            initial_state.party_id = party_id
        if ping_an_health_data:
            # Store the Ping An health data so load_patient_node can use it
            initial_state.ping_an_health_data = ping_an_health_data
            logger.info(f"DEBUG graph.process: Set ping_an_health_data with party_id={party_id}, data_keys={list(ping_an_health_data.keys()) if ping_an_health_data else None}")
        if previous_patient_context:
            # Store previous patient context so load_patient_node can merge with new data
            initial_state.previous_patient_context = previous_patient_context
            logger.info(f"DEBUG graph.process: Set previous_patient_context")

        logger.info(
            f"Processing request: patient_id={patient_id}, "
            f"input={user_input[:50]}..."
        )

        try:
            # Run the workflow - LangGraph returns a dict
            result_dict = await self.graph.ainvoke(initial_state)

            # Convert dict back to AgentState if needed
            if isinstance(result_dict, dict):
                # Handle status enum conversion
                if "status" in result_dict and isinstance(result_dict["status"], str):
                    result_dict["status"] = AgentStatus(result_dict["status"])
                elif "status" not in result_dict:
                    result_dict["status"] = AgentStatus.IDLE

                if "intent" in result_dict and isinstance(result_dict["intent"], str):
                    result_dict["intent"] = IntentType(result_dict["intent"])

                # Handle nested models - skip if already converted
                if "patient_context" in result_dict and isinstance(result_dict["patient_context"], dict):
                    result_dict["patient_context"] = PatientContext(**result_dict["patient_context"])
                if "conversation_memory" in result_dict and isinstance(result_dict["conversation_memory"], dict):
                    result_dict["conversation_memory"] = ConversationMemory(**result_dict["conversation_memory"])
                if "current_skill_result" in result_dict and isinstance(result_dict["current_skill_result"], dict):
                    result_dict["current_skill_result"] = SkillExecutionResult(**result_dict["current_skill_result"])
                if "executed_skills" in result_dict:
                    result_dict["executed_skills"] = [SkillExecutionResult(**s) if isinstance(s, dict) else s for s in result_dict["executed_skills"]]

                final_state = AgentState(**result_dict)
            else:
                final_state = result_dict

            logger.info(
                f"Request processed: status={final_state.status.value}, "
                f"intent={final_state.intent.value if final_state.intent else None}"
            )

            return final_state

        except Exception as e:
            logger.error(f"Failed to process request: {e}")
            import traceback
            traceback.print_exc()
            initial_state.error_message = str(e)
            initial_state.status = AgentStatus.ERROR
            return initial_state

    async def stream(
        self,
        user_input: str,
        patient_id: str,
    ):
        """
        Stream the agent workflow execution.

        Yields intermediate states as the workflow progresses.

        Args:
            user_input: User's input message
            patient_id: Patient identifier

        Yields:
            Intermediate agent states
        """
        from .state import create_initial_state

        initial_state = create_initial_state(user_input, patient_id)

        logger.info(f"Streaming request: patient_id={patient_id}")

        async for state in self.graph.astream(initial_state):
            yield state

    def get_state_summary(self, state: AgentState) -> dict:
        """
        Get a summary of the agent state.

        Args:
            state: Agent state to summarize

        Returns:
            Dictionary with state summary
        """
        return {
            "patient_id": state.patient_id,
            "status": state.status.value,
            "intent": state.intent.value if state.intent else None,
            "confidence": state.confidence,
            "skills_executed": len(state.executed_skills),
            "has_response": state.final_response is not None,
            "has_structured_output": state.structured_output is not None,
            "error": state.error_message,
        }


# Convenience function to create and use the agent
async def process_health_query(
    user_input: str,
    patient_id: str,
) -> AgentState:
    """
    Convenience function to process a health query.

    Args:
        user_input: User's input message
        patient_id: Patient identifier

    Returns:
        Final agent state with results
    """
    agent = MedicalAgent()
    return await agent.process(user_input, patient_id)
