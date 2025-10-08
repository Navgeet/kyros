#!/usr/bin/env python3
"""
FastAPI and WebSocket API layer for the LangGraph Supervised Planning Agent
Handles all HTTP routes and WebSocket connections
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from config import LangGraphAgentConfig
from state import AgentState, StateManager
from services import WebSocketManager


class AgentAPI:
    """API layer that handles FastAPI routes and WebSocket connections"""

    def __init__(self, agent_workflow, config: LangGraphAgentConfig, utility_service, websocket_manager: Optional[WebSocketManager] = None):
        self.agent_workflow = agent_workflow  # The compiled LangGraph workflow
        self.config = config
        self.utility_service = utility_service
        self.websocket_manager = websocket_manager or WebSocketManager()

        # Session management (shared with main agent)
        self.sessions: Dict[str, AgentState] = {}

        # Create FastAPI app
        self.app = self._create_fastapi_app()

    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        app = FastAPI(
            title="LangGraph Supervised Planning Agent V3",
            version="3.0.0",
            description="Human-in-the-loop planning with structured workflows"
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add routes
        self._setup_routes(app)

        return app

    def _setup_routes(self, app: FastAPI):
        """Setup FastAPI routes"""

        @app.get("/")
        async def get_index():
            return HTMLResponse(self.utility_service.get_html_interface())

        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "version": "3.0.0",
                "active_sessions": len(self.sessions)
            }

        @app.get("/sessions")
        async def get_sessions():
            return {
                "active_sessions": len(self.sessions),
                "sessions": [
                    {
                        "id": sid,
                        "phase": session["phase"],
                        "created_at": session["created_at"],
                        "last_activity": session["last_activity"],
                        "reconnections": session["reconnections"]
                    }
                    for sid, session in self.sessions.items()
                ]
            }

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket_connection(websocket)

    async def _handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connections with LangGraph workflow"""
        session_id = None

        try:
            await self.websocket_manager.connect(websocket)

            # Get initial message to determine session
            data = await websocket.receive_text()
            initial_message = json.loads(data)

            session_id = await self._handle_session_connection(websocket, initial_message)

            # Handle initial message if it was a user message
            if initial_message.get("type") == "user_message":
                await self._process_message_with_langgraph(initial_message, websocket, session_id)

            # Main message loop
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self._process_message_with_langgraph(message, websocket, session_id)

        except WebSocketDisconnect:
            self.websocket_manager.disconnect(websocket)
            if session_id and session_id in self.sessions:
                self.sessions[session_id]["websocket"] = None
                print(f"🔌 Session {session_id} disconnected")

        except Exception as e:
            if websocket in self.websocket_manager.active_connections:
                try:
                    await self._safe_send({
                        "type": "error",
                        "message": f"Error: {str(e)}"
                    }, websocket)
                except RuntimeError:
                    self.websocket_manager.disconnect(websocket)
            print(f"❌ WebSocket error: {e}")

    async def _handle_session_connection(self, websocket: WebSocket, initial_message: Dict) -> str:
        """Handle session connection/reconnection logic"""
        requested_session_id = initial_message.get("session_id")

        if requested_session_id and requested_session_id in self.sessions:
            # Reconnect to existing session
            session_id = requested_session_id
            state = self.sessions[session_id]
            state["websocket"] = websocket
            state["reconnections"] += 1
            StateManager.update_activity(state)

            await self._safe_send({
                "type": "reconnection",
                "session_id": session_id,
                "message": f"Reconnected to session {session_id}!"
            }, websocket)

            # Send current session state
            await self._send_session_state(websocket, session_id)

        else:
            # Create new session
            session_id = self._create_new_session(websocket)

            await self._safe_send({
                "type": "connection",
                "session_id": session_id,
                "message": "Welcome to the LangGraph Supervised Planning Agent V3!"
            }, websocket)

            await self._safe_send({
                "type": "agent_message",
                "message": "Please describe what you'd like me to help you with:"
            }, websocket)

        return session_id

    async def _process_message_with_langgraph(self, message: Dict, websocket: WebSocket, session_id: str):
        """Process message using LangGraph workflow"""
        state = self.sessions[session_id]
        state["current_message"] = message
        StateManager.update_activity(state)

        # Save conversation history periodically
        self.utility_service.save_conversation_history(session_id, state["conversation_history"])

        try:
            # Run the LangGraph workflow
            result_state = await self.agent_workflow.ainvoke(state)

            # Update session state
            self.sessions[session_id].update(result_state)
            self.sessions[session_id]["current_message"] = None

            # Send appropriate response based on phase
            await self._send_phase_response(websocket, session_id)

        except Exception as e:
            await self._safe_send({
                "type": "error",
                "message": f"Workflow error: {str(e)}"
            }, websocket)
            print(f"❌ Workflow error in session {session_id}: {e}")

    async def _send_phase_response(self, websocket: WebSocket, session_id: str):
        """Send appropriate response based on current phase"""
        session = self.sessions[session_id]
        phase = session["phase"]

        response_map = {
            "text_plan_approval": {
                "type": "text_plan_review",
                "plan": session.get("text_plan", ""),
                "message": "Here's my high-level plan. Please review it:"
            },
            "code_approval": {
                "type": "code_review",
                "code": session.get("python_code", ""),
                "message": "Here's the generated Python code. Please review it:"
            },
            "text_plan_feedback": {
                "type": "feedback_request",
                "plan_type": "text",
                "message": "Please tell me what needs to be improved in the plan:"
            },
            "code_feedback": {
                "type": "feedback_request",
                "plan_type": "code",
                "message": "Please tell me what needs to be improved in the code:"
            },
            "completed": {
                "type": "completion",
                "message": "Perfect! The plan and code have been approved.",
                "final_plan": session.get("text_plan", ""),
                "final_code": session.get("python_code", "")
            }
        }

        response = response_map.get(phase)
        if response:
            await self._safe_send(response, websocket)

    async def _send_session_state(self, websocket: WebSocket, session_id: str):
        """Send current session state to client"""
        session = self.sessions[session_id]

        await self._safe_send({
            "type": "session_state",
            "session_id": session_id,
            "phase": session["phase"],
            "text_plan": session.get("text_plan", ""),
            "python_code": session.get("python_code", ""),
            "user_request": session.get("user_request", "")
        }, websocket)

    async def _safe_send(self, message: dict, websocket: WebSocket):
        """Safely send a message to WebSocket"""
        await self.websocket_manager.send_personal_message(message, websocket)

    def _create_new_session(self, websocket: WebSocket) -> str:
        """Create a new session with proper state initialization"""
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = StateManager.create_initial_state(session_id, websocket)

        print(f"✨ Created new LangGraph session: {session_id}")
        return session_id

    async def start_server(self):
        """Start the FastAPI server"""
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)

        print("🚀 Starting LangGraph Supervised Planning Agent V3...")
        print(f"📡 Server available at http://{self.config.host}:{self.config.port}")
        print(f"🔌 WebSocket endpoint: ws://{self.config.host}:{self.config.port}/ws")
        print("📋 Features: Human-in-the-loop planning, RAG integration, Session management")

        await server.serve()