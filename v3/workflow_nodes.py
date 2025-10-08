"""
Workflow nodes for LangGraph Supervised Planning Agent
Each node represents a step in the planning workflow
"""

from datetime import datetime
from typing import Optional, List, Dict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from state import AgentState, StateManager
from services import PlanningService, RAGService, UtilityService


class WorkflowNodes:
    """Collection of workflow node implementations"""

    def __init__(self, planning_service: PlanningService, rag_service: RAGService,
                 utility_service: UtilityService):
        self.planning_service = planning_service
        self.rag_service = rag_service
        self.utility_service = utility_service

    async def handle_user_message(self, state: AgentState) -> AgentState:
        """Handle incoming user messages."""
        if not state["current_message"]:
            return state

        message = state["current_message"]
        user_message = message.get("content", "").strip()

        if not user_message:
            return state

        # Take screenshot
        screenshot = await self.utility_service.capture_screenshot()

        # Add to conversation history
        StateManager.add_conversation_entry(state, {
            "from": "user",
            "content": user_message,
            "screenshot": screenshot
        })

        # Update user request if this is initial request
        if state["phase"] == "greeting":
            state["user_request"] = user_message
            StateManager.transition_phase(state, "text_plan_generation")

        # Add to messages
        state["messages"].append(HumanMessage(content=user_message))
        state["screenshot"] = screenshot

        return state

    async def generate_text_plan(self, state: AgentState) -> AgentState:
        """Generate text plan with RAG integration."""
        if not state["user_request"]:
            return state

        try:
            # Generate text plan (includes RAG refinement)
            text_plan = await self.planning_service.generate_text_plan(
                state["user_request"],
                state
            )
            state["text_plan"] = text_plan
            StateManager.transition_phase(state, "text_plan_approval")

            # Add to conversation history
            StateManager.add_conversation_entry(state, {
                "from": "system",
                "content": f"Final text plan for user review:\n{text_plan}"
            })

            state["messages"].append(AIMessage(content=f"Generated text plan: {text_plan}"))

        except Exception as e:
            state["messages"].append(AIMessage(content=f"Error generating text plan: {e}"))

        return state

    async def handle_text_plan_approval(self, state: AgentState) -> AgentState:
        """Handle text plan approval decision."""
        message = state["current_message"]
        approved = message.get("approved", False) if message else False

        if approved:
            StateManager.transition_phase(state, "code_generation")
            StateManager.add_conversation_entry(state, {
                "from": "user",
                "content": "text_plan_approved"
            })
            state["messages"].append(SystemMessage(content="Text plan approved, moving to code generation"))
        else:
            StateManager.transition_phase(state, "text_plan_feedback")
            state["messages"].append(SystemMessage(content="Text plan needs feedback"))

        return state

    async def handle_text_plan_feedback(self, state: AgentState) -> AgentState:
        """Handle text plan feedback and improvement."""
        message = state["current_message"]
        feedback = message.get("content", "") if message else ""

        if feedback:
            state["feedback"] = feedback

            try:
                # Improve plan based on feedback
                improved_plan = await self.planning_service.improve_text_plan(
                    state["text_plan"],
                    feedback,
                    state["user_request"]
                )
                state["text_plan"] = improved_plan
                StateManager.transition_phase(state, "text_plan_approval")

                # Add to conversation history
                StateManager.add_conversation_entry(state, {
                    "from": "user",
                    "content": feedback
                })

                StateManager.add_conversation_entry(state, {
                    "from": "system",
                    "content": f"Improved text plan:\n{improved_plan}"
                })

                state["messages"].append(AIMessage(
                    content=f"Improved text plan based on feedback: {improved_plan}"
                ))

            except Exception as e:
                state["messages"].append(AIMessage(content=f"Error improving text plan: {e}"))

        return state

    async def generate_code(self, state: AgentState) -> AgentState:
        """Generate Python code from text plan."""
        if not state["text_plan"]:
            return state

        try:
            python_code = await self.planning_service.generate_code(
                state["text_plan"],
                state["user_request"]
            )
            state["python_code"] = python_code
            StateManager.transition_phase(state, "code_approval")

            # Add to conversation history
            StateManager.add_conversation_entry(state, {
                "from": "system",
                "content": python_code
            })

            state["messages"].append(AIMessage(content=f"Generated Python code: {python_code}"))

        except Exception as e:
            state["messages"].append(AIMessage(content=f"Error generating code: {e}"))

        return state

    async def handle_code_approval(self, state: AgentState) -> AgentState:
        """Handle code approval decision."""
        message = state["current_message"]
        approved = message.get("approved", False) if message else False

        if approved:
            StateManager.transition_phase(state, "completed")
            StateManager.add_conversation_entry(state, {
                "from": "user",
                "content": "code_approved"
            })
            state["messages"].append(SystemMessage(content="Code approved, task completed"))
        else:
            StateManager.transition_phase(state, "code_feedback")
            state["messages"].append(SystemMessage(content="Code needs feedback"))

        return state

    async def handle_code_feedback(self, state: AgentState) -> AgentState:
        """Handle code feedback and improvement."""
        message = state["current_message"]
        feedback = message.get("content", "") if message else ""

        if feedback:
            state["feedback"] = feedback

            try:
                # Improve code based on feedback
                improved_code = await self.planning_service.improve_code(
                    state["python_code"],
                    feedback,
                    state["text_plan"]
                )
                state["python_code"] = improved_code
                StateManager.transition_phase(state, "code_approval")

                # Add to conversation history
                StateManager.add_conversation_entry(state, {
                    "from": "user",
                    "content": feedback
                })

                StateManager.add_conversation_entry(state, {
                    "from": "system",
                    "content": f"Improved code:\n{improved_code}"
                })

                state["messages"].append(AIMessage(
                    content=f"Improved code based on feedback: {improved_code}"
                ))

            except Exception as e:
                state["messages"].append(AIMessage(content=f"Error improving code: {e}"))

        return state

    async def handle_replan(self, state: AgentState) -> AgentState:
        """Handle replanning request."""
        StateManager.transition_phase(state, "text_plan_generation")
        state["text_plan"] = ""
        state["python_code"] = ""
        state["messages"].append(SystemMessage(content="Replanning requested, starting over"))
        return state

    async def complete_task(self, state: AgentState) -> AgentState:
        """Complete the task."""
        StateManager.transition_phase(state, "completed")
        state["messages"].append(SystemMessage(content="Task completed successfully"))
        return state


class WorkflowRouter:
    """Handles routing logic for workflow transitions"""

    @staticmethod
    def route_from_user_message(state: AgentState) -> str:
        """Route from user message based on phase and message type."""
        if not state["current_message"]:
            return "end"

        message_type = state["current_message"].get("type")
        phase = state["phase"]

        if message_type == "user_message" and phase == "greeting":
            return "generate_text_plan"
        elif message_type == "approval":
            return "handle_approval"
        elif message_type == "feedback":
            return "handle_feedback"
        elif message_type == "replan":
            return "handle_replan"
        else:
            return "end"

    @staticmethod
    def route_from_text_plan(state: AgentState) -> str:
        """Route after text plan generation."""
        return "approval" if state["text_plan"] else "end"

    @staticmethod
    def route_from_text_approval(state: AgentState) -> str:
        """Route after text plan approval."""
        if state["phase"] == "code_generation":
            return "generate_code"
        elif state["phase"] == "text_plan_feedback":
            return "feedback"
        else:
            return "end"

    @staticmethod
    def route_from_text_feedback(state: AgentState) -> str:
        """Route after text plan feedback."""
        return "generate_text_plan" if state["phase"] == "text_plan_approval" else "end"

    @staticmethod
    def route_from_code_generation(state: AgentState) -> str:
        """Route after code generation."""
        return "approval" if state["python_code"] else "end"

    @staticmethod
    def route_from_code_approval(state: AgentState) -> str:
        """Route after code approval."""
        if state["phase"] == "completed":
            return "complete"
        elif state["phase"] == "code_feedback":
            return "feedback"
        else:
            return "end"

    @staticmethod
    def route_from_code_feedback(state: AgentState) -> str:
        """Route after code feedback."""
        return "generate_code" if state["phase"] == "code_approval" else "end"