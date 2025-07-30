#!/usr/bin/env python3

import argparse
import asyncio
from planner import Planner, Plan
from executor import Executor
from utils import input
from logger import agent_logger, get_session_logger
import uuid

class AIAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434", session_id: str = None):
        self.planner = Planner(ollama_url)
        self.executor = Executor()
        self.conversation_history = []
        self.session_id = session_id or str(uuid.uuid4())
        self.session_logger = get_session_logger(self.session_id)
        
        agent_logger.info(f"AIAgent initialized with session_id: {self.session_id}")
        self.session_logger.info(f"New session started with Ollama URL: {ollama_url}")
    
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
            tasks = self.planner.generate_plan(user_input, conversation_history=self.conversation_history, regenerate_screen_context=not is_replanning)
            
            if not tasks:
                agent_logger.warning("Failed to generate plan")
                self.session_logger.warning("PLANNING: Failed to generate plan")
                print("❌ Failed to generate plan!")
                continue
            
            # Log the generated plan
            plan_summary = [task.name for task in tasks]
            agent_logger.info(f"Generated plan with {len(tasks)} tasks: {plan_summary}")
            self.session_logger.info(f"PLAN GENERATED: {len(tasks)} tasks - {plan_summary}")
            
            print("📋 Generated plan:")
            self._print_tasks(tasks)
            print()
            
            # Execute phase
            agent_logger.info("Starting execution phase")
            self.session_logger.info("EXECUTION: Starting plan execution")
            print("⚙️  Executing...")
            success = self.executor.execute_plan(tasks)
            
            if success:
                agent_logger.info("Task completed successfully")
                self.session_logger.info("SUCCESS: Task completed successfully")
                print("🎉 Task completed successfully!")
                # Add successful plan to conversation history (filter out Plan tasks)
                filtered_tasks = self._filter_plan_tasks(tasks)
                self.conversation_history.append({"from": "system", "plan": [task.to_dict() for task in filtered_tasks]})
                return True
            else:
                # Check if any task has replan status (Plan task encountered)
                # replan_task = self._find_replan_task(tasks)
                # if replan_task:
                #     agent_logger.info(f"Plan task detected, replanning with original user input")
                #     self.session_logger.info(f"REPLAN: Using original user input for Plan task")
                #     print(f"🔄 Plan task detected, replanning with original user input")
                #     # Continue with original user_input for next iteration
                # else:
                #     agent_logger.warning(f"Task execution failed (attempt {attempt + 1}/{max_retries})")
                #     self.session_logger.warning(f"EXECUTION FAILED: Attempt {attempt + 1}/{max_retries}")
                #     print(f"❌ Task execution failed (attempt {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    # if not replan_task:
                    print("🔄 Going back to planning...")
                    # Filter out Plan tasks from conversation history
                    filtered_tasks = self._filter_plan_tasks(tasks)
                    self.conversation_history.append({"from": "system", "plan": [task.to_dict() for task in filtered_tasks]})
                    # previous_tasks = tasks  # Pass failed tasks as context
                    print()
        
        agent_logger.error("Task failed after all retry attempts")
        self.session_logger.error("FINAL FAILURE: Task failed after all retry attempts")
        print("❌ Task failed after all retry attempts!")
        # Add failed plan to conversation history
        # if previous_tasks:
        #     self.conversation_history.append({"from": "system", "plan": [task.to_dict() for task in previous_tasks]})
        return False
    
    def _find_replan_task(self, tasks):
        """Find a task with replan status (Plan task that needs replanning)."""
        def search_tasks(task_list):
            for task in task_list:
                if hasattr(task, 'status') and task.status == "replan" and isinstance(task, Plan):
                    return task
                if task.subtasks:
                    result = search_tasks(task.subtasks)
                    if result:
                        return result
            return None
        
        return search_tasks(tasks)
    
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
    
    def _print_tasks(self, tasks, indent=0):
        """Print tasks with their subtasks in a hierarchical format."""
        for task in tasks:
            prefix = "  " * indent
            deps_str = ""
            if task.dependencies:
                dep_names = [dep.name for dep in task.dependencies]
                deps_str = f" (depends on: {', '.join(dep_names)})"
            
            print(f"{prefix}{task.name}{deps_str}")
            
            if task.subtasks:
                self._print_tasks(task.subtasks, indent + 1)
    
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
    
    args = parser.parse_args()
    
    # Set OLLAMA_URL environment variable for tools
    import os
    os.environ["OLLAMA_URL"] = args.ollama_url
    
    agent = AIAgent(args.ollama_url)
    
    if args.task:
        # Single task mode
        agent.run_task(args.task)
    else:
        # Interactive mode
        asyncio.run(agent.run_interactive())

if __name__ == "__main__":
    main()
