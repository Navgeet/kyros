import base64
import json
from typing import List, Dict, Any, Optional, Callable
import subprocess
import tempfile
import os
from PIL import Image
from io import BytesIO
from agents.base_agent import BaseAgent
from utils import strip_json_code_blocks, compact_context, count_words


class BossAgent(BaseAgent):
    """Boss agent that orchestrates other agents and communicates with the user"""

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        base_url: str = None,
        websocket_callback: Optional[Callable] = None,
        config_dict: Dict[str, Any] = None
    ):
        super().__init__(
            agent_id=agent_id,
            api_key=api_key,
            base_url=base_url,
            websocket_callback=websocket_callback,
            agent_name="boss",
            config_dict=config_dict
        )
        self.subagents: Dict[str, Any] = {}
        self.config_dict = config_dict
        self.response_history: List[Dict[str, Any]] = []
        self.compacted_context: str = ""
        self.step_count: int = 0

    def get_system_prompt(self) -> str:
        """Get the system prompt for the boss agent"""
        return """# Identity

You are a computer-use agent. You coordinate tasks by delegating to specialized agents:

## Available Agents

1. **GUIAgent**: Handles mouse and keyboard interactions with GUI
   - Use for: clicking, typing, hotkeys, GUI automation

2. **ShellAgent**: Executes shell commands
   - Use for: running terminal commands, file operations, system tasks

3. **ResearchAgent**: Researches information using Tavily
   - Use for: searching the web, gathering information

## Your Responsibilities

1. Analyze the user's request and the current screenshot
2. For a complex task, first create a comprehensive plan and get that approved from user
3. Delegate manageable subtasks to sub-agents
4. Handle agent responses and coordinate multi-step workflows
5. Report results back to the user


## Example outputs

task delegation:
{
  "thought": "Your reasoning about the task",
  "action": {
    "type": "delegate",
    "agent": "GUIAgent|ShellAgent|ResearchAgent",
    "message": "task for the agent (e.g., 'Find all Python files', NOT 'run find . -name *.py')"
  }
}

communication with user:
{
  "thought": "Your reasoning about the task",
  "action": {
    "type": "message",
    "message": "does this plan look good?",
    "wait_for_response": true
  }
}

finishing up:
{
  "thought": "Your reasoning about the task",
  "action": {
    "type": "exit",
    "message": "a helpful message to be sent to user"
  }
}

## Important Rules

- CRITICAL: Respond with ONLY valid JSON. Do NOT include any text before or after the JSON.
- Always analyze the screenshot before making decisions
- When delegating: don't send the exact shell command or click coordinate, let the agent figure it out.
- When delegating: don't send too large or too small a task, achieve a middle ground
- Use "exit" action type when the task is complete

## Response Format Requirements

Your response must be ONLY a JSON object with no additional text:
- ✓ CORRECT: {"thought": "...", "action": {...}}
- ✗ WRONG: Here's what I'll do: {"thought": "...", "action": {...}}
"""

    def get_screenshot_base64(self) -> str:
        """Capture screenshot and return as base64-encoded JPEG using scrot"""
        # Create temp file and close it immediately so scrot can write to it
        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)  # Close the file descriptor immediately

        # Remove the empty file that mkstemp created
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        try:
            # Capture with scrot (ensure DISPLAY is set)
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            result = subprocess.run(
                ["scrot", temp_path],
                capture_output=True,
                timeout=2,
                env=env
            )

            if result.returncode != 0:
                raise RuntimeError(f"scrot failed with code {result.returncode}: stdout={result.stdout.decode()}, stderr={result.stderr.decode()}")

            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError(f"scrot did not create screenshot file at {temp_path}. Return code: {result.returncode}, stdout={result.stdout.decode()}, stderr={result.stderr.decode()}")

            # Load and convert to JPEG
            screenshot = Image.open(temp_path)
            buffer = BytesIO()
            screenshot.save(buffer, format="JPEG", quality=75)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response"""
        try:
            # Increment step count
            self.step_count += 1

            # Get compaction config
            compaction_config = self.config_dict.get('compaction', {}) if self.config_dict else {}
            trigger_steps = compaction_config.get('trigger', {}).get('steps', 5)
            trigger_words = compaction_config.get('trigger', {}).get('words', 1000)

            # Get current screenshot
            screenshot = self.get_screenshot_base64()

            # Store current response in history
            current_response = {
                "user_request": message.get('content', ''),
                "agent_responses": message.get('agent_responses', [])
            }
            self.response_history.append(current_response)

            # Check if compaction is needed
            context_text = str(self.response_history)
            word_count = count_words(context_text)

            if self.step_count >= trigger_steps or word_count >= trigger_words:
                # Compact the context
                task = message.get('content', '')
                self.compacted_context = compact_context(
                    self.response_history,
                    task,
                    self.config_dict,
                    self.websocket_callback,
                    self.agent_id,
                    self.agent_name
                )
                # Clear history after compaction
                self.response_history = []
                self.step_count = 0

            # Build context text
            context_parts = []
            if self.compacted_context:
                context_parts.append(f"Previous Context (compacted):\n{self.compacted_context}\n\n")

            context_parts.append(f"User Request: {message.get('content', '')}\n\nAgent Responses: {message.get('agent_responses', [])}")

            # Build messages for LLM
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "".join(context_parts)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": screenshot
                            }
                        }
                    ]
                }
            ]

            # Send screenshot update
            self.send_llm_update("screenshot", {
                "screenshot": screenshot
            })

            # Call LLM and get response
            response = self.call_llm(
                messages=messages,
                system=self.get_system_prompt()
            )

            # Parse response
            try:
                cleaned_response = strip_json_code_blocks(response)
                response_data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If not valid JSON, treat as a thought/response
                response_data = {
                    "thought": response,
                    "action": {
                        "type": "respond",
                        "message": response
                    }
                }

            return response_data

        except Exception as e:
            print(f"ERROR: BossAgent failed to process message: {e}")
            import traceback
            traceback.print_exc()
            return {
                "thought": f"Error occurred: {str(e)}",
                "action": {
                    "type": "respond",
                    "message": f"Error: {str(e)}"
                }
            }

    def get_or_create_agent(self, agent_type: str) -> Any:
        """Get existing agent or create a new one (single instance per type)"""
        # Check if agent of this type already exists
        if agent_type in self.subagents:
            return self.subagents[agent_type]

        # Create new agent instance
        try:
            if agent_type == "GUIAgent":
                from agents.gui_agent import GUIAgent
                agent = GUIAgent(
                    websocket_callback=self.websocket_callback,
                    config_dict=self.config_dict
                )
            elif agent_type == "ShellAgent":
                from agents.shell_agent import ShellAgent
                agent = ShellAgent(
                    websocket_callback=self.websocket_callback,
                    config_dict=self.config_dict
                )
            elif agent_type == "ResearchAgent":
                from agents.research_agent import ResearchAgent
                agent = ResearchAgent(
                    websocket_callback=self.websocket_callback,
                    config_dict=self.config_dict
                )
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")

            # Store by agent type (single instance per type)
            self.subagents[agent_type] = agent
            return agent

        except Exception as e:
            print(f"ERROR: Failed to create {agent_type}: {e}")
            import traceback
            traceback.print_exc()
            raise
