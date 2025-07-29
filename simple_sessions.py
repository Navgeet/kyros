#!/usr/bin/env python3

import uuid
import asyncio
import threading
from typing import Dict, Optional
from agent import AIAgent

class SimpleSession:
    def __init__(self, session_id: str, ollama_url: str):
        self.session_id = session_id
        self.agent = AIAgent(ollama_url, session_id=session_id)
        self.current_task = None
        self.status = "idle"  # "idle", "running", "completed", "failed"
        self.result = None
        self._lock = threading.Lock()

    def execute_task_sync(self, task: str, max_retries: int = 3) -> bool:
        """Execute a task synchronously and return success status"""
        with self._lock:
            self.current_task = task
            self.status = "running"
        
        try:
            success = self.agent.run_task(task, max_retries)
            with self._lock:
                self.status = "completed" if success else "failed"
                self.result = {"success": success, "task": task}
            return success
        except Exception as e:
            with self._lock:
                self.status = "failed"
                self.result = {"success": False, "task": task, "error": str(e)}
            return False

    def start_task_async(self, task: str, max_retries: int = 3):
        """Start task execution in a background thread"""
        def run_task():
            self.execute_task_sync(task, max_retries)
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return thread

class SimpleSessionManager:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.sessions: Dict[str, SimpleSession] = {}
        self.ollama_url = ollama_url

    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = SimpleSession(session_id, self.ollama_url)
        return session_id

    def get_session(self, session_id: str) -> Optional[SimpleSession]:
        return self.sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str] = None) -> SimpleSession:
        if session_id is None or session_id not in self.sessions:
            session_id = self.create_session(session_id)
        return self.sessions[session_id]

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_status(self, session_id: str) -> Dict:
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        return {
            "session_id": session_id,
            "status": session.status,
            "current_task": session.current_task,
            "result": session.result
        }

    def get_stats(self) -> Dict:
        return {
            "total_sessions": len(self.sessions),
            "sessions": {
                sid: {
                    "status": session.status,
                    "current_task": session.current_task
                }
                for sid, session in self.sessions.items()
            }
        }