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
    def __init__(self, ollama_url: str = "http://localhost:11434", vllm_url: str = None):
        self.ollama_url = ollama_url
        self.vllm_url = vllm_url or ollama_url
        self.streaming_callback = None
    
    def set_streaming_callback(self, callback):
        """Set callback function to receive streaming output during planning"""
        self.streaming_callback = callback
    
    def generate_plan(self, user_input: str, max_retries: int = 3, conversation_history: List[Dict] = None, regenerate_screen_context: bool = True) -> Dict:
        # Generate screen context only if requested (not during replanning)
        screen_context = ""
        if regenerate_screen_context:
            print("🔍 Analyzing screen...")
            screen_context = '' # 'The image shows a web page titled "testsheepnz.github.io/BasicCalculator.html." The page is a basic calculator with a simple interface. Here is a detailed breakdown:\n\n1. **Applications/Windows**:\n   - The main application is a web browser displaying a calculator page.\n   - There are multiple tabs open in the browser, including "1 (1) WhatsApp," "Basic Calculator," "Imported," "Baka-Updates - M...," "Don\'t use Mongo...," "GeoSpatial Index...," "git.rsbx.net/Docu...", "How to Beat Pro...", "How To Make Yo...", "http-headers-stat...", and "All Bookmarks."\n\n2. **UI Elements**:\n   - **Text Fields**:\n     - Two input fields for "First number" and "Second number."\n     - A dropdown menu for selecting the operation (e.g., "Add," "Subtract," "Multiply," "Divide").\n     - An input field for the answer.\n   - **Buttons**:\n     - A "Calculate" button to perform the operation.\n     - A "Clear" button to clear the input fields.\n   - **Labels**:\n     - Labels for "First number," "Second number," and "Operation."\n     - A checkbox labeled "Integer only."\n   - **Navigation**:\n     - A menu bar at the top with options like "Home," "Search," and "More."\n     - A search bar at the top.\n     - A menu icon for more options.\n     - A "Finish update" button at the top right.\n\n3. **Current State of the Desktop/Applications**:\n   - The desktop is open to a web browser with multiple tabs open.\n   - The main focus is on the calculator page, which is a basic HTML page with a simple calculator interface.\n   - The browser is likely being used for web development or testing purposes.\n\n4. **Relevant Context for Task Planning**:\n   - The user is likely testing or developing a basic calculator web page.\n   - The presence of multiple tabs suggests that the user might be testing different functionalities or debugging issues.\n   - The "Finish update" button indicates that the user might be in the process of finalizing or updating the page.\n\nThis description provides a comprehensive overview of the current state of the screen and the context in which it is being used.'
            # screen_context = self._generate_screen_context()
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
                
                # Try to improve the plan using LLM
                try:
                    improved_plan_json = self._improve_plan(plan_json, user_input, conversation_history)
                    if improved_plan_json:
                        improved_parsed_plan = self._parse_json_plan_to_dict(improved_plan_json)
                        print("✨ Plan improved successfully")
                        return improved_parsed_plan
                    else:
                        print("⚠️ Plan improvement failed, using original plan")
                except Exception as improve_error:
                    print(f"⚠️ Plan improvement error: {improve_error}, using original plan")
                
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
                    "model": "qwen2.5vl:3b",
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
            
            # Handle both old format ({"tasks": [...]}) and new format ([{message: "..."}, {tasks: [...]}])
            if isinstance(plan_data, list):
                # New format: array of messages and task objects
                return {"items": plan_data}
            elif "tasks" in plan_data:
                # Old format: wrap in items for consistency
                return {"items": [{"tasks": plan_data["tasks"]}]}
            else:
                # Direct task list format
                return {"items": [{"tasks": plan_data}]}
            
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format: {e}")
        except Exception as e:
            raise Exception(f"Error parsing plan: {e}")
    
    
    def _generate_single_plan(self, user_input: str, conversation_history: List[Dict] = None, screen_context: str = "") -> str:
        try:
            # Add OpenAI client import at the top if needed
            from openai import OpenAI

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

Return an array that can contain:
- Message objects: {{"message": "response to user"}} - for communicating with the user
- Task objects: {{"tasks": [...]}} - for defining executable tasks

You can mix messages and tasks in any order to provide user feedback and define actions.

## Interpolation Support
Messages support interpolation to reference task outputs:
- `{{{{task.id}}}}` - References the task name
- `{{{{task.id.stdout}}}}` - References the stdout output of a task
- `{{{{task.id.stderr}}}}` - References the stderr output of a task
- `{{{{task.id.property}}}}` - References any property of a task

Example: "The result is {{task.1.stdout}}" will be replaced with the actual stdout of task 1.

{context_section}

<Examples>
<Example>
<Input>search google for restaurants near me</Input>
<Output>
```json
[
  {{"message": "I'll help you search for restaurants on Google. Let me open a new tab and perform the search."}},
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
]
```
</Output>
</Example>
<Example>
<Input>click on the search box</Input>
<Output>
```json
[
  {{"message": "I need to locate the search box first, then I'll click on it."}},
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
        "params": {{"query": "locate the search box"}},
      }},
      {{
        "id": 2,
        "type": "plan",
        "dependencies": [1],
      }}
    ]
  }}
]
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
    {{"id": 1,"type": "tool_call","tool_name": "query_screen", "params": {{"query": "locate the search box"}}, "status": "success", "stdout": "click(x=0.4089, y=0.6493)"}},
    {{"id": 2,"type": "plan", "dependencies": [1], "status": "replan"}}
  ]
}}}}
]
</State>
<Output>
```json
[
  {{"message": "Great! I found the search box coordinates. Now I'll click on it."}},
  {{
    "tasks": [
      {{"id": 0, "type": "task", "name": "click on the search box", "verify_screen_change": true, "subtasks": [1, 2]}},
      {{"id": 1, "type": "tool_call", "tool_name": "query_screen", "params": {{"query": "locate the search box"}}, "status": "success", "stdout": "click(x=0.4089, y=0.6493)"}},
      {{"id": 2, "type": "tool_call", "tool_name": "click", "params": {{"x": 0.4089, "y": 0.6493}}, "verify_screen_change": true, "dependencies": [1]}},
    ]
  }}
]
```
</Output>
<Explain>
After the first attempt, we got the coordinates of the search box from `query_screen`.
Now we add new tasks to replace the Plan task
</Explain>
</Example>

<Example>
<Input>what is 2+2?</Input>
<Output>
```json
[
  {{
    "tasks": [
      {{
        "id": 0,
        "type": "task",
        "name": "calculate 2+2",
        "verify_screen_change": false,
        "subtasks": [1]
      }},
      {{
        "id": 1,
        "type": "tool_call",
        "tool_name": "add",
        "params": {{"a": 2, "b": 2}}
      }}
    ]
  }},
  {{"message": "The result of 2+2 is {{{{task.1.stdout}}}}"}}
]
```
</Output>
<Explain>
This example shows interpolation in a single plan. The message uses `{{{{task.1.stdout}}}}` to reference the output of the add tool call.
When the agent processes this message after executing the tasks, it will replace `{{{{task.1.stdout}}}}` with "4", 
so the user sees: "The result of 2+2 is 4"
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
    - locate the input field for email
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
            
            # Use OpenAI client with vLLM endpoint like foo.py
            client = OpenAI(
                api_key="EMPTY",
                base_url=self.vllm_url
            )
            
            messages = [{"role": "user", "content": prompt}]
            stream = client.chat.completions.create(
                model="Qwen/Qwen3-4B-Thinking-2507",
                messages=messages,
                stream=True,
                temperature=0.6,
                top_p=0.95,
                extra_body={
                    "top_k": 20,
                    "min_p": 0,
                    "presence_penalty": 1
                }
            )
            
            print("🤖 Generating plan...")
            printed_reasoning_content = False
            printed_content = False
            full_response = ""
            
            for chunk in stream:
                reasoning_content = None
                content = None
                
                # Check the content is reasoning_content or content
                if hasattr(chunk.choices[0].delta, "reasoning_content"):
                    reasoning_content = chunk.choices[0].delta.reasoning_content
                elif hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content

                if reasoning_content is not None:
                    if not printed_reasoning_content:
                        printed_reasoning_content = True
                        print("💭 Thinking:", end="", flush=True)
                        # Call streaming callback for thinking header
                        if self.streaming_callback:
                            self.streaming_callback("thinking", "💭 Thinking:")
                    print(f"\033[90m{reasoning_content}\033[0m", end="", flush=True)
                    # Call streaming callback for reasoning content
                    if self.streaming_callback:
                        self.streaming_callback("thinking", reasoning_content)
                elif content is not None:
                    if not printed_content:
                        printed_content = True
                        print("\n📋 Plan:", end="", flush=True)
                        # Call streaming callback for plan header
                        if self.streaming_callback:
                            self.streaming_callback("plan", "\n📋 Plan:")
                    print(content, end="", flush=True)
                    full_response += content
                    # Call streaming callback for plan content
                    if self.streaming_callback:
                        self.streaming_callback("plan", content)
            
            print()  # Final newline
            return full_response.strip()
                
        except Exception as e:
            print(f"Error calling vLLM: {e}")
            planner_logger.error(f"Error calling vLLM: {e}", exc_info=True)
            raise
    
    def _improve_plan(self, plan_json: str, user_input: str, conversation_history: List[Dict] = None) -> str:
        """Improve the generated plan by calling LLM with a sample prompt."""
        
        # Add conversation history as context if available
        context_section = ""
        if conversation_history:
            state_json = json.dumps(conversation_history, indent=2)
            context_section = f"""
<State>
{state_json}
</State>
"""
        
        improvement_prompt = f"""
<Instruction>
You are a plan optimization expert. Your task is to analyze and improve the given task plan.

Rules:
1. **Efficiency**: Instead of making several calls to vision tools, can we fetch the required info in 1 call?

If the plan is already optimal, return the original plan unchanged.
Return only the improved JSON plan wrapped in ```json code blocks.
</Instruction>

{context_section}

<UserRequest>
{user_input}
</UserRequest>

<OriginalPlan>
{plan_json}
</OriginalPlan>
"""

        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key="EMPTY",
                base_url=self.vllm_url
            )
            
            messages = [{"role": "user", "content": improvement_prompt}]
            response = client.chat.completions.create(
                model="Qwen/Qwen3-4B-Thinking-2507",
                messages=messages,
                stream=False,
                temperature=0.6,
                top_p=0.95,
                extra_body={
                    "top_k": 20,
                    "min_p": 0,
                    "presence_penalty": 1
                }
            )
            
            improved_plan = response.choices[0].message.content.strip()
            print("🔄 Plan improvement completed")
            planner_logger.info(f"Improved plan: {improved_plan}")
            return improved_plan
            
        except Exception as e:
            print(f"Error improving plan: {e}")
            planner_logger.error(f"Error improving plan: {e}", exc_info=True)
            return ""

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
