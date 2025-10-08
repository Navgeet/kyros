#!/usr/bin/env python3
"""
Web Server for Claude Code Agent - Provides a conversation frontend.

This web server:
1. Provides a web interface for users to interact with the Claude Code agent
2. Handles real-time communication via WebSockets
3. Displays plan reviews and execution results
4. Allows users to approve/reject plans before execution
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from claude_code_agent import ClaudeCodeAgent


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
            # Connection is already closed, remove it
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Remove broken connections
                self.disconnect(connection)


class ClaudeCodeWebServer:
    """Web server for Claude Code Agent interaction."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Claude Code Agent", version="1.0.0")
        self.agent = ClaudeCodeAgent()
        self.websocket_manager = WebSocketManager()
        self.pending_plans: Dict[str, Dict] = {}  # Store plans waiting for approval

        self._setup_middleware()
        self._setup_routes()

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

        @self.app.get("/screenshots/{filename}")
        async def get_screenshot(filename: str):
            screenshot_path = Path("screenshots") / filename
            if screenshot_path.exists():
                return FileResponse(str(screenshot_path))
            raise HTTPException(status_code=404, detail="Screenshot not found")

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_manager.connect(websocket)
            try:
                await self.websocket_manager.send_personal_message({
                    "type": "connection",
                    "message": "Connected to Claude Code Agent"
                }, websocket)

                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self._handle_websocket_message(message, websocket)

            except WebSocketDisconnect:
                self.websocket_manager.disconnect(websocket)
            except Exception as e:
                # Only try to send error if connection is still active
                if websocket in self.websocket_manager.active_connections:
                    try:
                        await self._safe_send({
                            "type": "error",
                            "message": f"Error: {str(e)}"
                        }, websocket)
                    except RuntimeError:
                        # Connection closed during error sending
                        self.websocket_manager.disconnect(websocket)

    async def _safe_send(self, message: dict, websocket: WebSocket):
        """Safely send a message to WebSocket, handling closed connections."""
        await self.websocket_manager.send_personal_message(message, websocket)

    async def _handle_websocket_message(self, message: Dict, websocket: WebSocket):
        """Handle incoming WebSocket messages."""
        message_type = message.get("type")

        if message_type == "user_request":
            await self._handle_user_request(message, websocket)
        elif message_type == "plan_approval":
            await self._handle_plan_approval(message, websocket)
        elif message_type == "get_history":
            await self._send_conversation_history(websocket)
        else:
            await self._safe_send({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }, websocket)

    async def _handle_user_request(self, message: Dict, websocket: WebSocket):
        """Handle user task requests."""
        user_request = message.get("content", "").strip()
        if not user_request:
            await self._safe_send({
                "type": "error",
                "message": "Empty request"
            }, websocket)
            return

        try:
            # Send acknowledgment
            await self._safe_send({
                "type": "status",
                "message": f"Processing request: {user_request}"
            }, websocket)

            # Take initial screenshot
            await self._safe_send({
                "type": "status",
                "message": "Taking screenshot..."
            }, websocket)

            initial_screenshot = self.agent.take_screenshot("before_request")

            # Generate plan
            await self._safe_send({
                "type": "status",
                "message": "Generating plan with Claude Code..."
            }, websocket)

            plan = self.agent.generate_plan_with_claude_code(user_request, initial_screenshot)

            # Create plan ID for approval workflow
            plan_id = str(uuid.uuid4())[:8]
            self.pending_plans[plan_id] = {
                "user_request": user_request,
                "plan": plan,
                "timestamp": datetime.now().isoformat()
            }

            # Send plan for review
            await self._safe_send({
                "type": "plan_review",
                "plan_id": plan_id,
                "user_request": user_request,
                "plan": {
                    "code": plan.get("code", ""),
                    "screenshot": initial_screenshot
                },
                "message": "Please review the generated plan. Approve to execute or reject to cancel."
            }, websocket)

        except Exception as e:
            await self._safe_send({
                "type": "error",
                "message": f"Error processing request: {str(e)}"
            }, websocket)

    async def _handle_plan_approval(self, message: Dict, websocket: WebSocket):
        """Handle plan approval/rejection."""
        plan_id = message.get("plan_id")
        approved = message.get("approved", False)

        if plan_id not in self.pending_plans:
            await self._safe_send({
                "type": "error",
                "message": "Plan not found or already processed"
            }, websocket)
            return

        plan_data = self.pending_plans.pop(plan_id)

        if not approved:
            await self._safe_send({
                "type": "plan_rejected",
                "message": "Plan rejected by user"
            }, websocket)
            return

        try:
            # Execute the approved plan
            await self._safe_send({
                "type": "status",
                "message": "Plan approved. Executing..."
            }, websocket)

            plan = plan_data["plan"]
            execution_result = self.agent.execute_generated_code(plan)

            # Take post-execution screenshot
            await self._safe_send({
                "type": "status",
                "message": "Taking post-execution screenshot..."
            }, websocket)

            import time
            time.sleep(1)
            post_screenshot = self.agent.take_screenshot("after_execution")

            # Get Claude Code review
            await self._safe_send({
                "type": "status",
                "message": "Getting execution review from Claude Code..."
            }, websocket)

            review = self.agent.review_execution_with_claude_code(
                plan, execution_result, post_screenshot
            )

            # Send execution results
            result = {
                "type": "execution_complete",
                "user_request": plan_data["user_request"],
                "execution": {
                    "success": execution_result[0],
                    "stdout": execution_result[1],
                    "stderr": execution_result[2]
                },
                "review": review,
                "screenshots": {
                    "before": plan.get("screenshot"),
                    "after": post_screenshot
                }
            }

            await self._safe_send(result, websocket)

            # Add to agent's conversation history
            self.agent.conversation_history.append({
                "user_request": plan_data["user_request"],
                "plan": plan,
                "execution_result": execution_result,
                "review": review,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            await self._safe_send({
                "type": "error",
                "message": f"Error executing plan: {str(e)}"
            }, websocket)

    async def _send_conversation_history(self, websocket: WebSocket):
        """Send conversation history to client."""
        await self._safe_send({
            "type": "conversation_history",
            "history": self.agent.conversation_history
        }, websocket)

    def _get_html_content(self) -> str:
        """Return the HTML content for the web interface."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Agent</title>
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
            height: 400px;
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
        .input-container {
            display: flex;
            gap: 10px;
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
        .approval-buttons {
            margin-top: 10px;
        }
        .approve-button, .reject-button {
            padding: 8px 16px;
            margin-right: 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .approve-button {
            background-color: #28a745;
            color: white;
        }
        .reject-button {
            background-color: #dc3545;
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
        }
        .screenshot {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
        }
        .connection-status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        .connected {
            background-color: #d4edda;
            color: #155724;
        }
        .disconnected {
            background-color: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="connection-status" id="connectionStatus">Connecting...</div>

    <div class="container">
        <div class="header">
            <h1>🤖 Claude Code Agent</h1>
            <p>Generate and execute computer use tasks with Claude Code</p>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="message agent-message">
                Welcome! I'm the Claude Code Agent. I can help you automate computer tasks by generating and executing Python code.
                <br><br>
                Just describe what you want to do (e.g., "search google for restaurants near me", "open a new browser tab", etc.)
            </div>
        </div>

        <div class="input-container">
            <input type="text" id="messageInput" class="input-field"
                   placeholder="Describe the task you want me to perform..."
                   onkeypress="handleKeyPress(event)">
            <button id="sendButton" class="send-button" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        let ws = null;
        let connected = false;
        let currentPlanId = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = function(event) {
                connected = true;
                updateConnectionStatus();
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
            if (connected) {
                statusEl.textContent = 'Connected';
                statusEl.className = 'connection-status connected';
            } else {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'connection-status disconnected';
            }
        }

        function handleMessage(message) {
            const chatContainer = document.getElementById('chatContainer');
            const messageEl = document.createElement('div');

            switch (message.type) {
                case 'connection':
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

                case 'plan_review':
                    currentPlanId = message.plan_id;
                    messageEl.className = 'message plan-review';
                    messageEl.innerHTML = `
                        <strong>Generated Plan for:</strong> ${message.user_request}
                        <div class="code-block">${message.plan.code}</div>
                        <div class="approval-buttons">
                            <button class="approve-button" onclick="approvePlan(true)">✅ Approve & Execute</button>
                            <button class="reject-button" onclick="approvePlan(false)">❌ Reject</button>
                        </div>
                    `;
                    break;

                case 'execution_complete':
                    messageEl.className = 'message agent-message';
                    const success = message.execution.success ? '✅' : '❌';
                    messageEl.innerHTML = `
                        <strong>Execution ${success} Complete:</strong> ${message.user_request}<br>
                        <strong>Success:</strong> ${message.execution.success}<br>
                        ${message.execution.stdout ? `<strong>Output:</strong> ${message.execution.stdout}<br>` : ''}
                        ${message.execution.stderr ? `<strong>Errors:</strong> ${message.execution.stderr}<br>` : ''}
                        <strong>Claude Code Review:</strong><br>
                        <div style="margin-top: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 4px;">
                            ${message.review}
                        </div>
                    `;
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
                type: 'user_request',
                content: message
            }));

            // Clear input and disable button temporarily
            input.value = '';
            sendButton.disabled = true;
            setTimeout(() => { sendButton.disabled = false; }, 1000);

            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function approvePlan(approved) {
            if (!currentPlanId) return;

            ws.send(JSON.stringify({
                type: 'plan_approval',
                plan_id: currentPlanId,
                approved: approved
            }));

            currentPlanId = null;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        // Initialize WebSocket connection
        connectWebSocket();
    </script>
</body>
</html>
        """

    def run(self):
        """Run the web server."""
        print(f"🚀 Starting Claude Code Agent Web Server...")
        print(f"📡 Server will be available at: http://{self.host}:{self.port}")
        print(f"🔗 WebSocket endpoint: ws://{self.host}:{self.port}/ws")

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


if __name__ == "__main__":
    server = ClaudeCodeWebServer()
    server.run()
