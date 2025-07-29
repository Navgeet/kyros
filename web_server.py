#!/usr/bin/env python3

import json
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import argparse
from agent import AIAgent
from logger import web_logger
from simple_sessions import SimpleSessionManager
import os
import uuid
from typing import Optional
from datetime import datetime

app = FastAPI(title="Triton AI Agent Web Interface")
templates = Jinja2Templates(directory="templates")

class TaskRequest(BaseModel):
    task: str
    max_retries: int = 3
    session_id: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    session_id: str
    status: str

class MessagesRequest(BaseModel):
    session_id: str
    since_message_id: Optional[str] = None

class MessagesResponse(BaseModel):
    messages: List[Dict[str, Any]]
    session_id: str

# Global session manager
session_manager = None

@app.on_event("startup")
def startup():
    global session_manager
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    session_manager = SimpleSessionManager(ollama_url)
    web_logger.info(f"Web server started with Ollama URL: {ollama_url}")

@app.get("/", response_class=HTMLResponse)
def get_index():
    """Serve the main web interface."""
    with open("templates/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/execute", response_model=TaskResponse)
def execute_task(request: TaskRequest):
    """Start task execution in background thread."""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    try:
        # Get or create session
        session = session_manager.get_or_create_session(request.session_id)
        session_id = session.session_id
        
        # Start task execution in background thread
        session.start_task_async(request.task, request.max_retries)
        
        return TaskResponse(
            task_id=str(uuid.uuid4()),
            session_id=session_id,
            status="started"
        )
        
    except Exception as e:
        web_logger.error(f"Web API: Error starting task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting task: {str(e)}")

@app.post("/api/messages", response_model=MessagesResponse)
def get_messages(request: MessagesRequest):
    """Get session status (simplified - no message history)."""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    try:
        status = session_manager.get_session_status(request.session_id)
        # Convert status to message format for compatibility
        messages = [{
            "id": "status",
            "type": "status",
            "content": f"Session status: {status.get('status', 'unknown')}",
            "timestamp": datetime.now().isoformat(),
            "metadata": status
        }]
        return MessagesResponse(
            messages=messages,
            session_id=request.session_id
        )
    except Exception as e:
        web_logger.error(f"Web API: Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting session status: {str(e)}")

@app.get("/api/status")
def get_status():
    """Get the current status of the session manager."""
    if not session_manager:
        return {"status": "not_initialized"}
    
    return {
        "status": "ready",
        "sessions": session_manager.get_stats()
    }

@app.post("/api/sessions")
def create_session():
    """Create a new session."""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    session_id = session_manager.create_session()
    web_logger.info(f"Web API: Created new session {session_id}")
    return {"session_id": session_id}

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session."""
    if not session_manager:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    
    success = session_manager.delete_session(session_id)
    if success:
        web_logger.info(f"Web API: Deleted session {session_id}")
        return {"status": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

def main():
    parser = argparse.ArgumentParser(description='Triton AI Agent Web Server')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to bind to (default: 8000)')
    parser.add_argument('--ollama-url', type=str, 
                       default='http://localhost:11434',
                       help='Ollama server URL')
    
    args = parser.parse_args()
    
    # Set environment variable for the agent
    os.environ["OLLAMA_URL"] = args.ollama_url
    
    web_logger.info(f"Starting Triton AI Agent Web Server on {args.host}:{args.port}")
    web_logger.info(f"Using Ollama URL: {args.ollama_url}")
    
    print(f"🚀 Starting Triton AI Agent Web Server...")
    print(f"🌐 Server: http://{args.host}:{args.port}")
    print(f"🧠 Ollama: {args.ollama_url}")
    print()
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
