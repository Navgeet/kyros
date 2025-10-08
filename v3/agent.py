#!/usr/bin/env python3
"""
Main LangGraph Supervised Planning Agent
Orchestrates the modular components into a cohesive agent system
"""

import asyncio
from typing import Optional

# LangGraph imports
from langgraph.graph import StateGraph, END

# Local imports
from config import LangGraphAgentConfig
from state import AgentState
from workflow_nodes import WorkflowNodes, WorkflowRouter
from services import PlanningService, RAGService, UtilityService, WebSocketManager
from api import AgentAPI


class LangGraphSupervisedPlanningAgent:
    """Main agent class that orchestrates all components"""

    def __init__(self, config: Optional[LangGraphAgentConfig] = None):
        self.config = config or LangGraphAgentConfig()
        self.config.validate()

        # Initialize services
        self.planning_service = PlanningService(self.config)
        self.rag_service = RAGService(self.config)
        self.utility_service = UtilityService(self.config)
        self.websocket_manager = WebSocketManager()

        # Initialize workflow components
        self.nodes = WorkflowNodes(
            self.planning_service,
            self.rag_service,
            self.utility_service
        )
        self.router = WorkflowRouter()

        # Build workflow
        self.workflow = self._build_workflow()
        self.graph = self.workflow.compile()

        # Initialize API layer with shared session management
        self.api = AgentAPI(
            self.graph,
            self.config,
            self.utility_service,
            self.websocket_manager
        )
        # Share session management between agent and API
        self.sessions = self.api.sessions

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow using modular nodes"""
        workflow = StateGraph(AgentState)

        # Add nodes using the modular node implementations
        workflow.add_node("handle_user_message", self.nodes.handle_user_message)
        workflow.add_node("generate_text_plan", self.nodes.generate_text_plan)
        workflow.add_node("handle_text_plan_approval", self.nodes.handle_text_plan_approval)
        workflow.add_node("handle_text_plan_feedback", self.nodes.handle_text_plan_feedback)
        workflow.add_node("generate_code", self.nodes.generate_code)
        workflow.add_node("handle_code_approval", self.nodes.handle_code_approval)
        workflow.add_node("handle_code_feedback", self.nodes.handle_code_feedback)
        workflow.add_node("handle_replan", self.nodes.handle_replan)
        workflow.add_node("complete_task", self.nodes.complete_task)

        # Set entry point
        workflow.set_entry_point("handle_user_message")

        # Define conditional routing using modular router
        workflow.add_conditional_edges(
            "handle_user_message",
            self.router.route_from_user_message,
            {
                "generate_text_plan": "generate_text_plan",
                "handle_approval": "handle_text_plan_approval",
                "handle_feedback": "handle_text_plan_feedback",
                "handle_replan": "handle_replan",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "generate_text_plan",
            self.router.route_from_text_plan,
            {
                "approval": "handle_text_plan_approval",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "handle_text_plan_approval",
            self.router.route_from_text_approval,
            {
                "generate_code": "generate_code",
                "feedback": "handle_text_plan_feedback",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "handle_text_plan_feedback",
            self.router.route_from_text_feedback,
            {
                "generate_text_plan": "generate_text_plan",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "generate_code",
            self.router.route_from_code_generation,
            {
                "approval": "handle_code_approval",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "handle_code_approval",
            self.router.route_from_code_approval,
            {
                "complete": "complete_task",
                "feedback": "handle_code_feedback",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "handle_code_feedback",
            self.router.route_from_code_feedback,
            {
                "generate_code": "generate_code",
                "end": END
            }
        )

        workflow.add_edge("handle_replan", "generate_text_plan")
        workflow.add_edge("complete_task", END)

        return workflow

    async def start_server(self):
        """Start the FastAPI server using the API layer"""
        await self.api.start_server()


# Convenience functions
def create_agent(config: Optional[LangGraphAgentConfig] = None) -> LangGraphSupervisedPlanningAgent:
    """Create a LangGraph supervised planning agent"""
    return LangGraphSupervisedPlanningAgent(config)


async def main():
    """Main entry point"""
    try:
        config = LangGraphAgentConfig.from_env()
        agent = create_agent(config)
        await agent.start_server()
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))