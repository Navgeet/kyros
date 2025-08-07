import requests
import json
import base64
import pyautogui
from typing import Dict, List, Any
from io import BytesIO
from logger import planner_logger

class Task:
    def __init__(self, name: str, verify_screen_change: bool = False):
        self.name = name
        self.subtasks = []
        self.dependencies = []
        self.verify_screen_change = verify_screen_change
        self.status = "blocked"  # blocked, running, success, error
        self.stdout = ""
        self.stderr = ""
    
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
            'verify_screen_change': self.verify_screen_change,
            'status': self.status,
            'stdout': self.stdout,
            'stderr': self.stderr
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
            'name': self.name,
            'status': self.status,
            'stdout': self.stdout,
            'stderr': self.stderr
        }

class Plan(Task):
    def __init__(self):
        super().__init__("plan")
    
    def to_dict(self):
        return {
            'type': 'plan',
            'status': self.status,
        }


class Planner:
    """Task planner that generates JSON task representations using LLM.
    
    Generates task hierarchies as JSON instead of Python code for better 
    reliability and easier debugging. The JSON is passed directly to the executor.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
    
    def generate_plan(self, user_input: str, max_retries: int = 3, conversation_history: List[Dict] = None, regenerate_screen_context: bool = True) -> Dict:
        # Generate screen context only if requested (not during replanning)
        screen_context = ""
        if regenerate_screen_context:
            print("🔍 Analyzing screen...")
            screen_context = self._generate_screen_context()
        else:
            print("🔄 Replanning without regenerating screen context...")

        for attempt in range(max_retries):
            if attempt > 0:
                print(f"Retrying plan generation (attempt {attempt + 1}/{max_retries})...")
            
            plan_json = self._generate_single_plan(user_input, conversation_history, screen_context)
            print('Generated Plan JSON:\n')
            print(plan_json)
            
            try:
                parsed_plan = self._parse_json_plan_to_dict(plan_json)
                return parsed_plan
            except Exception as e:
                print(f"Error parsing plan JSON: {e}")
                print(f"Plan content: {plan_json}")
                if attempt == max_retries - 1:
                    print("Max retries reached - plan generation failed")
                    return {}
        
        return {}
    
    def _generate_screen_context(self) -> str:
        """Generate screen context using vision model."""
        # Capture current screen as base64
        screenshot = pyautogui.screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        screen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        context_prompt = """
Analyze the current screen image and describe:
1. What applications/windows are visible
2. What UI elements are shown (buttons, text fields, menus, etc.)
3. Current state of the desktop/applications
4. Any relevant context that would be useful for task planning

Provide a concise description of what you see.
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen2.5vl:7b",
                    "prompt": context_prompt,
                    "stream": False,
                    "images": [screen_base64]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                context = result.get('response', '')
                print(f"📄 Screen context: {context}")
                return context
        except Exception as e:
            print(f"Error generating screen context: {e}")
        
        return "Screen context unavailable"
    
    def _parse_json_plan_to_dict(self, plan_json: str) -> Dict:
        """Parse JSON plan response and return as dictionary."""
        try:
            # Extract JSON from response if it's wrapped in code blocks
            if '```json' in plan_json:
                plan_json = plan_json.split('```json')[1].split('```')[0].strip()
            elif '```' in plan_json:
                plan_json = plan_json.split('```')[1].split('```')[0].strip()
            
            plan_data = json.loads(plan_json)
            return plan_data
            
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format: {e}")
        except Exception as e:
            raise Exception(f"Error parsing plan: {e}")
    
    
    def _generate_single_plan(self, user_input: str, conversation_history: List[Dict] = None, screen_context: str = "") -> str:
        try:

            # Add conversation history and screen context as context if available
            context_section = ""
            if conversation_history:
                state_json = json.dumps(conversation_history, indent=2)
                context_section += f"""
<State>
{state_json}
</State>
"""
        
            if screen_context:
                context_section += f"""
<ScreenContext>
{screen_context}
</ScreenContext>
"""

            prompt = f"""
<Instruction>
You are a task planner, you perform the following tasks:
PLAN: Given a user request and screen context, generate tasks to accomplish it.
    If you cannot complete a task, create `Task` nodes for some steps and then create a `Plan` node to trigger replanning.
REPLAN: given previous executed tasks, 
    analyze the output and create new tasks to accomplish the user request.
    If you cannot complete a task, create `Task` nodes for some steps and then create a `Plan` node to trigger replanning.
Return the JSON representation of tasks only.

{context_section}

<Examples>
<Example>
<Input>search google for restaurants near me</Input>
<Output>
```json
{{
  "tasks": [
    {{
      "id": 0,
      "type": "task",
      "name": "search google for restaurants near me",
      "verify_screen_change": false,
      "subtasks": [1, 2, 3],
    }},
    {{
      "id": 1,
      "type": "task", 
      "name": "focus chrome window",
      "verify_screen_change": true,
      "subtasks": [4],
    }},
    {{
      "id": 2,
      "type": "task",
      "name": "open new tab", 
      "verify_screen_change": true,
      "subtasks": [5],
      "dependencies": [1]
    }},
    {{
      "id": 3,
      "type": "task",
      "name": "type query and press enter",
      "verify_screen_change": true, 
      "subtasks": [6, 7],
      "dependencies": [2]
    }},
    {{
      "id": 4,
      "type": "tool_call",
      "tool_name": "focus_window",
      "params": {{"name": "chrome"}},
    }},
    {{
      "id": 5,
      "type": "tool_call",
      "tool_name": "hotkey",
      "params": {{"keys": "ctrl+t"}},
    }},
    {{
      "id": 6,
      "type": "tool_call",
      "tool_name": "type",
      "params": {{"text": "restaurants near me"}},
    }},
    {{
      "id": 7,
      "type": "tool_call", 
      "tool_name": "hotkey",
      "params": {{"keys": "enter"}},
    }}
  ]
}}
```
</Output>
</Example>
<Example>
<Input>click on the search box</Input>
<Output>
```json
{{
  "tasks": [
    {{
      "id": 0,
      "type": "task",
      "name": "click on the search box",
      "verify_screen_change": true,
      "subtasks": [1, 2],
    }},
    {{
      "id": 1,
      "type": "tool_call",
      "tool_name": "query_screen",
      "params": {{"query": "return coordinates for the search box"}},
    }},
    {{
      "id": 2,
      "type": "plan",
      "dependencies": [1],
    }}
  ]
}}
```
</Output>
<Explain>
Since we need to click on the search box, we first locate it on the screen using `query_screen`.
But since we don't know the exact output of `query_screen`, we create a Plan task to handle it.
On the next iteration, the agent will analyze the output of `query_screen` and create a task to click on the search box.
</Explain>
</Example>

<Example>
<Input>click on the search box</Input>
<State>
[
{{"from":"user", "text": "click on the search box"}},
{{"from":"system", "plan": {{
  "tasks": [
    {{"id": 0,"type": "task","name": "click on the search box","verify_screen_change": true,"subtasks": [1, 2], "status": "replan"}},
    {{"id": 1,"type": "tool_call","tool_name": "query_screen", "params": {{"query": "return coordinates for the search box"}}, "status": "success", "stdout": "bbox: (100, 200, 150, 300)"}},
    {{"id": 2,"type": "plan", "dependencies": [1], "status": "replan"}}
  ]
}}}}
]
</State>
<Output>
```json
{{
  "tasks": [
    {{"id": 0, "type": "task", "name": "click on the search box", "verify_screen_change": true, "subtasks": [1, 2]}},
    {{"id": 1, "type": "tool_call", "tool_name": "query_screen", "params": {{"query": "return coordinates for the search box"}}, "status": "success", "stdout": "bbox: (100, 200, 150, 300)"}},
    {{"id": 2, "type": "tool_call", "tool_name": "click", "params": {{"x": 125, "y": 250}}, "verify_screen_change": true, "dependencies": [1]}},
  ]
}}
```
</Output>
<Explain>
After the first attempt, we got the coordinates of the search box from `query_screen`.
Now we add new tasks to replace the Plan task
</Explain>
</Example>
</Examples>

<Tools>
**Math Operations**
- add(a, b): Add two integers

**Mouse/Keyboard**
- move_to(x, y): Move mouse to coordinates
- click(x, y)`: Left click at coordinates
- hotkey(keys): Send keyboard shortcut (e.g. "ctrl+t")
- type(text): Type text

**Screen**
- query_screen(query): Ask questions about the screen. Examples:
    - return coordinates for the input field for email
    - Does the button "Submit" exist on the screen?

**Window management**
- focus_window(name): Find and focus a window by name

**Process management**
- run_shell_command(args): Run a shell command
</Tools>

<Rules>
1. If a task changes the screen (like opening an app, running a command), then it should have `verify_screen_change=true`
2. If a tool returns some output that should be further analyzed, then create a Plan task after the tool call and add it as a subtask.
3. Don't add any subtasks after a Plan task, they will be created during replanning.
4. A tool call cannot have subtasks.
5. Each task must have a unique integer id.
6. Use task ids to reference subtasks and dependencies (not task names).
7. Return only valid JSON wrapped in ```json code blocks.
</Rules>
</Instruction>
<UserInput>
{user_input}
</UserInput>
"""
        

            planner_logger.info(f"prompt: {prompt}\n")
            # # print prompt in yellow
            # print(f"\033[93m{prompt}\033[0m")  # Yellow
            # print()
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen3:30b-a3b",
                    "prompt": prompt,
                    "stream": True
                },
                stream=True
            )
            
            if response.status_code == 200:
                full_response = ""
                in_thinking = False
                thinking_started = False
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            token = chunk.get('response', '')
                            full_response += token
                            
                            # Handle thinking content streaming
                            if not thinking_started and '<think>' in full_response:
                                print("💭 Thinking:")
                                thinking_started = True
                                in_thinking = True
                                # Find the start of thinking content
                                think_start = full_response.rfind('<think>') + 7
                                if len(full_response) > think_start:
                                    thinking_part = full_response[think_start:]
                                    if '</think>' in thinking_part:
                                        # Complete thinking block already available
                                        thinking_content = thinking_part.split('</think>')[0]
                                        print(f"\033[90m{thinking_content}\033[0m", end="", flush=True)
                                        print("\n")  # End thinking section
                                        in_thinking = False
                                    else:
                                        # Partial thinking content - print what we have so far
                                        print(f"\033[90m{thinking_part}\033[0m", end="", flush=True)
                            elif in_thinking:
                                if '</think>' in token:
                                    # End of thinking - print remaining content before the closing tag
                                    thinking_part = token.split('</think>')[0]
                                    if thinking_part:
                                        print(f"\033[90m{thinking_part}\033[0m", end="", flush=True)
                                    print("\n")  # End thinking section with newline
                                    in_thinking = False
                                else:
                                    # Continue thinking content - print this token
                                    print(f"\033[90m{token}\033[0m", end="", flush=True)
                            
                            if chunk.get('done', False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Extract the final code content (after </think> if present)
                if '</think>' in full_response:
                    code = full_response.split('</think>')[1].strip()
                else:
                    code = full_response.strip()
                
                return code
            else:
                print(f"Error: Ollama API returned status {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            planner_logger.error(f"Error calling Ollama: {e}", exc_info=True)
            raise
    
    def validate_plan(self, plan_json: str, user_input: str) -> bool:
        """Validate if the generated JSON plan follows the rules and accomplishes the user request."""
        
        validation_prompt = f"""
<Instruction>
You are a plan validator. Check if the given JSON plan follows these rules and accomplishes the user request:

## Rules to check:
1. Tasks that modify the UI (like opening an app) should have `verify_screen_change=true`
2. Dependencies should be logical (task B depends on task A if A must complete before B)
3. Each task must have a unique integer id
4. Subtasks and dependencies should reference task ids (integers), not names
5. The JSON should be valid and properly formatted
6. Tool calls should have correct tool names and parameters

## Available tools:
- add(a, b): Add two integers
- move_to(x, y): Move mouse to coordinates  
- click(x, y): Left click at coordinates
- hotkey(keys): Send keyboard shortcut
- type(text): Type text
- query_screen(query): Ask questions about the screen
- focus_window(name): Focus a window by name
- run_shell_command(args): Run a shell command

Respond with either "VALID" or "INVALID: [reason]"
</Instruction>

<UserRequest>
{user_input}
</UserRequest>

<GeneratedPlan>
{plan_json}
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
