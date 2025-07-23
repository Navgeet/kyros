import requests
import json
from typing import Dict, List, Any

class Task:
    def __init__(self, name: str, verify_screen_change: bool = False):
        self.name = name
        self.subtasks = []
        self.dependencies = []
        self.verify_screen_change = verify_screen_change
    
    def addSubtasks(self, *subtasks):
        """Add one or more subtasks to this task"""
        for subtask in subtasks:
            self.subtasks.append(subtask)
    
    def depends_on(self, *tasks):
        """Mark this task as dependent on other tasks"""
        for task in tasks:
            self.dependencies.append(task)
    
    def to_dict(self):
        return {
            'name': self.name,
            'subtasks': [subtask.to_dict() if hasattr(subtask, 'to_dict') else str(subtask) for subtask in self.subtasks],
            'dependencies': [dep.name if hasattr(dep, 'name') else str(dep) for dep in self.dependencies],
            'verify_screen_change': self.verify_screen_change
        }

class ToolCall(Task):
    def __init__(self, tool_name: str, params: Dict[str, Any]):
        super().__init__(f"{tool_name}({params})")
        self.tool_name = tool_name
        self.params = params
    
    def to_dict(self):
        return {
            'type': 'tool_call',
            'tool_name': self.tool_name,
            'params': self.params,
            'name': self.name
        }


class Planner:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
    
    def generate_plan(self, user_input: str, max_retries: int = 3) -> List[Task]:
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"Retrying plan generation (attempt {attempt + 1}/{max_retries})...")
            
            plan = self._generate_single_plan(user_input)
            
            # Validation disabled for now
            tasks = []
            exec(plan, {'Task': Task, 'ToolCall': ToolCall, 'tasks': tasks})
            return tasks
            
            if attempt == max_retries - 1:
                print("Max retries reached - plan generation failed")
                return []
        
        return []
    
    def _generate_single_plan(self, user_input: str) -> str:
        prompt = f"""
<Instruction>
You are a task planner. Given a user request, generate tasks to accomplish it. Return the python code only.

<Example>
<Input>search google for restaurants near me</Input>
<Output>
a = Task("search google for restaurants near me")
b = Task("focus chrome window", verify_screen_change=True)
c = Task("open new tab", verify_screen_change=True)
d = Task("type query and press enter", verify_screen_change=True)
a.addSubtasks(b, c, d)
c.depends_on(b)
d.depends_on(c)
b.addSubtasks(ToolCall("focus_window", {{"name": "chrome"}}))
c.addSubtasks(ToolCall("hotkey", {{"keys": "ctrl+t"}}))
d.addSubtasks(ToolCall("type", {{"text": "restaurants near me"}}), ToolCall("hotkey", {{"keys": "enter"}}))

tasks.append(a) # this is important
</Output>
</Example>

<Tools>
**Math Operations**
- add(a, b): Add two integers

**Mouse/Keyboard**
- move_to(x, y): Move mouse to coordinates
- click(x, y)`: Left click at coordinates
- hotkey(keys): Send keyboard shortcut (e.g. "ctrl+t")
- type(text): Type text

**Screen**
- screenshot(name): Take a screenshot and save with given name
- compare_screenshots(before, after): Compare two screenshots to detect changes

**Window management**
- focus_window(name): Find and focus a window by name

**Process management**
- run_shell_command(args): Run a shell command
</Tools>

<Rules>
1. If a task changes the screen (like opening an app, running a command), then it should be initialized with `verify_screen_change=True`
</Rules>
</Instruction>
<UserInput>
{user_input}
</UserInput>
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen3:30b-a3b",
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                code = result.get('response', '')
                
                # Extract thinking content
                thinking_content = ""
                if '<think>' in code and '</think>' in code:
                    thinking_content = code.split('<think>')[1].split('</think>')[0].strip()
                    print("💭 Thinking:")
                    print(f"\033[90m{thinking_content}\033[0m")  # Grey text
                    print()
                
                return code.split('</think>')[1].strip()
                
        except Exception as e:
            print(f"Error calling Ollama: {e}")
    
    def validate_plan(self, plan: str, user_input: str) -> bool:
        """Validate if the generated plan follows the rules and accomplishes the user request."""
        
        validation_prompt = f"""
<Instruction>
You are a plan validator. Check if the given plan follows these rules and accomplishes the user request:

## Rules to check:
1. Tasks that modify the UI (like opening an app) should be wrapped in VerifiedTaskUsingScreenChange
2. Dependencies should be logical (task B depends on task A if A must complete before B)
3. All top level tasks should be appended to the global tasks list
4. The output should be wrapped in ```python and ``` tags
5. <var>.wrapped_task.addSubtasks(<subtasks>) should only be used for instance of VerifiedTaskUsingScreenChange, not Task


## Available tools:
- add(a, b): Add two integers
- move_to(x, y): Move mouse to coordinates  
- click(x, y): Left click at coordinates
- hotkey(keys): Send keyboard shortcut
- type(text): Type text
- screenshot(name): Take a screenshot
- compare_screenshots(before, after): Compare screenshots
- focus_window(name): Focus a window by name
- run_shell_command(args): Run a shell command

Respond with either "VALID" or "INVALID: [reason]"
</Instruction>

<UserRequest>
{user_input}
</UserRequest>

<GeneratedPlan>
{plan}
</GeneratedPlan>
"""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen3:30b-a3b",
                    "prompt": validation_prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                validation_result = result.get('response', '').strip()
                
                if validation_result.startswith("VALID"):
                    print("✓ Plan validation passed")
                    return True
                else:
                    print(f"✗ Plan validation failed: {validation_result}")
                    return False
            else:
                print(f"Error validating plan: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error calling Ollama for validation: {e}")
            return False
