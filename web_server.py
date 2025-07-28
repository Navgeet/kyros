#!/usr/bin/env python3

import asyncio
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
import os

app = FastAPI(title="Triton AI Agent Web Interface")
templates = Jinja2Templates(directory="templates")

class TaskRequest(BaseModel):
    task: str
    max_retries: int = 3

class TaskResponse(BaseModel):
    success: bool
    message: str
    plan: List[Dict[str, Any]] = None
    conversation_history: List[Dict[str, Any]] = None

# Global agent instance
agent = None

@app.on_event("startup")
async def startup():
    global agent
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    agent = AIAgent(ollama_url)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main web interface."""
    with open("templates/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """Execute a task using the AI agent."""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        success = agent.run_task(request.task, request.max_retries)
        
        # Get the last executed plan from conversation history
        plan = None
        if agent.conversation_history:
            for entry in reversed(agent.conversation_history):
                if "plan" in entry:
                    plan = entry["plan"]
                    break
        
        message = "Task completed successfully!" if success else "Task execution failed after all retry attempts"
        
        return TaskResponse(
            success=success,
            message=message,
            plan=plan,
            conversation_history=agent.conversation_history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing task: {str(e)}")

@app.get("/api/status")
async def get_status():
    """Get the current status of the agent."""
    return {
        "status": "ready" if agent else "not_initialized",
        "conversation_length": len(agent.conversation_history) if agent else 0
    }

@app.post("/api/reset")
async def reset_conversation():
    """Reset the conversation history."""
    if agent:
        agent.conversation_history = []
        return {"status": "reset"}
    else:
        raise HTTPException(status_code=500, detail="Agent not initialized")

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
    
    print(f"🚀 Starting Triton AI Agent Web Server...")
    print(f"🌐 Server: http://{args.host}:{args.port}")
    print(f"🧠 Ollama: {args.ollama_url}")
    print()
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
