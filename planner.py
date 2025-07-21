import requests
import json
from typing import Dict, List, Any

class Task:
    def __init__(self, name: str):
        self.name = name
        self.subtasks = []
        self.dependencies = []
    
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
            'dependencies': [dep.name if hasattr(dep, 'name') else str(dep) for dep in self.dependencies]
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
    
    def generate_plan(self, user_input: str) -> List[Task]:
        prompt = f"""
You are a task planner. Given a user request, generate a sequence of tasks to accomplish it.

Available tools:
- focus_window(name): Find and focus a window by name
- launch(path): Launch an application 
- hotkey(keys): Send keyboard shortcut (e.g. "ctrl+t")
- type(text): Type text

User request: "{user_input}"

Generate a task plan as Python code. Example:



Input: "search google for restaurants near me"
Output:
```python
a = Task("search google for restaurants near me")
b = Task("focus chrome window")
c = Task("open new tab")
d = Task("type query and press enter")
a.addSubtasks(b, c, d)
c.depends_on(b)
d.depends_on(c)
b.addSubtasks(ToolCall("focus_window", {{"name": "chrome"}}))
c.addSubtasks(ToolCall("hotkey", {{"keys": "ctrl+t"}}))
c.addSubtasks(ToolCall("type", {{"text": "restaurants near me"}}), ToolCall("hotkey", {{"keys": "enter"}}))

tasks.append(a) # this is important
```

Return only the Python code to create the Tasks, and append it to the `tasks` list. Do not include any other text or explanations.
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
                
                # Extract Python code from response
                if '```python' in code:
                    code = code.split('```python')[1].split('```')[0].strip()
                elif '```' in code:
                    code = code.split('```')[1].split('```')[0].strip()
                
                # Execute the generated code to create Tasks
                tasks = []
                exec(code, {'Task': Task, 'ToolCall': ToolCall, 'tasks': tasks})
                return tasks
            else:
                raise Exception(f"Failed to generate plan: {response.status_code} {response.text}")
                
        except Exception as e:
            print(f"Error calling Ollama: {e}")
    
