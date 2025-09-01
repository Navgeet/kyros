#!/usr/bin/env python3
"""
Script to run task JSON files for testing the Kyros agent system.

Usage:
    python3 run_task_json.py <task_file.json>
    python3 run_task_json.py <task_file.json> --ollama-url http://localhost:11434

The JSON file should contain a task plan with the following structure:
{
  "tasks": [
    {
      "id": 0,
      "type": "task",
      "name": "task name",
      "verify_screen_change": false,
      "subtasks": [1, 2],
      "dependencies": []
    },
    {
      "id": 1,
      "type": "tool_call",
      "tool_name": "tool_name",
      "params": {"param": "value"}
    }
  ]
}
"""

import argparse
import json
import sys
import os
import time
from pathlib import Path
from executor import Executor
from logger import get_session_logger
import uuid

def load_task_json(file_path: str) -> dict:
    """Load and validate task JSON file."""
    try:
        with open(file_path, 'r') as f:
            task_data = json.load(f)
        
        # Validate required structure
        if 'tasks' not in task_data:
            raise ValueError("JSON file must contain 'tasks' key")
        
        if not isinstance(task_data['tasks'], list):
            raise ValueError("'tasks' must be a list")
        
        if not task_data['tasks']:
            raise ValueError("'tasks' list cannot be empty")
        
        print(f"✓ Loaded {len(task_data['tasks'])} tasks from {file_path}")
        return task_data
    
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{file_path}': {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def print_task_plan(plan: dict):
    """Print the task plan in a readable format."""
    tasks = plan.get('tasks', [])
    task_lookup = {task.get('id', i): task for i, task in enumerate(tasks)}
    
    # Find top-level tasks (not referenced as subtasks)
    subtask_ids = set()
    for task in tasks:
        for subtask_id in task.get('subtasks', []):
            subtask_ids.add(subtask_id)
    
    top_level_tasks = [task for task in tasks if task.get('id', 0) not in subtask_ids]
    
    def print_task(task, indent=0):
        prefix = "  " * indent
        task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
        task_type = task.get('type', 'task')
        
        # Show task type and tool info for tool calls
        type_info = f" [{task_type}]"
        if task_type == 'tool_call':
            tool_name = task.get('tool_name', 'unknown')
            params = task.get('params', {})
            type_info = f" [tool: {tool_name}({params})]"
        
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
        
        # Show verification
        verify_str = ""
        if task.get('verify_screen_change'):
            verify_str = " [verify screen]"
        
        print(f"{prefix}{task_name}{type_info}{verify_str}{deps_str}")
        
        # Print subtasks
        for subtask_id in task.get('subtasks', []):
            subtask = task_lookup.get(subtask_id)
            if subtask:
                print_task(subtask, indent + 1)
    
    print("📋 Task Plan:")
    for task in top_level_tasks:
        print_task(task)
    print()

def main():
    parser = argparse.ArgumentParser(description='Run task JSON files for testing')
    parser.add_argument('task_file', type=str, help='Path to JSON file containing task plan')
    parser.add_argument('--ollama-url', type=str, 
                       default='http://localhost:11434',
                       help='Ollama server URL')
    
    args = parser.parse_args()
    
    # Set OLLAMA_URL environment variable for tools
    os.environ["OLLAMA_URL"] = args.ollama_url
    
    # Suppress HTTP library logs to keep stdout clean
    import logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Load task JSON
    task_plan = load_task_json(args.task_file)
    
    # Create session logger
    session_id = str(uuid.uuid4())
    session_logger = get_session_logger(session_id)
    session_logger.info(f"Running task JSON file: {args.task_file}")
    
    # Print the plan
    print_task_plan(task_plan)
    
    # Create executor and run tasks
    print("⚙️  Executing tasks...")
    executor = Executor()
    
    try:
        success = executor.execute_plan(task_plan)
        
        if success:
            print("🎉 All tasks completed successfully!")
            session_logger.info("SUCCESS: All tasks completed successfully")
            sys.exit(0)
        else:
            print("❌ Task execution failed!")
            session_logger.error("FAILURE: Task execution failed")
            
            # Print failed tasks for debugging
            print("\n📊 Task Status Summary:")
            for task in task_plan.get('tasks', []):
                status = task.get('status', 'unknown')
                task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
                
                if status == 'success':
                    print(f"  ✓ {task_name}")
                elif status == 'error':
                    print(f"  ✗ {task_name}")
                    if task.get('stderr'):
                        print(f"    Error: {task.get('stderr')}")
                elif status == 'blocked':
                    print(f"  🚫 {task_name} (blocked)")
                    if task.get('stderr'):
                        print(f"    Reason: {task.get('stderr')}")
                elif status == 'replan':
                    print(f"  🔄 {task_name} (needs replanning)")
                else:
                    print(f"  ❓ {task_name} (status: {status})")
            
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Task execution interrupted by user")
        session_logger.info("Task execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        session_logger.error(f"Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    time.sleep(5)
    main()
