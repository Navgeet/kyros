#!/usr/bin/env python3

import uuid
import asyncio
import threading
from typing import Dict, Optional
from agent import AIAgent

class SimpleSession:
    def __init__(self, session_id: str, ollama_url: str, vllm_url: str = None):
        self.session_id = session_id
        self.agent = AIAgent(ollama_url, vllm_url, session_id=session_id)
        self.current_task = None
        self.status = "idle"  # "idle", "running", "completed", "failed"
        self.result = None
        self.current_plan = None
        self.task_progress = {}  # {task_id: {status, stdout, stderr, thinking_content}}
        self.current_thinking_task_id = None  # Track which task is currently thinking
        self.agent_messages = []  # Store agent messages for frontend display
        self._lock = threading.Lock()
        
        # Set up streaming callback for planning output
        self.agent.set_streaming_callback(self._on_planning_stream)
    
    def _on_planning_stream(self, stream_type: str, content: str):
        """Callback to handle streaming planning output"""

        with self._lock:
            # During planning, we're working on the top-level task (ID: "0")
            task_id = "0"
            
            if task_id in self.task_progress:
                if stream_type == "thinking":
                    # Append thinking content to the task
                    if "thinking_content" not in self.task_progress[task_id]:
                        self.task_progress[task_id]["thinking_content"] = ""
                    
                    # Handle special thinking markers
                    if content == "💭 Thinking:":
                        self.task_progress[task_id]["thinking_content"] = "💭 Thinking:\n"
                    else:
                        self.task_progress[task_id]["thinking_content"] += content
                        
                elif stream_type == "plan":
                    # Plan content goes to stdout
                    if "\n📋 Plan:" in content:
                        self.task_progress[task_id]["stdout"].append("📋 Plan generation started...")
                    # We could also append plan content to stdout if desired
                elif stream_type == "agent_message":
                    # Store agent messages for frontend display
                    self.agent_messages.append({
                        "message": content,
                        "timestamp": threading.current_thread().ident  # Simple timestamp
                    })
            else:
                print(f"DEBUG: Task {task_id} not found in task_progress", flush=True)
    
    def get_current_status(self):
        """Get real-time status including plan data from agent"""
        with self._lock:
            # Update plan and progress from agent in real-time
            if hasattr(self.agent, 'current_plan') and self.agent.current_plan:
                self.current_plan = self.agent.current_plan
            
            if hasattr(self.agent, 'task_status') and self.agent.task_status:
                self.task_progress = self.agent.task_status
            
            return {
                "status": self.status,
                "current_task": self.current_task,
                "current_plan": self.current_plan,
                "task_progress": self.task_progress,
                "result": self.result,
                "agent_messages": self.agent_messages
            }

    def execute_task_sync(self, task: str, max_retries: int = 3) -> bool:
        """Execute a task synchronously and return success status"""        
        try:
            # Update initial task status to show planning phase
            with self._lock:
                if "0" in self.task_progress:
                    self.task_progress["0"]["stdout"] = ["Planning phase started..."]
            
            # Hook into agent's plan generation and execution
            success = self.agent.run_task(task, max_retries)
            
            # Extract plan data from agent and merge with initial task
            if hasattr(self.agent, 'current_plan') and self.agent.current_plan:
                generated_plan = self.agent.current_plan
                
                # Create combined plan with user task as top level
                combined_tasks = [{
                    "id": "0",
                    "name": task,
                    "type": "user_task", 
                    "dependencies": [],
                    "subtasks": [str(t.get('id', '')) for t in generated_plan.get('tasks', [])]
                }]
                
                # Add generated subtasks with updated IDs
                for gen_task in generated_plan.get('tasks', []):
                    gen_task_copy = gen_task.copy()
                    combined_tasks.append(gen_task_copy)
                
                self.current_plan = {"tasks": combined_tasks}
                
                # Update task progress with generated tasks
                if hasattr(self.agent, 'task_status') and self.agent.task_status:
                    # Keep the initial task status and add generated ones
                    for task_id, status in self.agent.task_status.items():
                        self.task_progress[str(task_id)] = status
                
                # Update top-level task status based on execution result
                with self._lock:
                    if "0" in self.task_progress:
                        if success:
                            self.task_progress["0"]["status"] = "completed"
                            self.task_progress["0"]["stdout"].append("Task completed successfully!")
                        else:
                            self.task_progress["0"]["status"] = "failed"  
                            self.task_progress["0"]["stderr"] = ["Task execution failed"]
            
            with self._lock:
                self.status = "completed" if success else "failed"
                self.result = {"success": success, "task": task}
            return success
        except Exception as e:
            with self._lock:
                self.status = "failed"
                self.result = {"success": False, "task": task, "error": str(e)}
                # Update top-level task to show failure
                if "0" in self.task_progress:
                    self.task_progress["0"]["status"] = "failed"
                    self.task_progress["0"]["stderr"] = [str(e)]
            return False

    def create_initial_task_structure(self, task: str):
        """Create initial task structure immediately upon submission"""
        with self._lock:
            self.current_task = task
            self.status = "running"
            
            # Clear previous agent messages for new task
            self.agent_messages = []
            
            # Create initial top-level task structure
            self.current_plan = {
                "tasks": [{
                    "id": "0",
                    "name": task,
                    "type": "user_task",
                    "dependencies": []
                }]
            }
            
            # Set initial task status
            self.task_progress = {
                "0": {
                    "status": "running",
                    "stdout": ["Task submitted, planning in progress..."],
                    "stderr": []
                }
            }

    def start_task_async(self, task: str, max_retries: int = 3):
        """Start task execution in a background thread"""
        # Create initial task structure immediately
        self.create_initial_task_structure(task)
        
        def run_task():
            self.execute_task_sync(task, max_retries)
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return thread

class SimpleSessionManager:
    def __init__(self, ollama_url: str = "http://localhost:11434", vllm_url: str = None):
        self.sessions: Dict[str, SimpleSession] = {}
        self.ollama_url = ollama_url
        self.vllm_url = vllm_url

    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = SimpleSession(session_id, self.ollama_url, self.vllm_url)
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
        
        # Get real-time status from session
        status_data = session.get_current_status()
        
        # Get current plan and task progress for frontend
        current_plan = status_data.get('current_plan')
        task_progress = status_data.get('task_progress', {})
        
        # Merge task progress data into plan tasks
        if current_plan and 'tasks' in current_plan:
            for task in current_plan['tasks']:
                task_id = str(task.get('id', ''))
                progress = task_progress.get(task_id, {})
                
                # Merge progress data into the task (stdout, stderr, thinking)
                if progress:
                    # Only override status from progress if it's more recent/accurate
                    # The task in current_plan should already have the correct status from executor
                    task['stdout'] = progress.get('stdout', [])
                    task['stderr'] = progress.get('stderr', [])
                    task['thinking_content'] = progress.get('thinking_content', '')
        
        return {
            "session_id": session_id,
            "status": status_data.get('status'),
            "current_task": status_data.get('current_task'),
            "result": status_data.get('result'),
            "plan": current_plan,
            "agent_messages": status_data.get('agent_messages', [])
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
