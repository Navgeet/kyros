from typing import Dict, List, Any
import time
from tools import Tools
from planner import Task, ToolCall

class Executor:
    def __init__(self):
        self.tools = Tools()
        self.completed_tasks = set()
    
    def execute_plan(self, tasks: List[Task]) -> bool:
        """Execute tasks in the correct order based on dependencies."""
        return self._execute_tasks(tasks)
    
    def _execute_tasks(self, tasks: List[Task]) -> bool:
        """Execute a list of tasks, handling dependencies."""
        tasks_to_execute = tasks.copy()
        
        while tasks_to_execute:
            # Find tasks that can be executed (all dependencies completed)
            executable_tasks = []
            
            for task in tasks_to_execute:
                # Check if all dependencies are completed
                if all(dep.name in self.completed_tasks for dep in task.dependencies):
                    executable_tasks.append(task)
            
            if not executable_tasks:
                print("No executable tasks found - possible circular dependency")
                return False
            
            # Execute the first available task
            task = executable_tasks[0]
            success = self._execute_task(task)
            
            if success:
                self.completed_tasks.add(task.name)
                tasks_to_execute.remove(task)
                print(f"✓ Completed task: {task.name}")
                
                # Add delay between tasks
                if tasks_to_execute:  # Only delay if there are more tasks
                    time.sleep(0.5)
            else:
                print(f"✗ Failed task: {task.name}")
                return False
        
        print("All tasks completed successfully!")
        return True
    
    def _execute_task(self, task: Task) -> bool:
        """Execute a single task and its subtasks."""
        print(f"Executing task: {task.name}")
        
        # If this is a ToolCall, execute it directly
        if isinstance(task, ToolCall):
            return self._execute_tool_call(task)
        
        # Handle screen verification tasks
        if hasattr(task, 'verify_screen_change') and task.verify_screen_change:
            return self._execute_verified_task(task)
        
        # For regular tasks, execute all subtasks
        if task.subtasks:
            return self._execute_tasks(task.subtasks)
        
        # If no subtasks, consider it completed
        print(f"Task {task.name} has no subtasks - marking as completed")
        return True
    
    def _execute_tool_call(self, tool_call: ToolCall) -> bool:
        """Execute a tool call."""
        print(f"Executing tool: {tool_call.tool_name} with params {tool_call.params}")
        
        if hasattr(self.tools, tool_call.tool_name):
            method = getattr(self.tools, tool_call.tool_name)
            return method(**tool_call.params)
        else:
            print(f"Unknown tool: {tool_call.tool_name}")
            return False
    
    def _execute_verified_task(self, task: Task) -> bool:
        """Execute a task with screen change verification."""
        print(f"Executing verified task: {task.name}")
        
        # Generate unique screenshot names
        task_id = task.name.replace(' ', '_').replace(':', '').replace('(', '').replace(')', '')
        before_name = f"before_{task_id}"
        after_name = f"after_{task_id}"
        
        # Take before screenshot
        print("Taking before screenshot...")
        if not self.tools.screenshot(before_name):
            print("Failed to take before screenshot")
            return False
        
        # Execute the task's subtasks
        if task.subtasks:
            success = self._execute_tasks(task.subtasks)
            if not success:
                print("Task execution failed")
                return False
        else:
            print("No subtasks to execute")

        time.sleep(1)
        
        # Take after screenshot
        print("Taking after screenshot...")
        if not self.tools.screenshot(after_name):
            print("Failed to take after screenshot")
            return False
        
        # Compare screenshots
        print("Comparing screenshots...")
        verification_success = self.tools.compare_screenshots(before_name, after_name)
        
        if verification_success:
            print(f"✓ Screen verification passed for task: {task.name}")
            return True
        else:
            print(f"✗ Screen verification failed for task: {task.name}")
            return False