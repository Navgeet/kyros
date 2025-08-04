from typing import Dict, List, Any, Union
import time
import uuid
from tools import Tools

class Executor:
    def __init__(self):
        self.tools = Tools()
        self.completed_tasks = set()
    
    def execute_plan(self, plan: Dict) -> bool:
        """Execute JSON plan in the correct order based on dependencies."""
        tasks = plan.get('tasks', [])
        if not tasks:
            return True
        
        # Create a lookup table for task references
        task_lookup = {task.get('id', i): task for i, task in enumerate(tasks)}
        
        # Find top-level tasks (not referenced as subtasks)
        subtask_ids = set()
        for task in tasks:
            for subtask_id in task.get('subtasks', []):
                subtask_ids.add(subtask_id)
        
        top_level_tasks = [task for task in tasks if task.get('id', 0) not in subtask_ids]
        
        result = self._execute_json_tasks(top_level_tasks, task_lookup)
        
        # Convert "replan" result to False for the agent (to trigger retry)
        # but the task statuses will contain the replan information
        if result == "replan":
            return False
        
        return result
    
    def _execute_json_tasks(self, tasks: List[Dict], task_lookup: Dict[int, Dict]) -> Union[bool, str]:
        """Execute a list of JSON tasks, handling dependencies."""
        tasks_to_execute = tasks.copy()
        
        while tasks_to_execute:
            # Find tasks that can be executed (all dependencies completed)
            executable_tasks = []
            
            for task in tasks_to_execute:
                # Check if all dependencies are completed
                dependencies_met = True
                for dep_id in task.get('dependencies', []):
                    dep_task = task_lookup.get(dep_id)
                    if not dep_task or dep_task.get('status') != "success":
                        dependencies_met = False
                        break
                
                if dependencies_met:
                    executable_tasks.append(task)
            
            if not executable_tasks:
                print("No executable tasks found - possible circular dependency")
                # Mark remaining tasks as blocked
                for task in tasks_to_execute:
                    task['status'] = "blocked"
                    task['stderr'] = "Blocked due to dependency failure or circular dependency"
                return False
            
            # Execute the first available task
            task = executable_tasks[0]
            task['status'] = "running"
            result = self._execute_json_task(task, task_lookup)
            
            if result == "replan":
                # Handle replan case - propagate up
                return "replan"
            elif result:
                task['status'] = "success"
                task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
                self.completed_tasks.add(task_name)
                tasks_to_execute.remove(task)
                print(f"✓ Completed task: {task_name}")
                
                # Add delay between tasks
                if tasks_to_execute:  # Only delay if there are more tasks
                    time.sleep(0.5)
            else:
                # Handle actual task failure (result is False)
                task['status'] = "error"
                task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
                print(f"✗ Failed task: {task_name}")
                
                # Mark remaining tasks as blocked for actual errors
                for remaining_task in tasks_to_execute:
                    if remaining_task != task:
                        remaining_task['status'] = "blocked"
                        remaining_task['stderr'] = "Blocked due to previous task failure"
                return False
        
        print("All tasks completed successfully!")
        return True
    
    def _execute_json_task(self, task: Dict, task_lookup: Dict[int, Dict]) -> Union[bool, str]:
        """Execute a single JSON task and its subtasks."""
        task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
        print(f"Executing task: {task_name}")
        
        try:
            # If this is a ToolCall, execute it directly
            if task.get('type') == 'tool_call':
                success = self._execute_json_tool_call(task)
                if not success and not task.get('stderr'):
                    task['stderr'] = f"Tool call {task.get('tool_name')} failed"
                return success
            
            # If this is a Plan, mark it for replanning
            if task.get('type') == 'plan':
                task['status'] = "replan"
                return "replan"  # Return "replan" to trigger proper handling
            
            # Handle screen verification tasks
            if task.get('verify_screen_change'):
                result = self._execute_verified_json_task(task, task_lookup)
                
                # Handle replan case specially
                if result == "replan":
                    task['status'] = "replan"
                    return "replan"
                elif not result and not task.get('stderr'):
                    task['stderr'] = "Screen verification failed"
                
                return result
            
            # For regular tasks, execute all subtasks
            subtask_ids = task.get('subtasks', [])
            if subtask_ids:
                subtasks = [task_lookup[sid] for sid in subtask_ids if sid in task_lookup]
                result = self._execute_json_tasks(subtasks, task_lookup)
                
                # Handle replan case specially
                if result == "replan":
                    task['status'] = "replan"
                    return "replan"
                elif not result and not task.get('stderr'):
                    task['stderr'] = "Subtask execution failed"
                
                return result
            
            # If no subtasks, consider it completed
            print(f"Task {task_name} has no subtasks - marking as completed")
            task['stdout'] = "Task completed with no subtasks"
            return True
            
        except Exception as e:
            task['stderr'] = str(e)
            print(f"Exception in task {task_name}: {e}")
            return False
    
    def _execute_json_tool_call(self, task: Dict) -> bool:
        """Execute a JSON tool call."""
        tool_name = task.get('tool_name')
        params = task.get('params', {})
        print(f"Executing tool: {tool_name} with params {params}")
        
        if hasattr(self.tools, tool_name):
            method = getattr(self.tools, tool_name)
            try:
                # Special handling for tools that need task for output capture
                if tool_name in ["run_shell_command", "query_screen"]:
                    result = method(task=task, **params)
                else:
                    result = method(**params)
                    
                if result:
                    if not task.get('stdout'):  # Only set if not already set by tool
                        task['stdout'] = f"Tool {tool_name} executed successfully"
                else:
                    if not task.get('stderr'):  # Only set if not already set by tool
                        task['stderr'] = f"Tool {tool_name} returned False"
                return result
            except Exception as e:
                task['stderr'] = f"Tool {tool_name} raised exception: {str(e)}"
                return False
        else:
            task['stderr'] = f"Unknown tool: {tool_name}"
            print(f"Unknown tool: {tool_name}")
            return False
    
    def _execute_verified_json_task(self, task: Dict, task_lookup: Dict[int, Dict]) -> Union[bool, str]:
        """Execute a JSON task with screen change verification."""
        task_name = task.get('name', f"Task {task.get('id', 'unknown')}")
        print(f"Executing verified task: {task_name}")
        
        # Generate unique screenshot names using UUID
        unique_id = str(uuid.uuid4())[:8]
        task_id = task_name.replace(' ', '_').replace(':', '').replace('(', '').replace(')', '')
        before_name = f"before_{task_id}_{unique_id}"
        after_name = f"after_{task_id}_{unique_id}"
        
        # Take before screenshot
        print("Taking before screenshot...")
        if not self.tools.screenshot(before_name):
            task['stderr'] = "Failed to take before screenshot"
            print("Failed to take before screenshot")
            return False
        
        # Execute the task's subtasks
        subtask_ids = task.get('subtasks', [])
        if subtask_ids:
            subtasks = [task_lookup[sid] for sid in subtask_ids if sid in task_lookup]
            result = self._execute_json_tasks(subtasks, task_lookup)
            
            # Handle replan case specially
            if result == "replan":
                task['status'] = "replan"
                return "replan"
            elif not result:
                task['stderr'] = "Task execution failed during verification"
                print("Task execution failed")
                return False
        else:
            print("No subtasks to execute")

        time.sleep(1)
        
        # Take after screenshot
        print("Taking after screenshot...")
        if not self.tools.screenshot(after_name):
            task['stderr'] = "Failed to take after screenshot"
            print("Failed to take after screenshot")
            return False
        
        # Compare screenshots
        print("Comparing screenshots...")
        verification_success = self.tools.compare_screenshots(before_name, after_name)
        
        if verification_success:
            task['stdout'] = f"Screen verification passed - change detected between {before_name} and {after_name}"
            print(f"✓ Screen verification passed for task: {task_name}")
            return True
        else:
            task['stderr'] = f"Screen verification failed - no change detected between {before_name} and {after_name}"
            print(f"✗ Screen verification failed for task: {task_name}")
            return False