import json
from typing import List, Dict, Any, Optional, Callable
from agents.base_agent import BaseAgent
from utils import strip_json_code_blocks, compact_context, count_words


class BrowserBossAgent(BaseAgent):
    """Browser boss agent that orchestrates GUI agent, XPath agent, and Browser Action agent"""

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
            agent_name="browser_boss",
            config_dict=config_dict
        )
        self.subagents: Dict[str, Any] = {}
        self.config_dict = config_dict
        self.response_history: List[Dict[str, Any]] = []
        self.compacted_context: str = ""
        self.step_count: int = 0

    def get_system_prompt(self) -> str:
        """Get the system prompt for the browser boss agent"""
        return """# Identity

You are a Browser Boss Agent. You coordinate browser automation tasks by delegating to specialized agents:

## Available Agents

1. **GUIAgent**: Handles mouse and keyboard interactions with GUI
   - Use for: visually locating elements on screen by moving the mouse cursor

2. **XPathAgent**: Extracts and validates XPath expressions for elements
   - Use for: getting XPath of an element at specific coordinates (after GUIAgent positions the cursor)

3. **BrowserActionAgent**: Performs browser actions using Playwright
   - Use for: all browser operations (launch, navigate, click, input, etc.) using XPath

## Your Responsibilities

1. Analyze the user's browser automation request
2. Delegate sub-tasks to appropriate agents
3. Coordinate the workflow between agents
4. Report results back to the user

## Typical Workflow for Element Interaction

1. Delegate to **GUIAgent**: "Move mouse cursor to point at [element description]"
2. Get cursor position from GUI agent response
3. Delegate to **XPathAgent**: "Find XPath for element at coordinates (x, y)"
4. Get XPath from XPath agent response
5. Delegate to **BrowserActionAgent**: "Click element with xpath [xpath]" (or other action)

## Example Outputs

Task delegation:
{
  "thought": "Your reasoning about the task",
  "action": {
    "type": "delegate",
    "agent": "GUIAgent|XPathAgent|BrowserActionAgent",
    "message": "task for the agent"
  }
}

Communication with user:
{
  "thought": "Your reasoning about the task",
  "action": {
    "type": "message",
    "message": "message to user",
    "wait_for_response": true
  }
}

Finishing up:
{
  "thought": "Your reasoning about the task",
  "action": {
    "type": "exit",
    "message": "completion message"
  }
}

## Important Rules

- CRITICAL: Respond with ONLY valid JSON. Do NOT include any text before or after the JSON.
- Break down browser tasks into steps: locate element (GUI) → get XPath (XPath) → perform action (Browser)
- When delegating: provide clear, specific instructions
- Use "exit" action type when the task is complete

## Response Format Requirements

Your response must be ONLY a JSON object with no additional text:
- ✓ CORRECT: {"thought": "...", "action": {...}}
- ✗ WRONG: Here's what I'll do: {"thought": "...", "action": {...}}
"""

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response"""
        try:
            # Increment step count
            self.step_count += 1

            # Get compaction config
            compaction_config = self.config_dict.get('compaction', {}) if self.config_dict else {}
            trigger_steps = compaction_config.get('trigger', {}).get('steps', 5)
            trigger_words = compaction_config.get('trigger', {}).get('words', 1000)

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
                    "content": "".join(context_parts)
                }
            ]

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
            print(f"ERROR: BrowserBossAgent failed to process message: {e}")
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
            elif agent_type == "XPathAgent":
                from agents.xpath_agent import XPathAgent
                agent = XPathAgent(
                    websocket_callback=self.websocket_callback,
                    config_dict=self.config_dict
                )
            elif agent_type == "BrowserActionAgent":
                from agents.browser_action_agent import BrowserActionAgent
                agent = BrowserActionAgent(
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
