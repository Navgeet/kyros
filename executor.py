from typing import Dict, List, Any
import time
import uuid
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
                if all(dep.status == "success" for dep in task.dependencies):
                    executable_tasks.append(task)
            
            if not executable_tasks:
                print("No executable tasks found - possible circular dependency")
                # Mark remaining tasks as blocked
                for task in tasks_to_execute:
                    task.status = "blocked"
                    task.stderr = "Blocked due to dependency failure or circular dependency"
                return False
            
            # Execute the first available task
            task = executable_tasks[0]
            task.status = "running"
            success = self._execute_task(task)
            
            if success:
                task.status = "success"
                self.completed_tasks.add(task.name)
                tasks_to_execute.remove(task)
                print(f"✓ Completed task: {task.name}")
                
                # Add delay between tasks
                if tasks_to_execute:  # Only delay if there are more tasks
                    time.sleep(0.5)
            else:
                task.status = "error"
                print(f"✗ Failed task: {task.name}")
                # Mark remaining tasks as blocked
                for remaining_task in tasks_to_execute:
                    if remaining_task != task:
                        remaining_task.status = "blocked"
                        remaining_task.stderr = "Blocked due to previous task failure"
                return False
        
        print("All tasks completed successfully!")
        return True
    
    def _execute_task(self, task: Task) -> bool:
        """Execute a single task and its subtasks."""
        print(f"Executing task: {task.name}")
        
        try:
            # If this is a ToolCall, execute it directly
            if isinstance(task, ToolCall):
                success = self._execute_tool_call(task)
                if not success and not task.stderr:
                    task.stderr = f"Tool call {task.tool_name} failed"
                return success
            
            # Handle screen verification tasks
            if hasattr(task, 'verify_screen_change') and task.verify_screen_change:
                success = self._execute_verified_task(task)
                if not success and not task.stderr:
                    task.stderr = "Screen verification failed"
                return success
            
            # For regular tasks, execute all subtasks
            if task.subtasks:
                success = self._execute_tasks(task.subtasks)
                if not success and not task.stderr:
                    task.stderr = "Subtask execution failed"
                return success
            
            # If no subtasks, consider it completed
            print(f"Task {task.name} has no subtasks - marking as completed")
            task.stdout = "Task completed with no subtasks"
            return True
            
        except Exception as e:
            task.stderr = str(e)
            print(f"Exception in task {task.name}: {e}")
            return False
    
    def _execute_tool_call(self, tool_call: ToolCall) -> bool:
        """Execute a tool call."""
        print(f"Executing tool: {tool_call.tool_name} with params {tool_call.params}")
        
        if hasattr(self.tools, tool_call.tool_name):
            method = getattr(self.tools, tool_call.tool_name)
            try:
                # Special handling for run_shell_command to pass task for output capture
                if tool_call.tool_name == "run_shell_command":
                    result = method(task=tool_call, **tool_call.params)
                else:
                    result = method(**tool_call.params)
                    
                if result:
                    if not tool_call.stdout:  # Only set if not already set by tool
                        tool_call.stdout = f"Tool {tool_call.tool_name} executed successfully"
                else:
                    if not tool_call.stderr:  # Only set if not already set by tool
                        tool_call.stderr = f"Tool {tool_call.tool_name} returned False"
                return result
            except Exception as e:
                tool_call.stderr = f"Tool {tool_call.tool_name} raised exception: {str(e)}"
                return False
        else:
            tool_call.stderr = f"Unknown tool: {tool_call.tool_name}"
            print(f"Unknown tool: {tool_call.tool_name}")
            return False
    
    def _execute_verified_task(self, task: Task) -> bool:
        """Execute a task with screen change verification."""
        print(f"Executing verified task: {task.name}")
        
        # Generate unique screenshot names using UUID
        unique_id = str(uuid.uuid4())[:8]
        task_id = task.name.replace(' ', '_').replace(':', '').replace('(', '').replace(')', '')
        before_name = f"before_{task_id}_{unique_id}"
        after_name = f"after_{task_id}_{unique_id}"
        
        # Take before screenshot
        print("Taking before screenshot...")
        if not self.tools.screenshot(before_name):
            task.stderr = "Failed to take before screenshot"
            print("Failed to take before screenshot")
            return False
        
        # Execute the task's subtasks
        if task.subtasks:
            success = self._execute_tasks(task.subtasks)
            if not success:
                task.stderr = "Task execution failed during verification"
                print("Task execution failed")
                return False
        else:
            print("No subtasks to execute")

        time.sleep(1)
        
        # Take after screenshot
        print("Taking after screenshot...")
        if not self.tools.screenshot(after_name):
            task.stderr = "Failed to take after screenshot"
            print("Failed to take after screenshot")
            return False
        
        # Compare screenshots
        print("Comparing screenshots...")
        verification_success = self.tools.compare_screenshots(before_name, after_name)
        
        if verification_success:
            task.stdout = f"Screen verification passed - change detected between {before_name} and {after_name}"
            print(f"✓ Screen verification passed for task: {task.name}")
            return True
        else:
            task.stderr = f"Screen verification failed - no change detected between {before_name} and {after_name}"
            print(f"✗ Screen verification failed for task: {task.name}")
            return False