import json
import base64
import subprocess
import tempfile
import os
from PIL import Image
from io import BytesIO
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from agents.base_agent import BaseAgent
from utils import strip_json_code_blocks, compact_context, count_words, save_screenshot


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
        self.agent_summaries: Dict[str, str] = {}  # Track summaries from agent completions
        self.config_dict = config_dict
        self.response_history: List[Dict[str, Any]] = []
        self.compacted_context: str = ""
        self.step_count: int = 0
        self.summary_log_file = "/tmp/agent_summaries.log"  # Log file for summaries

    def log_summary(self, agent_type: str, summary: str):
        """Log agent summary to file"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"[{timestamp}] {agent_type}: {summary}\n"
            with open(self.summary_log_file, "a") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging summary: {e}")

    def get_screenshot_base64(self) -> str:
        """Capture screenshot of entire screen and return as base64-encoded JPEG using scrot"""
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
                env['DISPLAY'] = ':1'

            result = subprocess.run(
                ["scrot", temp_path],
                capture_output=True,
                timeout=2,
                env=env
            )

            if result.returncode != 0:
                raise RuntimeError(f"scrot failed with code {result.returncode}")

            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError(f"scrot did not create screenshot file at {temp_path}")

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

    def get_system_prompt(self) -> str:
        """Get the system prompt for the browser boss agent"""
        return """# Identity

You are a Browser Boss Agent. You coordinate browser automation tasks by delegating to specialized agents:

## Available Agents

1. **GUIAgent**: Handles mouse and keyboard interactions with GUI
   - Use for: scrolling, click/type (if xpath not available)

2. **XPathAgent**: Extracts and validates XPath expressions for elements
   - Use for: getting XPath of an element using description

3. **BrowserActionAgent**: Performs browser actions using Playwright
   - Use for: all browser operations (launch, navigate, click, input, etc.) using XPath

## Typical Workflow for Automation

1. Delegate to **XPathAgent**: "Find XPath for submit button
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
    "summary": "context about task"
  }
}

## Important Rules

- CRITICAL: Respond with ONLY valid JSON. Do NOT include any text before or after the JSON
- Always analyze the screenshot first
- Prefer using XPathAgent over GUIAgent whenever possible
- Fallback to GUIAgent if XPath not available/working
- Use "exit" action type when the task is complete. In summary, mention the browser state

## Response Format Requirements

Your response must be ONLY a JSON object with no additional text:
- ✓ CORRECT: {"thought": "...", "action": {...}}
- ✗ WRONG: Here's what I'll do: {"thought": "...", "action": {...}}
"""

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response - handles internal delegation loop"""
        try:
            task = message.get('content', '')
            max_iterations = 20
            iteration = 0

            # Initialize agent_responses for this browser task
            # If the message contains context about previously found xpaths, parse it
            initial_agent_responses = []
            if "Known XPaths:" in task:
                # Extract the known xpaths section and build agent_responses
                lines = task.split('\n')
                for line in lines:
                    if 'xpath=' in line:
                        # Extract xpath information and add to initial responses
                        if "✓" in line and "XPathAgent" in line:
                            # Example: "✓ XPathAgent: xpath='//input[@id='number1Field']' for 'First number' field"
                            # We'll store this as a successful XPathAgent result
                            initial_agent_responses.append({
                                "agent_type": "XPathAgent",
                                "response": {
                                    "success": True,
                                    "xpath": line.split("xpath='")[1].split("'")[0] if "xpath='" in line else ""
                                }
                            })

            internal_message = {
                "content": task,
                "agent_responses": initial_agent_responses
            }

            while iteration < max_iterations:
                iteration += 1

                # Increment step count
                self.step_count += 1

                # Get screenshot of entire screen
                screenshot = self.get_screenshot_base64()

                # Save screenshot
                save_screenshot(screenshot, prefix="browser_boss")

                # Get compaction config
                compaction_config = self.config_dict.get('compaction', {}) if self.config_dict else {}
                trigger_steps = compaction_config.get('trigger', {}).get('steps', 5)
                trigger_words = compaction_config.get('trigger', {}).get('words', 1000)

                # Store current response in history
                current_response = {
                    "user_request": internal_message.get('content', ''),
                    "agent_responses": internal_message.get('agent_responses', [])
                }
                self.response_history.append(current_response)

                # Check if compaction is needed
                context_text = str(self.response_history)
                word_count = count_words(context_text)

                if self.step_count >= trigger_steps or word_count >= trigger_words:
                    # Compact the context
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

                context_parts.append(f"User Request: {internal_message.get('content', '')}\n")

                # Extract useful information from agent responses (only show last few to avoid clutter)
                agent_responses = internal_message.get('agent_responses', [])
                if agent_responses:
                    context_parts.append("\nRecent Agent Results (DO NOT REQUEST SAME INFORMATION AGAIN):\n")
                    # Show only the most recent 5 results to avoid context overflow
                    recent_responses = agent_responses[-5:]
                    for i, resp in enumerate(recent_responses, 1):
                        agent_type = resp.get('agent_type', 'Unknown')
                        response = resp.get('response', {})

                        # Extract key information based on agent type
                        if agent_type == "XPathAgent":
                            xpath = response.get('xpath', '')
                            success = response.get('success', False)
                            if xpath:
                                # Show the xpath with success status
                                status = "✓" if success else "✗"
                                context_parts.append(f"{status} XPathAgent [Result {i}]: xpath='{xpath}'\n")
                            else:
                                error = response.get('error', 'Unknown error')
                                context_parts.append(f"✗ XPathAgent [Result {i}] FAILED: {error}\n")
                        elif agent_type == "BrowserActionAgent":
                            success = response.get('success', False)
                            result = response.get('result', response.get('message', ''))
                            if success:
                                context_parts.append(f"✓ BrowserActionAgent [Result {i}]: {result}\n")
                            else:
                                error = response.get('error', 'Unknown error')
                                context_parts.append(f"✗ BrowserActionAgent [Result {i}] FAILED: {error}\n")
                        elif agent_type == "GUIAgent":
                            success = response.get('success', False)
                            if success:
                                context_parts.append(f"✓ GUIAgent [Result {i}]: action completed\n")
                            else:
                                error = response.get('error', 'Unknown error')
                                context_parts.append(f"✗ GUIAgent [Result {i}] FAILED: {error}\n")

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

                action = response_data.get("action", {})
                action_type = action.get("type")

                # Handle exit - task complete
                if action_type == "exit":
                    summary = action.get("summary", "Browser task completed")

                    # Build comprehensive summary including any found XPaths for future reference
                    comprehensive_summary = summary
                    found_xpaths = []
                    for resp in internal_message.get("agent_responses", []):
                        if resp.get("agent_type") == "XPathAgent":
                            response = resp.get("response", {})
                            if response.get("success") and response.get("xpath"):
                                found_xpaths.append(response.get("xpath"))

                    if found_xpaths:
                        comprehensive_summary += f"\n\nKnown XPaths:\n"
                        for xpath in found_xpaths:
                            comprehensive_summary += f"- xpath='{xpath}'\n"

                    # Log the summary
                    self.log_summary("BrowserBossAgent", comprehensive_summary)
                    return {
                        "success": True,
                        "summary": comprehensive_summary,
                        "message": comprehensive_summary,  # Keep for backwards compatibility
                        "thought": response_data.get("thought", ""),
                        "iterations": iteration
                    }

                # Handle delegation to sub-agents
                elif action_type == "delegate":
                    agent_type = action.get("agent")
                    agent_message = action.get("message", "")

                    try:
                        # Get or create the subagent
                        agent = self.get_or_create_agent(agent_type)

                        # Send delegation event
                        if self.websocket_callback:
                            self.websocket_callback({
                                "type": "delegation",
                                "data": {
                                    "from_agent": "BrowserBoss",
                                    "agent_type": agent_type,
                                    "message": agent_message
                                }
                            })

                        # Build message with context if available
                        context = self.agent_summaries.get(agent_type, "")
                        if context:
                            full_message = f"Context from previous work:\n{context}\n\nNew task: {agent_message}"
                        else:
                            full_message = agent_message

                        # Delegate to agent
                        subagent_response = await agent.process_message({
                            "content": full_message
                        })

                        # Extract and store summary from response if agent exited
                        if subagent_response.get("exit") or "summary" in subagent_response:
                            # Prefer 'summary' field over 'message' for backwards compatibility
                            summary = subagent_response.get("summary", subagent_response.get("message", ""))
                            if summary:
                                self.agent_summaries[agent_type] = summary
                                # Log the agent summary
                                self.log_summary(agent_type, summary)

                        # Add subagent response to internal message for next iteration
                        if "agent_responses" not in internal_message:
                            internal_message["agent_responses"] = []

                        internal_message["agent_responses"].append({
                            "agent_type": agent_type,
                            "response": subagent_response
                        })

                    except Exception as e:
                        print(f"ERROR: Failed to delegate to {agent_type}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Add error to agent responses
                        if "agent_responses" not in internal_message:
                            internal_message["agent_responses"] = []
                        internal_message["agent_responses"].append({
                            "agent_type": agent_type,
                            "response": {
                                "success": False,
                                "error": str(e)
                            }
                        })

                # Handle message/respond - continue loop
                elif action_type in ["message", "respond"]:
                    # For now, just log and continue - could be enhanced to communicate with parent
                    print(f"BrowserBossAgent message: {action.get('message', '')}")
                    continue

                else:
                    # Unknown action type - continue
                    print(f"Unknown action type: {action_type}")
                    continue

            # Max iterations reached
            return {
                "success": False,
                "error": "Max iterations reached",
                "message": "Browser task did not complete within iteration limit",
                "iterations": iteration
            }

        except Exception as e:
            print(f"ERROR: BrowserBossAgent failed to process message: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": f"Error: {str(e)}"
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
                # Get BrowserActionAgent if it exists
                browser_action_agent = self.subagents.get("BrowserActionAgent")
                agent = XPathAgent(
                    websocket_callback=self.websocket_callback,
                    config_dict=self.config_dict,
                    browser_action_agent=browser_action_agent
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
