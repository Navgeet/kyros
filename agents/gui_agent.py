import base64
from typing import List, Dict, Any, Optional, Callable
from io import BytesIO
import subprocess
import os
import tempfile
import time
from PIL import Image, ImageDraw
from openai import OpenAI
from agents.base_agent import BaseAgent
import tools
from utils import compact_context, count_words, save_screenshot


class GUIAgent(BaseAgent):
    """GUI agent that handles mouse and keyboard actions"""

    def __init__(
        self,
        agent_id: str = None,
        api_key: str = None,
        base_url: str = None,
        websocket_callback: Optional[Callable] = None,
        config_dict: Dict[str, Any] = None
    ):
        # Store config_dict before calling parent init
        self.config_dict = config_dict

        super().__init__(
            agent_id=agent_id,
            api_key=api_key,
            base_url=base_url,
            websocket_callback=websocket_callback,
            agent_name="gui",
            config_dict=config_dict
        )
        self.running = False
        self.compacted_context: str = ""
        self.step_count: int = 0

        # Get screenshot delay from config (default 0.5 seconds)
        self.screenshot_delay = 0.5
        if self.config_dict and 'agents' in self.config_dict and 'gui' in self.config_dict['agents']:
            gui_config = self.config_dict['agents']['gui']
            self.screenshot_delay = gui_config.get('screenshot_delay', 0.5)

        # Setup action generation client (Hugging Face)
        self._setup_action_generation_client()

    def _setup_action_generation_client(self):
        """Setup the OpenAI client for action generation using Hugging Face"""
        # Initialize to None by default
        self.action_gen_client = None

        if self.config_dict and 'agents' in self.config_dict and 'gui' in self.config_dict['agents']:
            gui_config = self.config_dict['agents']['gui']
            if 'action_generation' in gui_config:
                action_gen_config = gui_config['action_generation']
                api_provider = action_gen_config.get('api_provider', 'huggingface')

                if api_provider == 'huggingface' or api_provider == 'novita':
                    hf_config = self.config_dict.get(api_provider, {})
                    api_key = hf_config.get('api_key')
                    base_url = hf_config.get('base_url')

                    self.action_gen_client = OpenAI(
                        base_url=base_url,
                        api_key=api_key
                    )
                    self.action_gen_model = action_gen_config.get('model')
                    self.action_gen_temperature = action_gen_config.get('temperature', 0.7)
                    self.action_gen_max_tokens = action_gen_config.get('max_tokens', 1000)

    def get_system_prompt(self) -> str:
        """Get the system prompt for the GUI agent"""
        return """
# Identity

You are a GUI Agent. Your job is to analyze the given screenshot and execute the given TASK by performing step-by-step actions.

# Tools

- tools.focus_window(window_id): Focus/activate a window by its ID and move mouse to center
- tools.move(x, y): Move mouse to relative coordinates (x and y are floats between 0 and 1).
- tools.click(x, y, button=1, clicks=1): Click at relative coordinates (x and y are floats between 0 and 1). button: 1=left, 2=middle, 3=right. clicks: 1=single, 2=double, etc.
- tools.scroll(amount): Scroll at current mouse position. amount: positive=down, negative=up.
- tools.type(text): Type the given text
- tools.hotkey(keys): Press a hotkey combination (e.g., 'super+r', 'ctrl+c')
- tools.wait(n): Wait for n seconds.
- tools.exit(message, exitCode): Exit the agent when finished (exitCode 0 for success, -1 for error)

# Rules

- Respond with executable Python code that calls ONE of these tools
- Only generate 1 action at a time. Also add a comment before every action
- Don't repeat the same action again and again
- Look at the "Currently active windows" list (format: window_id desktop host window_title) to determine which window to focus
- The mouse cursor looks like a red dot
- Analyze the screenshot carefully, don't make up GUI elements

# Example

```python
# Focus the Firefox browser window with ID 0x02400003
tools.focus_window("0x02400003")
```

```python
# Click on the search box
tools.click(0.5, 0.3)
```
"""

    def get_screenshot_base64(self) -> str:
        """Capture screenshot and return as base64-encoded JPEG with cursor drawn"""
        # Create temp file and close it immediately so import can write to it
        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)  # Close the file descriptor immediately

        # Remove the empty file that mkstemp created
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        try:
            # Set up environment
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            # Capture screenshot with import
            result = subprocess.run(
                ["import", "-window", "root", temp_path],
                capture_output=True,
                timeout=2,
                env=env
            )

            if result.returncode != 0:
                raise RuntimeError(f"import failed with code {result.returncode}: {result.stderr.decode()}")

            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError(f"import did not create screenshot file at {temp_path}")

            # Get cursor position using Python Xlib
            cursor_x, cursor_y = None, None
            try:
                import Xlib.display
                display = Xlib.display.Display(env.get('DISPLAY', ':0'))
                root = display.screen().root
                pointer = root.query_pointer()
                cursor_x = pointer.root_x
                cursor_y = pointer.root_y
                display.close()
            except Exception as e:
                # If Xlib fails, don't draw cursor
                pass

            # Load screenshot and draw cursor
            screenshot = Image.open(temp_path)

            # Only draw cursor if we successfully got the position
            if cursor_x is not None and cursor_y is not None:
                draw = ImageDraw.Draw(screenshot)
                # Draw a simple cursor (red circle with white outline)
                cursor_size = 10
                draw.ellipse(
                    [cursor_x - cursor_size, cursor_y - cursor_size,
                     cursor_x + cursor_size, cursor_y + cursor_size],
                    fill='red',
                    outline='white',
                    width=2
                )

            # Convert to JPEG
            buffer = BytesIO()
            screenshot.save(buffer, format="JPEG", quality=75)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_active_windows(self) -> str:
        """Get list of active windows"""
        try:
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.stdout if result.returncode == 0 else "N/A"
        except:
            return "N/A"

    def execute_action(self, action_code: str) -> dict:
        """Execute the generated Python code"""
        # Extract the actual Python code
        code = action_code
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        # Execute the code and capture the result
        result = {"stdout": "", "stderr": "", "exitCode": 0}

        try:
            # Create a namespace with tools available and a result holder
            namespace = {"tools": tools, "__action_result__": None}

            # Parse the code to extract the tool call and capture its result
            lines = code.split('\n')
            modified_lines = []

            for line in lines:
                stripped = line.strip()
                # If this is a tools call (not exit and not a comment), capture its result
                if stripped.startswith('tools.') and not stripped.startswith('tools.exit('):
                    # Calculate indentation
                    indent = len(line) - len(line.lstrip())
                    modified_lines.append(' ' * indent + f'__action_result__ = {stripped}')
                else:
                    modified_lines.append(line)

            modified_code = '\n'.join(modified_lines)

            # Execute the modified code
            exec(modified_code, namespace)

            # Extract result if available
            if namespace.get("__action_result__") is not None:
                tool_result = namespace["__action_result__"]
                if isinstance(tool_result, dict):
                    result["stdout"] = tool_result.get("stdout", "")
                    result["stderr"] = tool_result.get("stderr", "")
                    result["exitCode"] = tool_result.get("exitCode", 0)

        except tools.ExitException as e:
            # Handle exit
            self.running = False
            result["stdout"] = e.message
            result["exitCode"] = e.exit_code
        except Exception as e:
            result["stderr"] = str(e)
            result["exitCode"] = -1

        return result

    def generate_action(self, messages: List[Dict[str, Any]], system: str) -> str:
        """Generate action using Hugging Face client or fallback to regular LLM"""
        if self.action_gen_client:
            try:
                # Prepare messages
                llm_messages = messages.copy()
                if system:
                    llm_messages.insert(0, {"role": "system", "content": system})

                # Log input
                self._log_llm_call({
                    "event": "input",
                    "model": self.action_gen_model,
                    "temperature": self.action_gen_temperature,
                    "max_tokens": self.action_gen_max_tokens,
                    "messages": self._elide_image_data(llm_messages)
                })

                # Send start event with elided image data
                self.send_llm_update("llm_call_start", {
                    "messages": self._elide_image_data(llm_messages),
                    "model": self.action_gen_model,
                    "temperature": self.action_gen_temperature,
                    "max_tokens": self.action_gen_max_tokens
                })

                response_text = ""

                # Use Hugging Face router with streaming
                response = self.action_gen_client.chat.completions.create(
                    model=self.action_gen_model,
                    messages=llm_messages,
                    temperature=self.action_gen_temperature,
                    max_tokens=self.action_gen_max_tokens,
                    stream=True
                )

                reasoning_text = ""

                for chunk in response:
                    # Skip empty chunks
                    if not chunk.choices:
                        continue

                    # Handle reasoning content
                    if hasattr(chunk.choices[0].delta, 'model_extra') and chunk.choices[0].delta.model_extra:
                        reasoning_content = chunk.choices[0].delta.model_extra.get('reasoning_content')
                        if reasoning_content:
                            reasoning_text += reasoning_content
                            self.send_llm_update("llm_reasoning_chunk", {
                                "content": reasoning_content
                            })

                    # Handle regular content
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        self.send_llm_update("llm_content_chunk", {
                            "content": content
                        })

                # Log output
                self._log_llm_call({
                    "event": "output",
                    "response": response_text,
                    "reasoning": reasoning_text
                })

                # Send end event
                self.send_llm_update("llm_call_end", {
                    "response": response_text,
                    "reasoning": reasoning_text
                })

                return response_text
            except Exception as e:
                print(f"Error using Hugging Face for action generation: {e}")
                # Fallback to regular LLM
                return self.call_llm(messages=messages, system=system)
        else:
            # Use regular LLM
            return self.call_llm(messages=messages, system=system)

    def verify_action(self, screenshot_before: str, screenshot_after: str, action: str) -> str:
        """Verify if action succeeded by comparing screenshots"""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Action performed: {action}\n\nDid the action succeed? Provide a brief analysis.\n\nScreenshot before:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": screenshot_before
                        }
                    },
                    {
                        "type": "text",
                        "text": "Screenshot after:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": screenshot_after
                        }
                    }
                ]
            }
        ]

        verification = self.call_llm(
            messages=messages,
            system="You are a verification assistant. Compare two screenshots (before and after an action) and determine if the action succeeded. Be concise.",
            max_tokens=500
        )

        return verification

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and execute GUI actions in a loop"""
        task = message.get("content", "")
        self.running = True
        max_iterations = message.get("max_iterations", 20)
        iteration = 0
        history = []

        while self.running and iteration < max_iterations:
            iteration += 1
            self.step_count += 1

            # Get compaction config
            compaction_config = self.config_dict.get('compaction', {}) if self.config_dict else {}
            trigger_steps = compaction_config.get('trigger', {}).get('steps', 5)
            trigger_words = compaction_config.get('trigger', {}).get('words', 1000)

            # Check if compaction is needed
            context_text = str(history)
            word_count = count_words(context_text)

            if self.step_count >= trigger_steps or word_count >= trigger_words:
                # Compact the context
                self.compacted_context = compact_context(
                    history,
                    task,
                    self.config_dict,
                    self.websocket_callback,
                    self.agent_id,
                    self.agent_name
                )
                # Clear history after compaction
                history = []
                self.step_count = 0

            # Get current screenshot
            screenshot = self.get_screenshot_base64()
            active_windows = self.get_active_windows()

            # Save screenshot to disk
            save_screenshot(screenshot, prefix="gui")

            # Send screenshot update
            self.send_llm_update("screenshot", {
                "screenshot": screenshot,
                "active_windows": active_windows
            })

            # Build context for LLM
            text_parts = [f"# Task\n\n{task}"]

            if self.compacted_context:
                text_parts.append(f"\n# Previous Actions (compacted)\n{self.compacted_context}")

            if history:
                text_parts.append("\n# Previous Actions")
                for i, item in enumerate(history, 1):
                    text_parts.append(f"\n{i}. Action: {item['action']}")
                    if item.get('verification'):
                        text_parts.append(f"   Verification: {item['verification']}")

            text_parts.append(f"\n# Context\nPlatform: Linux\nCurrently active windows:\n```\n{active_windows}\n```\nScreenshot: refer to the image")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "\n".join(text_parts)
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

            # Generate action using Hugging Face (or fallback to regular LLM)
            action_code = self.generate_action(
                messages=messages,
                system=self.get_system_prompt()
            )

            # Extract Python code from markdown code blocks if present
            if "```python" in action_code:
                action_code = action_code.split("```python")[1].split("```")[0].strip()
            elif "```" in action_code:
                action_code = action_code.split("```")[1].split("```")[0].strip()

            # Check if this is an exit action
            is_exit_action = "tools.exit" in action_code

            # Capture screenshot before action
            screenshot_before = screenshot if not is_exit_action else None

            # Send action update
            self.send_llm_update("action_execute", {
                "action": action_code,
                "iteration": iteration
            })

            # Execute action
            exec_result = self.execute_action(action_code)

            # Log tool execution result
            print(f"Tool execution result: {exec_result}")
            if exec_result.get("stderr"):
                print(f"Tool stderr: {exec_result['stderr']}")
            if exec_result.get("exitCode") != 0:
                print(f"Tool failed with exit code: {exec_result['exitCode']}")

            # Send execution result
            self.send_llm_update("action_result", {
                "result": exec_result
            })

            if is_exit_action or not self.running:
                # Exit action - no verification needed
                history.append({
                    "action": action_code,
                    "result": exec_result,
                    "verification": None
                })
                break

            # Add delay before taking screenshot to allow UI to update
            # Skip delay if the action was already a wait command
            if not "tools.wait" in action_code:
                time.sleep(self.screenshot_delay)

            # Capture screenshot after action
            screenshot_after = self.get_screenshot_base64()

            # Verify action
            verification = self.verify_action(screenshot_before, screenshot_after, action_code)

            # Send verification update
            self.send_llm_update("action_verification", {
                "verification": verification
            })

            # Add to history
            history.append({
                "action": action_code,
                "result": exec_result,
                "verification": verification
            })

        return {
            "success": True,
            "iterations": iteration,
            "history": history
        }
