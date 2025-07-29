#!/usr/bin/env python3

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from agent import AIAgent

class MessageType(Enum):
    USER = "user"
    SYSTEM = "system"
    STATUS = "status"
    PLAN = "plan"
    ERROR = "error"
    EXECUTION = "execution"

@dataclass
class Message:
    id: str
    type: MessageType
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

@dataclass
class TaskExecution:
    task_id: str
    task: str
    status: str  # "pending", "running", "completed", "failed"
    messages: List[Message]
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class Session:
    def __init__(self, session_id: str, ollama_url: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.messages: List[Message] = []
        self.current_execution: Optional[TaskExecution] = None
        self.agent = AIAgent(ollama_url, session_id=session_id)
        self._lock = threading.Lock()
        
        # Add welcome message
        self.add_message(MessageType.SYSTEM, "Welcome to Triton AI Agent! Enter a task to get started.")
    
    def add_message(self, msg_type: MessageType, content: str, metadata: Optional[Dict[str, Any]] = None):
        with self._lock:
            message = Message(
                id=str(uuid.uuid4()),
                type=msg_type,
                content=content,
                timestamp=datetime.now(),
                metadata=metadata
            )
            self.messages.append(message)
            self.last_activity = datetime.now()
            return message
    
    def get_messages_since(self, message_id: Optional[str] = None) -> List[Message]:
        with self._lock:
            if message_id is None:
                return self.messages.copy()
            
            # Find the index of the message with the given ID
            try:
                for i, msg in enumerate(self.messages):
                    if msg.id == message_id:
                        return self.messages[i+1:].copy()
                return self.messages.copy()
            except:
                return self.messages.copy()
    
    def start_task_execution(self, task: str, max_retries: int = 3) -> str:
        with self._lock:
            task_id = str(uuid.uuid4())
            self.current_execution = TaskExecution(
                task_id=task_id,
                task=task,
                status="pending",
                messages=[],
                started_at=datetime.now()
            )
            
            # Add user message
            self.add_message(MessageType.USER, task)
            self.add_message(MessageType.STATUS, "Task received, starting execution...", 
                           {"task_id": task_id, "status": "pending"})
            
            return task_id
    
    def update_execution_status(self, status: str, message: str = None, metadata: Dict[str, Any] = None):
        with self._lock:
            if self.current_execution:
                self.current_execution.status = status
                if status in ["completed", "failed"]:
                    self.current_execution.completed_at = datetime.now()
                
                if message:
                    msg_type = MessageType.ERROR if status == "failed" else MessageType.STATUS
                    self.add_message(msg_type, message, metadata)

class SessionManager:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.sessions: Dict[str, Session] = {}
        self.ollama_url = ollama_url
        self._lock = threading.Lock()
        
        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = Session(session_id, self.ollama_url)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        if session_id is None:
            session_id = self.create_session()
        elif session_id not in self.sessions:
            self.create_session(session_id)
        
        return self.sessions[session_id]
    
    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def get_messages(self, session_id: str, since_message_id: Optional[str] = None) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            return []
        
        messages = session.get_messages_since(since_message_id)
        return [msg.to_dict() for msg in messages]
    
    def execute_task_sync(self, session_id: str, task: str, max_retries: int = 3):
        """Execute a task synchronously"""
        session = self.get_session(session_id)
        if not session:
            print(f"DEBUG: Session not found: {session_id}")
            return
        
        task_id = session.start_task_execution(task, max_retries)
        print(f"DEBUG: Started task execution with task_id: {task_id}")
        
        try:
            print(f"DEBUG: run_task started for task: {task}")
            session.update_execution_status("running", "Planning and executing task...")
            
            # Add debug logging
            print(f"DEBUG: Starting task execution for: {task}")
            session.add_message(MessageType.STATUS, f"Starting task: {task}")
            
            print(f"DEBUG: About to call session.agent.run_task")
            success = session.agent.run_task(task, max_retries)
            print(f"DEBUG: session.agent.run_task returned: {success}")
            
            # Get the plan from conversation history
            plan = None
            if session.agent.conversation_history:
                for entry in reversed(session.agent.conversation_history):
                    if "plan" in entry:
                        plan = entry["plan"]
                        break
            
            if success:
                print(f"DEBUG: Task completed successfully")
                session.update_execution_status("completed", 
                    "Task completed successfully!", 
                    {"plan": plan, "task_id": task_id})
            else:
                print(f"DEBUG: Task failed")
                session.update_execution_status("failed", 
                    "Task execution failed after all retry attempts", 
                    {"task_id": task_id})
                
        except Exception as e:
            print(f"DEBUG: Exception in task execution: {str(e)}")
            import traceback
            traceback.print_exc()
            session.update_execution_status("failed", f"Error executing task: {str(e)}", 
                                          {"error": str(e), "task_id": task_id})

    async def execute_task_async(self, session_id: str, task: str, max_retries: int = 3):
        """Execute a task asynchronously in the background"""
        print(f"DEBUG: execute_task_async called for session {session_id}, task: {task}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.execute_task_sync, session_id, task, max_retries)
    
    def _start_cleanup_task(self):
        """Start background cleanup task for old sessions"""
        def cleanup():
            while True:
                try:
                    current_time = datetime.now()
                    sessions_to_remove = []
                    
                    with self._lock:
                        for session_id, session in self.sessions.items():
                            # Remove sessions inactive for more than 1 hour
                            if current_time - session.last_activity > timedelta(hours=1):
                                sessions_to_remove.append(session_id)
                    
                    for session_id in sessions_to_remove:
                        self.delete_session(session_id)
                    
                    # Sleep for 10 minutes before next cleanup
                    import time
                    time.sleep(600)
                    
                except Exception as e:
                    print(f"Error in session cleanup: {e}")
                    import time
                    time.sleep(60)  # Wait 1 minute before retrying
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def get_session_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": sum(1 for s in self.sessions.values() 
                                     if datetime.now() - s.last_activity < timedelta(minutes=30)),
                "sessions": {
                    sid: {
                        "created_at": session.created_at.isoformat(),
                        "last_activity": session.last_activity.isoformat(),
                        "message_count": len(session.messages),
                        "current_task": session.current_execution.task if session.current_execution else None,
                        "task_status": session.current_execution.status if session.current_execution else None
                    }
                    for sid, session in self.sessions.items()
                }
            }