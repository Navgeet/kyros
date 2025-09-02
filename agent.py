#!/usr/bin/env python3

import argparse
import asyncio
from planner import Planner, Plan
from executor import Executor
from utils import input
from logger import agent_logger, get_session_logger
import uuid

class AIAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434", vllm_url: str = None, session_id: str = None):
        self.planner = Planner(ollama_url, vllm_url)
        self.executor = Executor()
        self.conversation_history = []
        self.session_id = session_id or str(uuid.uuid4())
        self.session_logger = get_session_logger(self.session_id)
        
        # Store current plan and task status for external access
        self.current_plan = None
        self.task_status = {}  # {task_id: {status, stdout, stderr}}
        
        # Callback for streaming output (thinking and regular output)
        self.streaming_callback = None
        
        agent_logger.info(f"AIAgent initialized with session_id: {self.session_id}")
        self.session_logger.info(f"New session started with Ollama URL: {ollama_url}")
    
    def set_streaming_callback(self, callback):
        """Set callback function to receive streaming output during planning"""
        self.streaming_callback = callback
        self.planner.set_streaming_callback(callback)
    
    def run_task(self, user_input: str, max_retries: int = 3) -> bool:
        """Run a single task with the given user input."""
        agent_logger.info(f"Starting task: {user_input}")
        self.session_logger.info(f"USER INPUT: {user_input}")
        
        print(f"📝 Task: {user_input}")
        print()
        
        # Add user message to conversation history
        self.conversation_history.append({"from": "user", "message": user_input})

        # previous_tasks = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                agent_logger.info(f"Retrying task (attempt {attempt + 1}/{max_retries})")
                self.session_logger.info(f"RETRY: Attempt {attempt + 1}/{max_retries}")
                print(f"🔄 Retrying task (attempt {attempt + 1}/{max_retries})...")
                print()
            
            # Plan phase
            agent_logger.info("Starting planning phase")
            self.session_logger.info("PLANNING: Starting plan generation")
            print("🧠 Planning...")
            # Don't regenerate screen context when replanning (attempt > 0)
            is_replanning = attempt > 0
            plan = self.planner.generate_plan(user_input, conversation_history=self.conversation_history, regenerate_screen_context=not is_replanning)
            
            if not plan or not plan.get('tasks'):
                agent_logger.warning("Failed to generate plan")
                self.session_logger.warning("PLANNING: Failed to generate plan")
                print("❌ Failed to generate plan!")
                continue
            
            # Store the plan for external access
            self.current_plan = plan
            # Initialize task status for all tasks
            self.task_status = {}
            for task in plan.get('tasks', []):
                task_id = str(task.get('id', ''))
                self.task_status[task_id] = {
                    'status': 'pending',
                    'stdout': [],
                    'stderr': []
                }
            
            # Log the generated plan
            task_names = [task.get('name', f"Task {task.get('id', 'unknown')}") for task in plan.get('tasks', [])]
            agent_logger.info(f"Generated plan with {len(plan.get('tasks', []))} tasks: {task_names}")
            self.session_logger.info(f"PLAN GENERATED: {len(plan.get('tasks', []))} tasks - {task_names}")
            
            print("📋 Generated plan:")
            self._print_json_plan(plan)
            print()
            
            # Execute phase
            agent_logger.info("Starting execution phase")
            self.session_logger.info("EXECUTION: Starting plan execution")
            print("⚙️  Executing...")
            success = self.executor.execute_plan(plan)
            
            if success:
                agent_logger.info("Task completed successfully")
                self.session_logger.info("SUCCESS: Task completed successfully")
                print("🎉 Task completed successfully!")
                # Add successful plan to conversation history
                self.conversation_history.append({"from": "system", "plan": plan})
                return True
            else:
                # Check if any task has replan status (Plan task encountered)
                replan_task = self._find_replan_task(plan)
                if replan_task:
                    agent_logger.info(f"Plan task detected, replanning with original user input")
                    self.session_logger.info(f"REPLAN: Using original user input for Plan task")
                    print(f"🔄 Plan task detected, replanning...")
                    # Continue with original user_input for next iteration
                else:
                    agent_logger.warning(f"Task execution failed (attempt {attempt + 1}/{max_retries})")
                    self.session_logger.warning(f"EXECUTION FAILED: Attempt {attempt + 1}/{max_retries}")
                    print(f"❌ Task execution failed (attempt {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    if replan_task:
                        print("🔄 Going back to planning for replanning...")
                    else:
                        print("🔄 Going back to planning...")
                    # Add plan with status info to conversation history
                    self.conversation_history.append({"from": "system", "plan": plan})
                    print()
        
        agent_logger.error("Task failed after all retry attempts")
        self.session_logger.error("FINAL FAILURE: Task failed after all retry attempts")
        print("❌ Task failed after all retry attempts!")
        # Add failed plan to conversation history
        # if previous_tasks:
        #     self.conversation_history.append({"from": "system", "plan": [task.to_dict() for task in previous_tasks]})
        return False
    
    def _find_replan_task(self, plan):
        """Find a task with replan status (Plan task that needs replanning)."""
        def search_tasks(task_list, task_lookup):
            for task in task_list:
                if task.get('status') == "replan":
                    return task
                
                # Recursively search subtasks
                subtask_ids = task.get('subtasks', [])
                if subtask_ids:
                    subtasks = [task_lookup.get(sid) for sid in subtask_ids if sid in task_lookup]
                    result = search_tasks(subtasks, task_lookup)
                    if result:
                        return result
            return None
        
        tasks = plan.get('tasks', [])
        # Create lookup table for task references
        task_lookup = {task.get('id', i): task for i, task in enumerate(tasks)}
        
        # Find top-level tasks (not referenced as subtasks)
        subtask_ids = set()
        for task in tasks:
            for subtask_id in task.get('subtasks', []):
                subtask_ids.add(subtask_id)
        
        top_level_tasks = [task for task in tasks if task.get('id', 0) not in subtask_ids]
        
        return search_tasks(top_level_tasks, task_lookup)
    
    def _filter_plan_tasks(self, tasks):
        """Remove Plan tasks from task hierarchy before adding to conversation history."""
        filtered_tasks = []
        
        for task in tasks:
            # Skip Plan tasks
            if isinstance(task, Plan):
                continue
            
            # Create a copy of the task and filter its subtasks recursively
            filtered_task = task.__class__.__dict__.copy() if hasattr(task, '__class__') else task
            filtered_task = type(task).__new__(type(task))
            filtered_task.__dict__.update(task.__dict__)
            
            if task.subtasks:
                filtered_task.subtasks = self._filter_plan_tasks(task.subtasks)
            
            filtered_tasks.append(filtered_task)
        
        return filtered_tasks
    
    def _print_json_plan(self, plan):
        """Print JSON plans with their subtasks in a hierarchical format."""
        # Create a lookup table for task references
        task_lookup = {task.get('id', i): task for i, task in enumerate(plan.get('tasks', []))}
        
        # Find top-level tasks (not referenced as subtasks)
        subtask_ids = set()
        for task in plan.get('tasks', []):
            for subtask_id in task.get('subtasks', []):
                subtask_ids.add(subtask_id)
        
        top_level_tasks = [task for task in plan.get('tasks', []) if task.get('id', 0) not in subtask_ids]
        
        def print_task(task, indent=0):
            prefix = "  " * indent
            task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
            
            # Show dependencies
            deps_str = ""
            if task.get('dependencies'):
                dep_names = []
                for dep_id in task.get('dependencies', []):
                    dep_task = task_lookup.get(dep_id)
                    if dep_task:
                        dep_names.append(dep_task.get('name', f"Task {dep_id}"))
                if dep_names:
                    deps_str = f" (depends on: {', '.join(dep_names)})"
            
            print(f"{prefix}{task_name}{deps_str}")
            
            # Print subtasks
            for subtask_id in task.get('subtasks', []):
                subtask = task_lookup.get(subtask_id)
                if subtask:
                    print_task(subtask, indent + 1)
        
        for task in top_level_tasks:
            print_task(task)
    
    async def run_interactive(self):
        """Run the agent in interactive mode - continuous loop."""
        agent_logger.info("Starting interactive mode")
        self.session_logger.info("INTERACTIVE MODE: Session started")
        
        print("🤖 AI Agent starting in interactive mode...")
        print("Type 'quit', 'exit', or 'q' to stop.")
        print()
        
        while True:
            try:
                user_input = await input()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    agent_logger.info("Interactive mode ended by user")
                    self.session_logger.info("INTERACTIVE MODE: Session ended by user")
                    print("👋 Goodbye!")
                    break
                
                print()
                self.run_task(user_input)
                print("-" * 50)
                print()
                
            except KeyboardInterrupt:
                agent_logger.info("Interactive mode interrupted by user")
                self.session_logger.info("INTERACTIVE MODE: Session interrupted")
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                agent_logger.error(f"Error in interactive mode: {e}")
                self.session_logger.error(f"INTERACTIVE ERROR: {e}")
                print(f"❌ Error: {e}")
                print()

def main():
    parser = argparse.ArgumentParser(description='AI Agent with planning and execution')
    parser.add_argument('--task', type=str, 
                       help='Single task to execute (if not provided, runs in interactive mode)')
    parser.add_argument('--ollama-url', type=str, 
                       default='http://localhost:11434',
                       help='Ollama server URL')
    parser.add_argument('--vllm-url', type=str,
                       help='vLLM server URL for planning (defaults to ollama-url)')
    
    args = parser.parse_args()
    
    # Set OLLAMA_URL environment variable for tools
    import os
    os.environ["OLLAMA_URL"] = args.ollama_url
    
    # Suppress HTTP library logs to keep stdout clean
    import logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    agent = AIAgent(args.ollama_url, args.vllm_url)
    
    if args.task:
        # Single task mode
        agent.run_task(args.task)
    else:
        # Interactive mode
        asyncio.run(agent.run_interactive())

if __name__ == "__main__":
    main()
