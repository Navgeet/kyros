#!/usr/bin/env python3
"""
V2 Agent with Conversational Planning Workflow
- High-level text plan generation and approval
- Plan improvement based on user feedback
- Low-level code generation and approval
- Code improvement based on user feedback
- Support for replanning at both levels
"""

import asyncio
import json
import os
import uuid
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Import existing planning modules
import sys
sys.path.append('..')
from generate_text_plan import generate_text_plan_internlm
from refine_plan import refine_plan_internlm
from plan_to_code import plan_to_code_internlm


class WebSocketManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except RuntimeError:
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)


class ConversationalPlanningAgent:
    """V2 Agent with conversational planning workflow."""

    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Conversational Planning Agent V2", version="2.0.0")
        self.websocket_manager = WebSocketManager()

        # Session management
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout_hours = 24  # Sessions expire after 24 hours

        # API configuration
        self.api_url = os.getenv("INTERNLM_API_URL", "http://localhost:23333")
        self.api_key = os.getenv("INTERNLM_API_KEY")

        # Directory setup for conversations and screenshots
        self.conversations_dir = Path("conversations")
        self.screenshots_dir = Path("screenshots")
        self.conversations_dir.mkdir(exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)

        self._setup_middleware()
        self._setup_routes()

        # Session cleanup task will be started when the server starts
        self._cleanup_task = None

    def _setup_middleware(self):
        """Set up CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Set up all routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            return self._get_html_content()

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.get("/sessions")
        async def get_sessions():
            """Debug endpoint to check session status."""
            session_info = {}
            for sid, session in self.sessions.items():
                session_info[sid] = {
                    "phase": session["phase"],
                    "created_at": session["created_at"],
                    "last_activity": session["last_activity"],
                    "reconnections": session.get("reconnections", 0),
                    "has_websocket": session["websocket"] is not None,
                    "user_request": session["user_request"][:50] + "..." if session["user_request"] else ""
                }
            return {
                "total_sessions": len(self.sessions),
                "sessions": session_info,
                "timestamp": datetime.now().isoformat()
            }

        @self.app.on_event("startup")
        async def startup_event():
            """Start background tasks when the server starts."""
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            print("🧹 Started session cleanup task")

        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Clean up background tasks when the server shuts down."""
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
                print("🛑 Stopped session cleanup task")

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_manager.connect(websocket)
            session_id = None

            try:
                # Wait for initial message to get session ID or create new session
                data = await websocket.receive_text()
                initial_message = json.loads(data)

                if initial_message.get("type") == "resume_session" and initial_message.get("session_id"):
                    # Resume existing session
                    requested_session_id = initial_message["session_id"]
                    if requested_session_id in self.sessions:
                        session_id = requested_session_id
                        # Update websocket reference and last activity
                        self.sessions[session_id]["websocket"] = websocket
                        self.sessions[session_id]["last_activity"] = datetime.now().isoformat()
                        self.sessions[session_id]["reconnections"] = self.sessions[session_id].get("reconnections", 0) + 1

                        print(f"🔄 Session {session_id} resumed (reconnections: {self.sessions[session_id]['reconnections']})")

                        # Send session resumption confirmation (no visible message to user)
                        await self._safe_send({
                            "type": "session_resumed",
                            "session_id": session_id,
                            "silent": True  # Flag to indicate this should not show a message
                        }, websocket)

                        # Send current session state silently
                        await self._send_session_state(websocket, session_id, silent=True)
                    else:
                        # Session not found, create new one
                        session_id = self._create_new_session(websocket)
                        print(f"❌ Session {requested_session_id} not found, created new session {session_id}")
                        await self._safe_send({
                            "type": "session_not_found",
                            "session_id": session_id,
                            "message": f"Previous session {requested_session_id} not found or expired. Starting a new conversation."
                        }, websocket)
                else:
                    # Create new session (either explicit new_session or no session ID provided)
                    session_id = self._create_new_session(websocket)

                    if initial_message.get("type") == "new_session":
                        # Explicit new session request
                        await self._safe_send({
                            "type": "connection",
                            "session_id": session_id,
                            "message": "New session created! Welcome to the Conversational Planning Agent V2!"
                        }, websocket)
                    else:
                        # Default new session
                        await self._safe_send({
                            "type": "connection",
                            "session_id": session_id,
                            "message": "Welcome to the Conversational Planning Agent V2! I'll help you create and refine plans step by step."
                        }, websocket)

                    await self._safe_send({
                        "type": "agent_message",
                        "message": "Please describe what you'd like me to help you with:"
                    }, websocket)

                    # Handle the initial message if it was a user message
                    if initial_message.get("type") == "user_message":
                        await self._handle_websocket_message(initial_message, websocket, session_id)

                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self._handle_websocket_message(message, websocket, session_id)

            except WebSocketDisconnect:
                self.websocket_manager.disconnect(websocket)
                # Keep session data for potential reconnection
                if session_id and session_id in self.sessions:
                    self.sessions[session_id]["websocket"] = None
                    self.sessions[session_id]["last_disconnect"] = datetime.now().isoformat()
            except Exception as e:
                if websocket in self.websocket_manager.active_connections:
                    try:
                        await self._safe_send({
                            "type": "error",
                            "message": f"Error: {str(e)}"
                        }, websocket)
                    except RuntimeError:
                        self.websocket_manager.disconnect(websocket)

    async def _safe_send(self, message: dict, websocket: WebSocket):
        """Safely send a message to WebSocket."""
        await self.websocket_manager.send_personal_message(message, websocket)

    def _create_new_session(self, websocket: WebSocket) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())[:8]
        self.sessions[session_id] = {
            "phase": "greeting",  # greeting -> text_plan -> text_approval -> code_plan -> code_approval -> completed
            "user_request": "",
            "text_plan": "",
            "python_code": "",
            "conversation_history": [],
            "websocket": websocket,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "reconnections": 0
        }
        print(f"✨ Created new session: {session_id}")
        return session_id

    async def _send_session_state(self, websocket: WebSocket, session_id: str, silent: bool = False):
        """Send current session state to reconnected client."""
        session = self.sessions.get(session_id)
        if not session:
            return

        phase = session["phase"]

        # If silent, restore state and send current plan/code if in approval phase
        if silent:
            # Send state restoration data to frontend
            await self._safe_send({
                "type": "state_restoration",
                "phase": phase,
                "text_plan": session.get("text_plan", ""),
                "python_code": session.get("python_code", ""),
                "user_request": session.get("user_request", "")
            }, websocket)

            # If we're in an approval phase, show the current plan/code
            if phase == "text_plan_approval" and session.get("text_plan"):
                await self._safe_send({
                    "type": "text_plan_review",
                    "plan": session["text_plan"],
                    "message": "Here's your current plan. Please review it:"
                }, websocket)
            elif phase == "code_approval" and session.get("python_code"):
                await self._safe_send({
                    "type": "code_review",
                    "code": session["python_code"],
                    "message": "Here's your current code. Please review it:"
                }, websocket)
            elif phase == "completed":
                await self._safe_send({
                    "type": "completion",
                    "message": "Your task was completed successfully!",
                    "final_plan": session["text_plan"],
                    "final_code": session["python_code"]
                }, websocket)
            return

        # Send appropriate message based on current phase (only when not silent)
        if phase == "text_plan_approval" and session["text_plan"]:
            await self._safe_send({
                "type": "text_plan_review",
                "plan": session["text_plan"],
                "message": "Here's your current plan. Please review it:"
            }, websocket)
        elif phase == "text_plan_feedback":
            await self._safe_send({
                "type": "feedback_request",
                "plan_type": "text",
                "message": "Please provide feedback to improve the text plan:"
            }, websocket)
        elif phase == "code_approval" and session["python_code"]:
            await self._safe_send({
                "type": "code_review",
                "code": session["python_code"],
                "message": "Here's your current code. Please review it:"
            }, websocket)
        elif phase == "code_feedback":
            await self._safe_send({
                "type": "feedback_request",
                "plan_type": "code",
                "message": "Please provide feedback to improve the code:"
            }, websocket)
        elif phase == "completed":
            await self._safe_send({
                "type": "completion",
                "message": "Your task was completed successfully!",
                "final_plan": session["text_plan"],
                "final_code": session["python_code"]
            }, websocket)
        else:
            # Default state - ready for user input
            await self._safe_send({
                "type": "agent_message",
                "message": "What would you like me to help you with?"
            }, websocket)

    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions periodically."""
        while True:
            try:
                current_time = datetime.now()
                expired_sessions = []

                for session_id, session_data in self.sessions.items():
                    # Check if session has been inactive or disconnected for too long
                    last_activity = datetime.fromisoformat(session_data.get("last_activity", session_data["created_at"]))
                    hours_since_activity = (current_time - last_activity).total_seconds() / 3600

                    if hours_since_activity > self.session_timeout_hours:
                        expired_sessions.append(session_id)

                # Remove expired sessions
                for session_id in expired_sessions:
                    print(f"🧹 Cleaning up expired session: {session_id}")
                    del self.sessions[session_id]

                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)

            except Exception as e:
                print(f"❌ Error in session cleanup: {e}")
                await asyncio.sleep(3600)  # Continue trying even if error occurs

    async def _handle_websocket_message(self, message: Dict, websocket: WebSocket, session_id: str):
        """Handle incoming WebSocket messages based on conversation phase."""
        message_type = message.get("type")
        session = self.sessions.get(session_id)

        if not session:
            await self._safe_send({
                "type": "error",
                "message": "Session not found"
            }, websocket)
            return

        # Update last activity timestamp
        session["last_activity"] = datetime.now().isoformat()

        if message_type == "user_message":
            await self._handle_user_message(message, websocket, session_id)
        elif message_type == "approval":
            await self._handle_approval(message, websocket, session_id)
        elif message_type == "feedback":
            await self._handle_feedback(message, websocket, session_id)
        elif message_type == "replan":
            await self._handle_replan(message, websocket, session_id)
        elif message_type == "execute_code":
            await self._handle_code_execution(message, websocket, session_id)
        else:
            await self._safe_send({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }, websocket)

    async def _handle_user_message(self, message: Dict, websocket: WebSocket, session_id: str):
        """Handle user messages based on current phase."""
        user_message = message.get("content", "").strip()
        session = self.sessions[session_id]
        phase = session["phase"]

        if not user_message:
            return

        # Take screenshot
        screenshot = await self._capture_screenshot()

        # Add to conversation history with screenshot
        session["conversation_history"].append({
            "from": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
            "screenshot": screenshot
        })

        # Save conversation after user message
        self._save_conversation_history(session_id)

        if phase == "greeting":
            # Initial request - generate text plan
            session["user_request"] = user_message
            session["phase"] = "text_plan_generation"

            await self._safe_send({
                "type": "status",
                "message": "Generating high-level text plan..."
            }, websocket)

            # Generate text plan
            text_plan = await self._generate_text_plan(user_message)
            session["text_plan"] = text_plan
            session["phase"] = "text_plan_approval"

            # Record text plan generation
            session["conversation_history"].append({
                "from": "system",
                "content": text_plan,
                "timestamp": datetime.now().isoformat()
            })

            # Save conversation after text plan generation
            self._save_conversation_history(session_id)

            await self._safe_send({
                "type": "text_plan_review",
                "plan": text_plan,
                "message": "Here's my high-level plan. Please review it:"
            }, websocket)

        else:
            await self._safe_send({
                "type": "agent_message",
                "message": "I received your message. Please use the approval or feedback buttons to continue."
            }, websocket)

    async def _handle_approval(self, message: Dict, websocket: WebSocket, session_id: str):
        """Handle plan/code approval."""
        approved = message.get("approved", False)
        session = self.sessions[session_id]
        phase = session["phase"]

        if phase == "text_plan_approval":
            if approved:
                # Move to code generation
                session["phase"] = "code_generation"

                # Record plan approval
                session["conversation_history"].append({
                    "from": "user",
                    "content": "text_plan_approved",
                    "timestamp": datetime.now().isoformat()
                })

                # Save conversation after approval
                self._save_conversation_history(session_id)

                await self._safe_send({
                    "type": "status",
                    "message": "Great! Now generating Python code from the plan..."
                }, websocket)

                # Generate code from text plan
                python_code = await self._generate_code(session["text_plan"], session["user_request"])
                session["python_code"] = python_code
                session["phase"] = "code_approval"

                # Record code generation
                session["conversation_history"].append({
                    "from": "system",
                    "content": python_code,
                    "timestamp": datetime.now().isoformat()
                })

                # Save conversation after code generation
                self._save_conversation_history(session_id)

                await self._safe_send({
                    "type": "code_review",
                    "code": python_code,
                    "message": "Here's the generated Python code. Please review it:"
                }, websocket)
            else:
                # Text plan rejected, ask for feedback
                session["phase"] = "text_plan_feedback"
                await self._safe_send({
                    "type": "feedback_request",
                    "plan_type": "text",
                    "message": "I understand you'd like changes to the plan. Please tell me what needs to be improved:"
                }, websocket)

        elif phase == "code_approval":
            if approved:
                # Code approved, task complete
                session["phase"] = "completed"

                # Record code approval
                session["conversation_history"].append({
                    "from": "user",
                    "content": "code_approved",
                    "timestamp": datetime.now().isoformat()
                })

                # Save conversation after approval
                self._save_conversation_history(session_id)

                await self._safe_send({
                    "type": "completion",
                    "message": "Perfect! The plan and code have been approved. You can now save or execute the code.",
                    "final_plan": session["text_plan"],
                    "final_code": session["python_code"]
                }, websocket)
            else:
                # Code rejected, ask for feedback
                session["phase"] = "code_feedback"
                await self._safe_send({
                    "type": "feedback_request",
                    "plan_type": "code",
                    "message": "I understand you'd like changes to the code. Please tell me what needs to be improved:"
                }, websocket)

    async def _handle_feedback(self, message: Dict, websocket: WebSocket, session_id: str):
        """Handle user feedback for plan/code improvement."""
        feedback = message.get("content", "").strip()
        session = self.sessions[session_id]
        phase = session["phase"]

        print(f"🔄 Handling feedback in phase: {phase}, feedback: {feedback[:50]}...")

        if not feedback:
            await self._safe_send({
                "type": "error",
                "message": "Empty feedback received. Please provide feedback."
            }, websocket)
            return

        if phase == "text_plan_feedback":
            # Take screenshot for feedback
            screenshot = await self._capture_screenshot()

            # Record feedback
            session["conversation_history"].append({
                "from": "user",
                "content": feedback,
                "timestamp": datetime.now().isoformat(),
                "screenshot": screenshot
            })

            # Save conversation after feedback
            print(f"💾 Saving conversation after user feedback: {session_id}")
            self._save_conversation_history(session_id)

            # Improve text plan based on feedback
            await self._safe_send({
                "type": "status",
                "message": "Improving the text plan based on your feedback..."
            }, websocket)

            improved_plan = await self._improve_text_plan(session["text_plan"], feedback, session["user_request"])
            session["text_plan"] = improved_plan
            session["phase"] = "text_plan_approval"

            # Record improved plan
            session["conversation_history"].append({
                "from": "system",
                "content": improved_plan,
                "timestamp": datetime.now().isoformat()
            })

            # Save conversation after plan improvement
            print(f"💾 Saving conversation after plan improvement: {session_id}")
            self._save_conversation_history(session_id)

            await self._safe_send({
                "type": "text_plan_review",
                "plan": improved_plan,
                "message": "Here's the improved plan based on your feedback:"
            }, websocket)

        elif phase == "code_feedback":
            # Record feedback (no screenshot for code feedback)
            session["conversation_history"].append({
                "from": "user",
                "content": feedback,
                "timestamp": datetime.now().isoformat()
            })

            # Save conversation after feedback
            print(f"💾 Saving conversation after user feedback: {session_id}")
            self._save_conversation_history(session_id)

            # Improve code based on feedback
            await self._safe_send({
                "type": "status",
                "message": "Improving the Python code based on your feedback..."
            }, websocket)

            improved_code = await self._improve_code(session["python_code"], feedback, session["text_plan"])
            session["python_code"] = improved_code
            session["phase"] = "code_approval"

            # Record improved code
            session["conversation_history"].append({
                "from": "system",
                "content": improved_code,
                "timestamp": datetime.now().isoformat()
            })

            # Save conversation after code improvement
            print(f"💾 Saving conversation after code improvement: {session_id}")
            self._save_conversation_history(session_id)

            await self._safe_send({
                "type": "code_review",
                "code": improved_code,
                "message": "Here's the improved code based on your feedback:"
            }, websocket)

        else:
            # Handle feedback using smart context detection
            print(f"🔄 Auto-detecting feedback context from phase: {phase}")

            # Determine context based on current phase
            if "code" in phase.lower() or phase in ["code_approval", "code_generation"]:
                # We're in a code-related phase, treat as code feedback
                if "python_code" in session and session["python_code"]:
                    print("🐍 Processing code feedback (phase indicates code context)")
                    session["phase"] = "code_feedback"

                    # Record feedback
                    session["conversation_history"].append({
                        "from": "user",
                        "content": feedback,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation after feedback
                    print(f"💾 Saving conversation after user feedback: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "status",
                        "message": "Improving the Python code based on your feedback..."
                    }, websocket)

                    improved_code = await self._improve_code(session["python_code"], feedback, session["text_plan"])
                    session["python_code"] = improved_code
                    session["phase"] = "code_approval"

                    # Record improved code
                    session["conversation_history"].append({
                        "from": "system",
                        "content": improved_code,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation after code improvement
                    print(f"💾 Saving conversation after code improvement: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "code_review",
                        "code": improved_code,
                        "message": "Here's the improved code based on your feedback:"
                    }, websocket)
                else:
                    await self._safe_send({
                        "type": "error",
                        "message": "No code found to improve. Please generate code first."
                    }, websocket)

            elif "text" in phase.lower() or "plan" in phase.lower() or phase in ["text_plan_approval", "text_plan_generation"]:
                # We're in a text plan-related phase, treat as text plan feedback
                if "text_plan" in session and session["text_plan"]:
                    print("📝 Processing text plan feedback (phase indicates plan context)")
                    session["phase"] = "text_plan_feedback"

                    # Take screenshot for text plan feedback
                    screenshot = await self._capture_screenshot()

                    # Record feedback
                    session["conversation_history"].append({
                        "from": "user",
                        "content": feedback,
                        "timestamp": datetime.now().isoformat(),
                        "screenshot": screenshot
                    })

                    # Save conversation after feedback
                    print(f"💾 Saving conversation after user feedback: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "status",
                        "message": "Improving the text plan based on your feedback..."
                    }, websocket)

                    improved_plan = await self._improve_text_plan(session["text_plan"], feedback, session["user_request"])
                    session["text_plan"] = improved_plan
                    session["phase"] = "text_plan_approval"

                    # Record improved plan
                    session["conversation_history"].append({
                        "from": "system",
                        "content": improved_plan,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation after plan improvement
                    print(f"💾 Saving conversation after plan improvement: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "text_plan_review",
                        "plan": improved_plan,
                        "message": "Here's the improved plan based on your feedback:"
                    }, websocket)
                else:
                    await self._safe_send({
                        "type": "error",
                        "message": "No text plan found to improve. Please generate a plan first."
                    }, websocket)

            else:
                # Fallback: check what content is available
                if "python_code" in session and session["python_code"]:
                    # We have code, treat as code feedback
                    print("🐍 Processing code feedback (fallback: has code content)")
                    session["phase"] = "code_feedback"

                    # Record feedback
                    session["conversation_history"].append({
                        "from": "user",
                        "content": feedback,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation after feedback
                    print(f"💾 Saving conversation after user feedback: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "status",
                        "message": "Improving the Python code based on your feedback..."
                    }, websocket)

                    improved_code = await self._improve_code(session["python_code"], feedback, session["text_plan"])
                    session["python_code"] = improved_code
                    session["phase"] = "code_approval"

                    # Record improved code
                    session["conversation_history"].append({
                        "from": "system",
                        "content": improved_code,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation after code improvement
                    print(f"💾 Saving conversation after code improvement: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "code_review",
                        "code": improved_code,
                        "message": "Here's the improved code based on your feedback:"
                    }, websocket)

                elif "text_plan" in session and session["text_plan"]:
                    # We have a text plan, treat as text plan feedback
                    print("📝 Processing text plan feedback (fallback: has plan content)")
                    session["phase"] = "text_plan_feedback"

                    # Take screenshot for text plan feedback
                    screenshot = await self._capture_screenshot()

                    # Record feedback
                    session["conversation_history"].append({
                        "from": "user",
                        "content": feedback,
                        "timestamp": datetime.now().isoformat(),
                        "screenshot": screenshot
                    })

                    # Save conversation after feedback
                    print(f"💾 Saving conversation after user feedback: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "status",
                        "message": "Improving the text plan based on your feedback..."
                    }, websocket)

                    improved_plan = await self._improve_text_plan(session["text_plan"], feedback, session["user_request"])
                    session["text_plan"] = improved_plan
                    session["phase"] = "text_plan_approval"

                    # Record improved plan
                    session["conversation_history"].append({
                        "from": "system",
                        "content": improved_plan,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation after plan improvement
                    print(f"💾 Saving conversation after plan improvement: {session_id}")
                    self._save_conversation_history(session_id)

                    await self._safe_send({
                        "type": "text_plan_review",
                        "plan": improved_plan,
                        "message": "Here's the improved plan based on your feedback:"
                    }, websocket)
                else:
                    # No plan or code to improve
                    await self._safe_send({
                        "type": "error",
                        "message": f"Cannot process feedback in current phase: {phase}. Please start with a new request or approve/reject the current plan/code."
                    }, websocket)

    async def _handle_replan(self, message: Dict, websocket: WebSocket, session_id: str):
        """Handle replanning requests."""
        plan_type = message.get("plan_type", "text")  # "text" or "code"
        session = self.sessions[session_id]

        if plan_type == "text":
            # Restart from text planning
            session["phase"] = "text_plan_generation"
            session["text_plan"] = ""
            session["python_code"] = ""

            await self._safe_send({
                "type": "status",
                "message": "Replanning from scratch. Generating new high-level text plan..."
            }, websocket)

            text_plan = await self._generate_text_plan(session["user_request"])
            session["text_plan"] = text_plan
            session["phase"] = "text_plan_approval"

            await self._safe_send({
                "type": "text_plan_review",
                "plan": text_plan,
                "message": "Here's a completely new high-level plan:"
            }, websocket)

        elif plan_type == "code":
            # Restart from code generation
            session["phase"] = "code_generation"
            session["python_code"] = ""

            await self._safe_send({
                "type": "status",
                "message": "Regenerating Python code from the approved text plan..."
            }, websocket)

            python_code = await self._generate_code(session["text_plan"], session["user_request"])
            session["python_code"] = python_code
            session["phase"] = "code_approval"

            await self._safe_send({
                "type": "code_review",
                "code": python_code,
                "message": "Here's freshly generated Python code:"
            }, websocket)

    async def _handle_code_execution(self, message: Dict, websocket: WebSocket, session_id: str):
        """Handle code execution requests."""
        session = self.sessions[session_id]
        python_code = session.get("python_code", "")

        print(f"🚀 Code execution requested for session {session_id}")

        if not python_code:
            await self._safe_send({
                "type": "error",
                "message": "No code found to execute. Please generate code first."
            }, websocket)
            return

        await self._safe_send({
            "type": "status",
            "message": "🚀 Executing generated code..."
        }, websocket)

        try:
            # Execute the code in a controlled environment
            execution_result = await self._execute_python_code(python_code, session)

            # Send execution results
            result_message = {
                "type": "execution_result",
                "success": execution_result["success"],
                "output": execution_result["output"],
                "error": execution_result["error"],
                "execution_time": execution_result["execution_time"],
                "message": "Code execution completed!"
            }

            # Add JSON-specific fields if available
            if "json_result" in execution_result:
                result_message.update({
                    "task_done": execution_result["task_done"],
                    "task_messages": execution_result["task_messages"],
                    "task_context": execution_result["task_context"],
                    "json_result": execution_result["json_result"]
                })

                # Update message based on task completion status
                if execution_result["task_done"]:
                    result_message["message"] = "✅ Task completed successfully!"
                else:
                    result_message["message"] = "⚠️ Task requires replanning"

            await self._safe_send(result_message, websocket)

            # Send task messages as separate user-facing messages if available
            if "json_result" in execution_result and execution_result["task_messages"]:
                for task_message in execution_result["task_messages"]:
                    await self._safe_send({
                        "type": "agent_message",
                        "message": task_message
                    }, websocket)

            # Log execution
            print(f"✅ Code execution completed for session {session_id}: success={execution_result['success']}")

        except Exception as e:
            error_msg = f"Error executing code: {str(e)}"
            print(f"❌ {error_msg}")

            await self._safe_send({
                "type": "execution_result",
                "success": False,
                "output": "",
                "error": error_msg,
                "execution_time": 0,
                "message": "Code execution failed!"
            }, websocket)

    async def _generate_text_plan(self, user_request: str) -> str:
        """Generate high-level text plan."""
        try:
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            text_plan = await loop.run_in_executor(
                None,
                generate_text_plan_internlm,
                user_request,
                self.api_url,
                self.api_key,
                True,  # include_screenshot
                False,  # stream
                None   # screenshot_file
            )
            return text_plan
        except Exception as e:
            return f"Error generating text plan: {str(e)}"

    async def _improve_text_plan(self, original_plan: str, feedback: str, user_request: str) -> str:
        """Improve text plan based on feedback."""
        try:
            # Combine feedback into the refinement process
            improvement_prompt = f"Original plan:\n{original_plan}\n\nUser feedback:\n{feedback}\n"

            loop = asyncio.get_event_loop()
            improved_plan = await loop.run_in_executor(
                None,
                refine_plan_internlm,
                improvement_prompt,
                self.api_url,
                self.api_key,
                True,  # include_screenshot - enabled for plan improvement with feedback
                False,  # stream
                None   # screenshot_file
            )
            return improved_plan
        except Exception as e:
            return f"Error improving text plan: {str(e)}"

    async def _generate_code(self, text_plan: str, user_request: str) -> str:
        """Generate Python code from text plan."""
        try:
            loop = asyncio.get_event_loop()
            python_code = await loop.run_in_executor(
                None,
                plan_to_code_internlm,
                text_plan,
                user_request,
                self.api_url,
                self.api_key,
                False,  # include_screenshot - commented out for code generation
                False,  # stream
                None   # screenshot_file
            )
            return python_code
        except Exception as e:
            return f"Error generating code: {str(e)}"

    async def _improve_code(self, original_code: str, feedback: str, text_plan: str) -> str:
        """Improve Python code based on feedback using dedicated code improvement API."""
        try:
            improved_code = await self._improve_code_internlm(original_code, feedback, text_plan)
            return improved_code
        except Exception as e:
            return f"Error improving code: {str(e)}"

    async def _improve_code_internlm(self, original_code: str, feedback: str, text_plan: str) -> str:
        """Improve Python code using InternLM API with specialized code improvement prompt."""
        import requests

        # Create a specialized code improvement prompt
        improvement_prompt = f"""You are a code improvement specialist. Improve the given Python code based on user feedback. Only make the required changes, don't change anything else.
High Level Plan:
{text_plan}

ORIGINAL CODE:
```python
{original_code}
```

USER FEEDBACK:
{feedback}

Available tools:
- tools.focus_window(name): Focus window by name (e.g., "chrome", "firefox")
- tools.hotkey(keys): Send keyboard shortcuts (e.g., "ctrl+t", "ctrl+w", "enter", "escape")
- tools.type(text): Type the specified text
- tools.click(x, y): Click at coordinates (use floats 0-1 for relative positioning)
- tools.move_to(x, y): Move mouse to coordinates (use floats 0-1 for relative positioning)
- tools.query_screen(query): Ask questions about screen content
- tools.run_shell_command(args): Execute shell commands
- tools.add(a, b): Add two numbers

Rules:
1. Return False from main function to trigger replanning. This can be used as a fallback in error scenarios.
2. Return True from main function to indicate task completion.


"""

        # Prepare API request
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = {
            "model": "internvl3.5-241b-a28b",
            "messages": [
                {
                    "role": "user",
                    "content": improvement_prompt
                }
            ],
            "stream": False,
            "temperature": 0.2  # Lower temperature for more consistent code improvements
        }

        # Make API request in executor to avoid blocking
        loop = asyncio.get_event_loop()

        def make_request():
            response = requests.post(f"{self.api_url}/v1/chat/completions",
                                   headers=headers, json=data, timeout=120)

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")

            result = response.json()

            if 'choices' not in result or not result['choices']:
                raise Exception("No response from API")

            return result['choices'][0]['message']['content'].strip()

        improved_code = await loop.run_in_executor(None, make_request)
        return improved_code

    def _extract_code_from_markdown(self, response: str) -> str:
        """Extract Python code from markdown blocks in the response."""
        # Try to extract code from markdown blocks
        if '```python' in response:
            code = response.split('```python')[1].split('```')[0].strip()
        elif '```' in response:
            code = response.split('```')[1].split('```')[0].strip()
        else:
            # If no code blocks found, return the whole response
            code = response.strip()

        # Ensure it starts with import if it's valid Python code
        if code and not code.startswith('#') and not code.startswith('import'):
            if 'tools.' in code:
                code = 'import tools\n' + code

        return code

    async def _execute_python_code(self, python_code: str, session: Dict) -> Dict:
        """Execute Python code in a controlled environment using exec()."""
        import time
        import io
        import sys
        import contextlib

        start_time = time.time()

        try:
            # Extract code from markdown blocks if present
            code_to_execute = self._extract_code_from_markdown(python_code)
            print(f"🐍 Original code length: {len(python_code)} characters")
            print(f"🐍 Extracted code length: {len(code_to_execute)} characters")
            print(f"🔍 Checking for main function definition...")

            if 'def main(' in code_to_execute:
                print(f"✅ Found main function definition")
            else:
                print(f"⚠️ No main function definition found")

            print(f"🐍 Final code length: {len(code_to_execute)} characters")
            print(f"📄 Code to execute:")
            print("-" * 60)
            print(code_to_execute)
            print("-" * 60)

            # Create a custom scope for execution
            scope = {}

            # Capture stdout and stderr during execution
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                print(f"🚀 Executing Python code using exec()...")

                # Execute the code in the custom scope with captured output
                with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                    exec(code_to_execute, scope)

                execution_time = time.time() - start_time
                print(f"⏱️ Execution completed in {execution_time:.2f}s")

                captured_stdout = stdout_capture.getvalue()
                captured_stderr = stderr_capture.getvalue()

                print(f"📤 STDOUT ({len(captured_stdout)} chars):")
                print(captured_stdout)
                print(f"⚠️ STDERR ({len(captured_stderr)} chars):")
                print(captured_stderr)

                # Check if main function exists in scope and call it directly
                if 'main' in scope and callable(scope['main']):
                    print(f"✅ Found main function in scope, calling it directly...")
                    try:
                        result = scope['main']()
                        print(f"✅ Main function returned: {result}")

                        # Validate the expected structure
                        if isinstance(result, dict):
                            required_keys = ['messages', 'context', 'done']
                            has_all_keys = all(key in result for key in required_keys)
                            print(f"🔍 Result validation - has all keys {required_keys}: {has_all_keys}")

                            if has_all_keys:
                                print(f"✅ Result structure is valid")
                                return {
                                    "success": True,
                                    "output": captured_stdout,
                                    "error": captured_stderr if captured_stderr else None,
                                    "execution_time": round(execution_time, 2),
                                    "json_result": result,
                                    "task_done": result.get('done', False),
                                    "task_messages": result.get('messages', []),
                                    "task_context": result.get('context', [])
                                }
                            else:
                                print(f"⚠️ Result doesn't have expected structure, treating as regular output")
                                return {
                                    "success": True,
                                    "output": captured_stdout,
                                    "error": captured_stderr if captured_stderr else None,
                                    "execution_time": round(execution_time, 2),
                                    "result": result
                                }
                        else:
                            print(f"⚠️ Main function didn't return a dict, treating as regular output")
                            return {
                                "success": True,
                                "output": captured_stdout,
                                "error": captured_stderr if captured_stderr else None,
                                "execution_time": round(execution_time, 2),
                                "result": result
                            }
                    except Exception as e:
                        print(f"❌ Error calling main function: {e}")
                        return {
                            "success": False,
                            "output": captured_stdout,
                            "error": f"Error calling main function: {str(e)}",
                            "execution_time": round(execution_time, 2)
                        }
                else:
                    # No main function found, just return the captured output
                    print(f"⚠️ No callable main function found in scope")
                    return {
                        "success": True,
                        "output": captured_stdout,
                        "error": captured_stderr if captured_stderr else None,
                        "execution_time": round(execution_time, 2)
                    }
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"❌ Error during code execution: {e}")
                return {
                    "success": False,
                    "output": stdout_capture.getvalue(),
                    "error": f"Code execution error: {str(e)}",
                    "execution_time": round(execution_time, 2)
                }

        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Unexpected error: {e}")
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}",
                "execution_time": round(execution_time, 2)
            }

    def _generate_unique_filename(self, extension: str = "png") -> str:
        """Generate a unique filename with random characters."""
        # Generate 16 random characters (letters + digits)
        random_chars = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{random_chars}.{extension}"

    async def _capture_screenshot(self) -> Optional[str]:
        """Capture screenshot and save it with unique filename."""
        try:
            import subprocess

            filename = self._generate_unique_filename("png")
            screenshot_path = self.screenshots_dir / filename

            # Use different screenshot tools based on system
            try:
                # Try with gnome-screenshot first (Linux)
                result = subprocess.run([
                    'gnome-screenshot', '-f', str(screenshot_path)
                ], capture_output=True, timeout=10)

                if result.returncode == 0 and screenshot_path.exists():
                    print(f"📸 Screenshot saved: {filename}")
                    return filename
            except:
                pass

            try:
                # Try with scrot (Linux)
                result = subprocess.run([
                    'scrot', str(screenshot_path)
                ], capture_output=True, timeout=10)

                if result.returncode == 0 and screenshot_path.exists():
                    print(f"📸 Screenshot saved: {filename}")
                    return filename
            except:
                pass

            try:
                # Try with import (ImageMagick)
                result = subprocess.run([
                    'import', '-window', 'root', str(screenshot_path)
                ], capture_output=True, timeout=10)

                if result.returncode == 0 and screenshot_path.exists():
                    print(f"📸 Screenshot saved: {filename}")
                    return filename
            except:
                pass

            print("⚠️ Screenshot capture failed - no suitable tool found")
            return None

        except Exception as e:
            print(f"❌ Screenshot capture error: {e}")
            return None

    def _save_conversation_history(self, session_id: str):
        """Save conversation history to JSON file."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                print(f"❌ Save failed: session {session_id} not found")
                return

            print(f"💾 Saving session {session_id} with {len(session.get('conversation_history', []))} messages")

            conversation_data = {
                "session_id": session_id,
                "created_at": session.get("created_at"),
                "last_activity": session.get("last_activity"),
                "user_request": session.get("user_request", ""),
                "text_plan": session.get("text_plan", ""),
                "python_code": session.get("python_code", ""),
                "reconnections": session.get("reconnections", 0),
                "conversation_history": session.get("conversation_history", []),
                "screenshots": session.get("screenshots", []),
                "execution_results": session.get("execution_results", []),
                "feedback_history": session.get("feedback_history", []),
                "metadata": {
                    "agent_version": "2.0.0",
                    "api_url": self.api_url,
                    "total_messages": len(session.get("conversation_history", [])),
                    "has_text_plan": bool(session.get("text_plan")),
                    "has_code": bool(session.get("python_code")),
                    "saved_at": datetime.now().isoformat()
                }
            }

            # Save to file with session ID as filename
            conversation_file = self.conversations_dir / f"{session_id}.json"
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)

            print(f"💾 Conversation saved: {session_id}.json")

        except Exception as e:
            print(f"❌ Error saving conversation: {e}")


    def _get_html_content(self) -> str:
        """Return the HTML content for the web interface."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversational Planning Agent V2</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        .chat-container {
            height: 500px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #fafafa;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 6px;
        }
        .user-message {
            background-color: #007bff;
            color: white;
            margin-left: 20%;
        }
        .agent-message {
            background-color: #e9ecef;
            color: #333;
            margin-right: 20%;
        }
        .status-message {
            background-color: #fff3cd;
            color: #856404;
            font-style: italic;
        }
        .error-message {
            background-color: #f8d7da;
            color: #721c24;
        }
        .plan-review {
            background-color: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }
        .code-review {
            background-color: #d1ecf1;
            color: #0c5460;
            border-left: 4px solid #17a2b8;
        }
        .feedback-request {
            background-color: #fff3cd;
            color: #856404;
            border-left: 4px solid #ffc107;
        }
        .completion {
            background-color: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
            font-weight: bold;
        }
        .input-container {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .input-field {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .send-button {
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .send-button:hover {
            background-color: #0056b3;
        }
        .send-button:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        .action-buttons {
            margin-top: 10px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .approve-button, .reject-button, .feedback-button, .replan-button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .approve-button {
            background-color: #28a745;
            color: white;
        }
        .reject-button {
            background-color: #dc3545;
            color: white;
        }
        .feedback-button {
            background-color: #ffc107;
            color: #212529;
        }
        .replan-button {
            background-color: #6f42c1;
            color: white;
        }
        .code-block {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        .plan-block {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 15px;
            margin: 10px 0;
            white-space: pre-wrap;
        }
        .connection-status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        .session-info {
            position: fixed;
            top: 40px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 11px;
            background-color: #e9ecef;
            color: #495057;
        }
        .session-controls {
            position: fixed;
            top: 70px;
            right: 10px;
            display: flex;
            gap: 5px;
        }
        .session-button {
            padding: 4px 8px;
            font-size: 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            background-color: #6c757d;
            color: white;
        }
        .session-button:hover {
            background-color: #5a6268;
        }
        .new-session-button {
            background-color: #28a745;
        }
        .new-session-button:hover {
            background-color: #218838;
        }
        .connected {
            background-color: #d4edda;
            color: #155724;
        }
        .disconnected {
            background-color: #f8d7da;
            color: #721c24;
        }
        .feedback-input {
            width: 100%;
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            min-height: 80px;
            resize: vertical;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">Connecting...</div>
    <div class="session-info" id="sessionInfo">No session</div>
    <div class="session-controls">
        <button class="session-button new-session-button" onclick="startNewSession()" title="Start a completely new session">
            🆕 New
        </button>
        <button class="session-button" onclick="clearSessionData()" title="Clear session data and refresh">
            🗑️ Clear
        </button>
    </div>

    <div class="container">
        <div class="header">
            <h1>🤖 Conversational Planning Agent V2</h1>
            <p>Interactive planning with high-level plans, code generation, and iterative improvement</p>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="message agent-message">
                Welcome to the Conversational Planning Agent V2!<br><br>
                I'll help you create plans through conversation:
                <ol>
                    <li><strong>High-level Plan:</strong> I'll generate a text plan for your request</li>
                    <li><strong>Plan Review:</strong> You can approve, provide feedback, or request replanning</li>
                    <li><strong>Code Generation:</strong> Once approved, I'll generate Python code</li>
                    <li><strong>Code Review:</strong> You can approve, provide feedback, or regenerate</li>
                </ol>
                Let's start! What would you like me to help you with?
            </div>
        </div>

        <div class="input-container">
            <input type="text" id="messageInput" class="input-field"
                   placeholder="Describe what you want me to help you with..."
                   onkeypress="handleKeyPress(event)">
            <button id="sendButton" class="send-button" onclick="sendMessage()">Send</button>
        </div>

        <div id="feedbackContainer" class="hidden">
            <textarea id="feedbackInput" class="feedback-input"
                     placeholder="Please describe what needs to be improved..."
                     onkeypress="handleFeedbackKeyPress(event)"></textarea>
            <div style="margin-top: 10px;">
                <button id="submitFeedbackButton" onclick="sendFeedback()" class="feedback-button">Submit Feedback</button>
                <button onclick="cancelFeedback()" class="reject-button">Cancel</button>
                <button onclick="debugFeedbackInput()" class="session-button" style="margin-left: 10px;">🔍 Debug</button>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let connected = false;
        let sessionId = null;
        let currentPhase = "greeting";
        let pendingApprovalType = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = function(event) {
                connected = true;
                updateConnectionStatus();

                // Check if we should force a new session (sessionId was cleared)
                const savedSessionId = localStorage.getItem('agentSessionId');
                const forceNewSession = window.forceNewSession || false;
                window.forceNewSession = false; // Reset flag

                if (savedSessionId && !forceNewSession) {
                    console.log(`Attempting to resume session: ${savedSessionId}`);
                    ws.send(JSON.stringify({
                        type: 'resume_session',
                        session_id: savedSessionId
                    }));
                } else {
                    console.log('Starting new session');
                    ws.send(JSON.stringify({
                        type: 'new_session'
                    }));
                }
            };

            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                handleMessage(message);
            };

            ws.onclose = function(event) {
                connected = false;
                updateConnectionStatus();
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                connected = false;
                updateConnectionStatus();
            };
        }

        function updateConnectionStatus() {
            const statusEl = document.getElementById('connectionStatus');
            const sessionEl = document.getElementById('sessionInfo');

            if (connected) {
                statusEl.textContent = 'Connected';
                statusEl.className = 'connection-status connected';
            } else {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'connection-status disconnected';
            }

            if (sessionId) {
                sessionEl.textContent = `Session: ${sessionId}`;
            } else {
                sessionEl.textContent = 'No session';
            }
        }

        function handleMessage(message) {
            const chatContainer = document.getElementById('chatContainer');
            const messageEl = document.createElement('div');

            switch (message.type) {
                case 'connection':
                    sessionId = message.session_id;
                    localStorage.setItem('agentSessionId', sessionId);
                    updateConnectionStatus();
                    messageEl.className = 'message agent-message';
                    messageEl.textContent = message.message;
                    break;

                case 'session_resumed':
                    sessionId = message.session_id;
                    localStorage.setItem('agentSessionId', sessionId);
                    updateConnectionStatus();

                    // Only show message if not silent
                    if (!message.silent) {
                        messageEl.className = 'message status-message';
                        messageEl.innerHTML = `✅ ${message.message}`;
                    } else {
                        // Silent resumption - don't add any message to chat
                        return; // Exit early, don't append messageEl
                    }
                    break;

                case 'session_not_found':
                    sessionId = message.session_id;
                    localStorage.setItem('agentSessionId', sessionId);
                    updateConnectionStatus();
                    messageEl.className = 'message status-message';
                    messageEl.innerHTML = `⚠️ ${message.message}`;
                    break;

                case 'agent_message':
                    messageEl.className = 'message agent-message';
                    messageEl.textContent = message.message;
                    break;

                case 'status':
                    messageEl.className = 'message status-message';
                    messageEl.textContent = message.message;
                    break;

                case 'error':
                    messageEl.className = 'message error-message';
                    messageEl.textContent = message.message;
                    break;

                case 'text_plan_review':
                    currentPhase = 'text_plan_approval';
                    pendingApprovalType = 'text';
                    saveSessionState();
                    messageEl.className = 'message plan-review';
                    messageEl.innerHTML = `
                        <strong>${message.message}</strong>
                        <div class="plan-block">${message.plan}</div>
                        <div class="action-buttons">
                            <button class="approve-button" onclick="sendApproval(true)">✅ Approve Plan</button>
                            <button class="reject-button" onclick="requestFeedback()">❌ Request Changes</button>
                            <button class="replan-button" onclick="requestReplan('text')">🔄 Generate New Plan</button>
                        </div>
                    `;
                    break;

                case 'code_review':
                    currentPhase = 'code_approval';
                    pendingApprovalType = 'code';
                    saveSessionState();
                    messageEl.className = 'message code-review';
                    messageEl.innerHTML = `
                        <strong>${message.message}</strong>
                        <div class="code-block">${message.code}</div>
                        <div class="action-buttons">
                            <button class="approve-button" onclick="sendApproval(true)">✅ Approve Code</button>
                            <button class="reject-button" onclick="requestFeedback()">❌ Request Changes</button>
                            <button class="replan-button" onclick="requestReplan('code')">🔄 Generate New Code</button>
                        </div>
                    `;
                    break;

                case 'feedback_request':
                    messageEl.className = 'message feedback-request';
                    messageEl.innerHTML = `
                        <strong>${message.message}</strong>
                        <p>Use the feedback form below to describe your changes.</p>
                    `;
                    showFeedbackForm();
                    break;

                case 'completion':
                    currentPhase = 'completed';
                    saveSessionState();
                    messageEl.className = 'message completion';
                    messageEl.innerHTML = `
                        <strong>🎉 ${message.message}</strong>
                        <details style="margin-top: 10px;">
                            <summary><strong>Final Plan</strong></summary>
                            <div class="plan-block">${message.final_plan}</div>
                        </details>
                        <details style="margin-top: 10px;">
                            <summary><strong>Final Code</strong></summary>
                            <div class="code-block">${message.final_code}</div>
                        </details>
                        <div class="action-buttons" style="margin-top: 15px;">
                            <button class="approve-button" onclick="executeCode()">🚀 Execute Code</button>
                            <button class="feedback-button" onclick="startNewSession()">🆕 Start New Task</button>
                        </div>
                    `;
                    break;

                case 'state_restoration':
                    // Silently restore UI state based on current phase
                    currentPhase = message.phase;
                    saveSessionState();

                    // Restore UI elements based on phase without showing messages
                    if (message.phase === 'text_plan_approval' && message.text_plan) {
                        pendingApprovalType = 'text';
                        // Could add UI elements here silently if needed
                    } else if (message.phase === 'code_approval' && message.python_code) {
                        pendingApprovalType = 'code';
                        // Could add UI elements here silently if needed
                    } else if (message.phase === 'text_plan_feedback') {
                        showFeedbackForm();
                    } else if (message.phase === 'code_feedback') {
                        showFeedbackForm();
                    }

                    // Don't append any message element for state restoration
                    return;

                case 'execution_result':
                    messageEl.className = message.success ? 'message completion' : 'message error-message';
                    let resultContent = `<strong>${message.success ? '✅' : '❌'} ${message.message}</strong>`;

                    if (message.execution_time !== undefined) {
                        resultContent += `<p><strong>⏱️ Execution time:</strong> ${message.execution_time}s</p>`;
                    }

                    // Display task messages if available (from JSON result)
                    if (message.task_messages && message.task_messages.length > 0) {
                        resultContent += `
                            <details style="margin-top: 10px;" open>
                                <summary><strong>📋 Task Messages</strong></summary>
                                <div class="plan-block">`;
                        message.task_messages.forEach(msg => {
                            resultContent += `• ${msg}<br>`;
                        });
                        resultContent += `</div>
                            </details>
                        `;
                    }

                    // Display task context if available (from JSON result)
                    if (message.task_context && message.task_context.length > 0) {
                        resultContent += `
                            <details style="margin-top: 10px;">
                                <summary><strong>🗂️ Task Context</strong></summary>
                                <div class="plan-block">`;
                        message.task_context.forEach(ctx => {
                            resultContent += `• ${ctx}<br>`;
                        });
                        resultContent += `</div>
                            </details>
                        `;
                    }

                    // Display raw output if available
                    if (message.output) {
                        resultContent += `
                            <details style="margin-top: 10px;">
                                <summary><strong>📤 Raw Output</strong></summary>
                                <div class="code-block">${message.output}</div>
                            </details>
                        `;
                    }

                    if (message.error) {
                        resultContent += `
                            <details style="margin-top: 10px;">
                                <summary><strong>⚠️ Error/Warning</strong></summary>
                                <div class="code-block" style="color: #dc3545;">${message.error}</div>
                            </details>
                        `;
                    }

                    if (message.success) {
                        // Check if task is done (from JSON result)
                        if (message.task_done === false) {
                            // Task needs replanning
                            resultContent += `
                                <div class="action-buttons" style="margin-top: 15px;">
                                    <button class="replan-button" onclick="requestReplan('code')">🔄 Replan & Generate New Code</button>
                                    <button class="feedback-button" onclick="requestFeedback()">💬 Provide Feedback</button>
                                    <button class="approve-button" onclick="executeCode()">🔄 Run Again</button>
                                    <button class="feedback-button" onclick="startNewSession()">🆕 Start New Task</button>
                                </div>
                            `;
                        } else {
                            // Task completed successfully
                            resultContent += `
                                <div class="action-buttons" style="margin-top: 15px;">
                                    <button class="approve-button" onclick="executeCode()">🔄 Run Again</button>
                                    <button class="feedback-button" onclick="startNewSession()">🆕 Start New Task</button>
                                </div>
                            `;
                        }
                    } else {
                        resultContent += `
                            <div class="action-buttons" style="margin-top: 15px;">
                                <button class="reject-button" onclick="executeCode()">🔄 Try Again</button>
                                <button class="feedback-button" onclick="startNewSession()">🆕 Start New Task</button>
                            </div>
                        `;
                    }

                    messageEl.innerHTML = resultContent;
                    break;

                default:
                    messageEl.className = 'message agent-message';
                    messageEl.textContent = JSON.stringify(message);
            }

            chatContainer.appendChild(messageEl);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function sendMessage() {
            const input = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const message = input.value.trim();

            if (!message || !connected) return;

            // Add user message to chat
            const chatContainer = document.getElementById('chatContainer');
            const userMessageEl = document.createElement('div');
            userMessageEl.className = 'message user-message';
            userMessageEl.textContent = message;
            chatContainer.appendChild(userMessageEl);

            // Send to server
            ws.send(JSON.stringify({
                type: 'user_message',
                content: message
            }));

            // Save session state after user interaction
            saveSessionState();

            // Clear input and disable button temporarily
            input.value = '';
            sendButton.disabled = true;
            setTimeout(() => { sendButton.disabled = false; }, 1000);

            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function sendApproval(approved) {
            ws.send(JSON.stringify({
                type: 'approval',
                approved: approved
            }));
            saveSessionState();
        }

        function requestFeedback() {
            console.log('💭 requestFeedback called');
            showFeedbackForm();
        }

        // Add flag to prevent double submission
        let feedbackSubmitting = false;

        function sendFeedback() {
            console.log('🔍 === SEND FEEDBACK START ===');

            // Prevent double submission
            if (feedbackSubmitting) {
                console.log('⚠️ Feedback already being submitted, ignoring');
                return;
            }

            const feedbackInput = document.getElementById('feedbackInput');

            if (!feedbackInput) {
                console.error('❌ Feedback input element not found');
                return;
            }

            // Get feedback text - simple and direct
            let feedback = feedbackInput.value || '';
            feedback = feedback.trim();

            console.log('📤 Sending feedback:', `"${feedback}"`);

            // If empty, provide default message
            if (!feedback) {
                feedback = 'No specific feedback provided';
            }

            // Set flag to prevent double submission
            feedbackSubmitting = true;

            submitFeedbackToServer(feedback, feedbackInput);
        }

        function submitFeedbackToServer(feedback, feedbackInput) {
            console.log('📤 === SUBMITTING TO SERVER ===');
            console.log('📤 Feedback to send:', `"${feedback}"`);

            if (!connected || !ws) {
                alert('Not connected to server. Please wait for connection to restore.');
                return;
            }

            try {
                console.log('📤 Sending feedback to server...');

                // Add feedback message to chat immediately for user feedback
                const chatContainer = document.getElementById('chatContainer');
                const feedbackMsg = document.createElement('div');
                feedbackMsg.className = 'message user-message';
                feedbackMsg.textContent = `💬 Feedback: ${feedback}`;
                chatContainer.appendChild(feedbackMsg);

                const message = {
                    type: 'feedback',
                    content: feedback
                };

                console.log('📤 WebSocket message:', message);
                ws.send(JSON.stringify(message));

                saveSessionState();

                // Clear the input
                console.log('🧹 Clearing feedback input');
                feedbackInput.value = '';

                hideFeedbackForm();

                // Show status message
                const statusMsg = document.createElement('div');
                statusMsg.className = 'message status-message';
                statusMsg.textContent = '📝 Feedback submitted. Processing improvements...';
                chatContainer.appendChild(statusMsg);

                chatContainer.scrollTop = chatContainer.scrollHeight;

                console.log('✅ Feedback sent successfully');
            } catch (error) {
                console.error('❌ Error sending feedback:', error);
                alert(`Error sending feedback: ${error.message}. Please try again.`);
            } finally {
                // Reset flag to allow future submissions
                feedbackSubmitting = false;
            }
        }

        function cancelFeedback() {
            hideFeedbackForm();
        }

        function requestReplan(planType) {
            ws.send(JSON.stringify({
                type: 'replan',
                plan_type: planType
            }));
        }

        function showFeedbackForm() {
            console.log('📝 showFeedbackForm called');
            const feedbackContainer = document.getElementById('feedbackContainer');
            const feedbackInput = document.getElementById('feedbackInput');

            if (feedbackContainer) {
                feedbackContainer.classList.remove('hidden');
                console.log('✅ Feedback form shown');
            } else {
                console.error('❌ feedbackContainer element not found');
            }

            if (feedbackInput) {
                feedbackInput.focus();
                console.log('✅ Feedback input focused');
            } else {
                console.error('❌ feedbackInput element not found');
            }
        }

        function hideFeedbackForm() {
            console.log('🙈 hideFeedbackForm called');
            const feedbackContainer = document.getElementById('feedbackContainer');

            if (feedbackContainer) {
                feedbackContainer.classList.add('hidden');
                console.log('✅ Feedback form hidden');
            } else {
                console.error('❌ feedbackContainer element not found');
            }
        }

        function executeCode() {
            console.log('🚀 Execute code requested');

            if (!connected || !ws) {
                alert('Not connected to server. Please wait for connection to restore.');
                return;
            }

            // Show confirmation dialog
            const confirmExecution = confirm(
                '⚠️ Execute Generated Code?\\n\\n' +
                'This will run the generated Python code on the server.\\n' +
                'The code will have access to system tools and may perform actions.\\n\\n' +
                'Are you sure you want to execute it?'
            );

            if (!confirmExecution) {
                console.log('🛑 Code execution cancelled by user');
                return;
            }

            try {
                console.log('🚀 Sending code execution request');

                // Add execution request message to chat
                const chatContainer = document.getElementById('chatContainer');
                const execMsg = document.createElement('div');
                execMsg.className = 'message user-message';
                execMsg.textContent = '🚀 Execute Code';
                chatContainer.appendChild(execMsg);

                // Send execution request to server
                ws.send(JSON.stringify({
                    type: 'execute_code'
                }));

                // Show status message
                const statusMsg = document.createElement('div');
                statusMsg.className = 'message status-message';
                statusMsg.textContent = '⏳ Executing code... Please wait for results.';
                chatContainer.appendChild(statusMsg);

                chatContainer.scrollTop = chatContainer.scrollHeight;

                console.log('✅ Code execution request sent');
            } catch (error) {
                console.error('❌ Error requesting code execution:', error);
                alert(`Error requesting code execution: ${error.message}`);
            }
        }

        function startNewConversation() {
            // This is the old function, now replaced by startNewSession
            startNewSession();
        }

        function startNewSession() {
            // Force create a new session by clearing data and reconnecting
            console.log('🆕 Starting new session...');

            // Clear all session data
            localStorage.removeItem('agentSessionId');
            localStorage.removeItem('agentPhase');
            localStorage.removeItem('agentLastActivity');

            sessionId = null;
            currentPhase = "greeting";
            pendingApprovalType = null;

            // Clear chat container
            document.getElementById('chatContainer').innerHTML = `
                <div class="message agent-message">
                    Welcome to the Conversational Planning Agent V2!<br><br>
                    I'll help you create plans through conversation:
                    <ol>
                        <li><strong>High-level Plan:</strong> I'll generate a text plan for your request</li>
                        <li><strong>Plan Review:</strong> You can approve, provide feedback, or request replanning</li>
                        <li><strong>Code Generation:</strong> Once approved, I'll generate Python code</li>
                        <li><strong>Code Review:</strong> You can approve, provide feedback, or regenerate</li>
                    </ol>
                    Let's start! What would you like me to help you with?
                </div>
            `;

            // Hide feedback form
            hideFeedbackForm();

            // Update UI
            updateConnectionStatus();

            // Set flag to force new session
            window.forceNewSession = true;

            // Close existing connection and reconnect
            if (ws) {
                ws.close();
            }
            connectWebSocket();

            // Show confirmation
            setTimeout(() => {
                const chatContainer = document.getElementById('chatContainer');
                const confirmMsg = document.createElement('div');
                confirmMsg.className = 'message status-message';
                confirmMsg.innerHTML = '✨ New session started! Previous conversation data cleared.';
                chatContainer.appendChild(confirmMsg);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }, 1000);
        }

        function clearSessionData() {
            // Clear session data and refresh the page
            console.log('🗑️ Clearing session data...');

            localStorage.removeItem('agentSessionId');
            localStorage.removeItem('agentPhase');
            localStorage.removeItem('agentLastActivity');

            // Show confirmation and refresh
            if (confirm('This will clear all session data and refresh the page. Continue?')) {
                location.reload();
            }
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        function handleFeedbackKeyPress(event) {
            // Ctrl+Enter or Shift+Enter to submit feedback
            if ((event.ctrlKey || event.shiftKey) && event.key === 'Enter') {
                event.preventDefault();
                sendFeedback();
            }
        }

        function debugFeedbackInput() {
            const feedbackInput = document.getElementById('feedbackInput');
            console.log('🔍 === FEEDBACK DEBUG INFO ===');
            console.log('Element:', feedbackInput);
            console.log('Element type:', feedbackInput ? feedbackInput.tagName : 'NULL');
            console.log('Value:', feedbackInput ? feedbackInput.value : 'NULL');
            console.log('Value length:', feedbackInput ? feedbackInput.value.length : 'NULL');
            console.log('TextContent:', feedbackInput ? feedbackInput.textContent : 'NULL');
            console.log('InnerText:', feedbackInput ? feedbackInput.innerText : 'NULL');
            console.log('InnerHTML:', feedbackInput ? feedbackInput.innerHTML : 'NULL');
            console.log('Placeholder:', feedbackInput ? feedbackInput.placeholder : 'NULL');
            console.log('Disabled:', feedbackInput ? feedbackInput.disabled : 'NULL');
            console.log('ReadOnly:', feedbackInput ? feedbackInput.readOnly : 'NULL');
            console.log('Style display:', feedbackInput ? window.getComputedStyle(feedbackInput).display : 'NULL');
            console.log('Style visibility:', feedbackInput ? window.getComputedStyle(feedbackInput).visibility : 'NULL');
            console.log('=== END DEBUG INFO ===');

            if (feedbackInput) {
                alert(`Debug Info:\nValue: "${feedbackInput.value}"\nLength: ${feedbackInput.value.length}\nType: ${feedbackInput.tagName}`);
            } else {
                alert('Feedback input element not found!');
            }
        }

        // Check for existing session on page load
        function checkExistingSession() {
            const savedSessionId = localStorage.getItem('agentSessionId');
            const savedPhase = localStorage.getItem('agentPhase');

            if (savedSessionId) {
                console.log(`Found existing session: ${savedSessionId}, phase: ${savedPhase}`);
                sessionId = savedSessionId;
                currentPhase = savedPhase || 'greeting';
                updateConnectionStatus();

                // Show a reconnection message
                const chatContainer = document.getElementById('chatContainer');
                const reconnectMsg = document.createElement('div');
                reconnectMsg.className = 'message status-message';
                reconnectMsg.innerHTML = `🔄 Attempting to resume session ${savedSessionId}...`;
                chatContainer.appendChild(reconnectMsg);
            }
        }

        // Save session state to localStorage
        function saveSessionState() {
            if (sessionId) {
                localStorage.setItem('agentSessionId', sessionId);
                localStorage.setItem('agentPhase', currentPhase);
                localStorage.setItem('agentLastActivity', new Date().toISOString());
            }
        }

        // Debug: Check if all required elements exist
        function debugElementsOnLoad() {
            console.log('🔍 Debugging elements on page load:');

            const elements = {
                'feedbackContainer': document.getElementById('feedbackContainer'),
                'feedbackInput': document.getElementById('feedbackInput'),
                'submitFeedbackButton': document.getElementById('submitFeedbackButton'),
                'chatContainer': document.getElementById('chatContainer'),
                'messageInput': document.getElementById('messageInput'),
                'sendButton': document.getElementById('sendButton')
            };

            Object.entries(elements).forEach(([name, element]) => {
                if (element) {
                    console.log(`✅ ${name}: Found`);
                } else {
                    console.error(`❌ ${name}: Not found`);
                }
            });

            // Note: Not adding extra event listeners to prevent double submission
            // The onclick attribute in HTML should be sufficient
        }

        // Initialize session check and WebSocket connection
        checkExistingSession();
        connectWebSocket();

        // Run debug check after DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', debugElementsOnLoad);
        } else {
            debugElementsOnLoad();
        }
    </script>
</body>
</html>
        """

    def run(self):
        """Run the web server."""
        print(f"🚀 Starting Conversational Planning Agent V2...")
        print(f"📡 Server will be available at: http://{self.host}:{self.port}")
        print(f"🔗 WebSocket endpoint: ws://{self.host}:{self.port}/ws")

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


if __name__ == "__main__":
    agent = ConversationalPlanningAgent()
    agent.run()
