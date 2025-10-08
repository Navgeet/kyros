"""
State management for LangGraph Supervised Planning Agent
"""

from typing import Dict, List, Optional, TypedDict, Annotated, Literal
from datetime import datetime
from fastapi import WebSocket
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# Type definitions
AgentPhase = Literal[
    "greeting",
    "text_plan_generation",
    "text_plan_approval",
    "text_plan_feedback",
    "code_generation",
    "code_approval",
    "code_feedback",
    "completed"
]

MessageType = Literal[
    "user_message",
    "approval",
    "feedback",
    "replan",
    "code_execution",
    "connection",
    "reconnection"
]


class AgentState(TypedDict):
    """State for the LangGraph agent workflow"""
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    phase: AgentPhase
    user_request: str
    text_plan: str
    python_code: str
    conversation_history: List[Dict]
    websocket: Optional[WebSocket]
    created_at: str
    last_activity: str
    reconnections: int
    current_message: Optional[Dict]
    screenshot: Optional[str]

    # RAG and feedback state
    learning_objects: Optional[List[Dict]]
    feedback: Optional[str]
    approval_status: Optional[bool]

    # Execution state
    execution_result: Optional[Dict]


class StateManager:
    """Manages agent state creation and transitions"""

    @staticmethod
    def create_initial_state(session_id: str, websocket: WebSocket) -> AgentState:
        """Create initial agent state for new session"""
        return AgentState(
            messages=[],
            session_id=session_id,
            phase="greeting",
            user_request="",
            text_plan="",
            python_code="",
            conversation_history=[],
            websocket=websocket,
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            reconnections=0,
            current_message=None,
            screenshot=None,
            learning_objects=None,
            feedback=None,
            approval_status=None,
            execution_result=None
        )

    @staticmethod
    def update_activity(state: AgentState) -> AgentState:
        """Update last activity timestamp"""
        state["last_activity"] = datetime.now().isoformat()
        return state

    @staticmethod
    def add_conversation_entry(state: AgentState, entry: Dict) -> AgentState:
        """Add entry to conversation history"""
        entry["timestamp"] = datetime.now().isoformat()
        state["conversation_history"].append(entry)
        return state

    @staticmethod
    def transition_phase(state: AgentState, new_phase: AgentPhase) -> AgentState:
        """Safely transition to new phase"""
        state["phase"] = new_phase
        return StateManager.update_activity(state)

    @staticmethod
    def can_transition(current_phase: AgentPhase, target_phase: AgentPhase) -> bool:
        """Check if phase transition is valid"""
        valid_transitions = {
            "greeting": ["text_plan_generation"],
            "text_plan_generation": ["text_plan_approval"],
            "text_plan_approval": ["code_generation", "text_plan_feedback"],
            "text_plan_feedback": ["text_plan_approval"],
            "code_generation": ["code_approval"],
            "code_approval": ["completed", "code_feedback"],
            "code_feedback": ["code_approval"],
            "completed": []  # Terminal state
        }

        return target_phase in valid_transitions.get(current_phase, [])