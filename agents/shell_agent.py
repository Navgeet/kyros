import subprocess
import uuid
import json
from typing import List, Dict, Any, Optional, Callable
from agents.base_agent import BaseAgent
from utils import strip_json_code_blocks, compact_context, count_words


class ShellAgent(BaseAgent):
    """Shell agent that creates a shell session and executes commands"""

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
            agent_name="shell",
            config_dict=config_dict
        )
        self.session_id = str(uuid.uuid4())
        self.history: List[Dict[str, Any]] = []
        self.working_directory = None
        self.config_dict = config_dict
        self.compacted_context: str = ""
        self.step_count: int = 0

    def get_system_prompt(self) -> str:
        """Get the system prompt for the shell agent"""
        return """# Identity

You are an agent generating shell commands to accomplish the given task in a step-by-step manner.

# Rules

- Respond with a JSON object containing your thought process and the command to execute
- Gather more information about your environment using shell commands
- Consider the current working directory and command history
- If a task is complete, return an empty command

# Response Format

```json
{
  "thought": "Your reasoning about what to do next",
  "command": "the shell command to execute"
}
```

When the task is complete, respond with:
```json
{
  "command": "",
}
```
"""

    def execute_command(self, cmd: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command and return the result"""
        try:
            # Execute command with working directory if set
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_directory
            )

            # Update working directory if this was a cd command
            if cmd.strip().startswith("cd "):
                if result.returncode == 0:
                    # Get the new working directory
                    pwd_result = subprocess.run(
                        f"{cmd} && pwd",
                        shell=True,
                        capture_output=True,
                        text=True,
                        cwd=self.working_directory
                    )
                    if pwd_result.returncode == 0:
                        self.working_directory = pwd_result.stdout.strip()

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exitCode": result.returncode,
                "cwd": self.working_directory
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "exitCode": -1,
                "cwd": self.working_directory
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exitCode": -1,
                "cwd": self.working_directory
            }

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and execute shell commands"""
        try:
            task = message.get("content", "")
            max_iterations = message.get("max_iterations", 20)
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                self.step_count += 1

                try:
                    # Get compaction config
                    compaction_config = self.config_dict.get('compaction', {}) if self.config_dict else {}
                    trigger_steps = compaction_config.get('trigger', {}).get('steps', 5)
                    trigger_words = compaction_config.get('trigger', {}).get('words', 1000)

                    # Check if compaction is needed
                    context_text = str(self.history)
                    word_count = count_words(context_text)

                    if self.step_count >= trigger_steps or word_count >= trigger_words:
                        # Compact the context
                        self.compacted_context = compact_context(
                            self.history,
                            task,
                            self.config_dict,
                            self.websocket_callback,
                            self.agent_id,
                            self.agent_name
                        )
                        # Clear history after compaction
                        self.history = []
                        self.step_count = 0

                    # Build context for LLM
                    context_parts = [f"# Task\n\n{task}"]

                    if self.compacted_context:
                        context_parts.append(f"\n# Previous Actions (compacted)\n{self.compacted_context}")

                    if self.working_directory:
                        context_parts.append(f"\n# Current Working Directory\n{self.working_directory}")

                    if self.history:
                        context_parts.append("\n# Command History")
                        for i, item in enumerate(self.history[-10:], 1):  # Show last 10 commands
                            context_parts.append(f"\n{i}. Command: {item['command']}")
                            context_parts.append(f"   Exit Code: {item['result']['exitCode']}")
                            if item['result']['stdout']:
                                context_parts.append(f"   Stdout: {item['result']['stdout'][:200]}")
                            if item['result']['stderr']:
                                context_parts.append(f"   Stderr: {item['result']['stderr'][:200]}")

                    messages = [
                        {
                            "role": "user",
                            "content": "\n".join(context_parts)
                        }
                    ]

                    # Generate next action
                    response = self.call_llm(
                        messages=messages,
                        system=self.get_system_prompt()
                    )

                    # Parse response
                    try:
                        cleaned_response = strip_json_code_blocks(response)
                        response_data = json.loads(cleaned_response)
                    except json.JSONDecodeError:
                        # If not valid JSON, treat as error
                        print(f"ERROR: ShellAgent received invalid JSON response: {response}")
                        return {
                            "success": False,
                            "error": "Invalid response format",
                            "iterations": iteration,
                            "history": self.history
                        }

                    # Send thought update
                    self.send_llm_update("thought", {
                        "thought": response_data.get("thought", ""),
                        "iteration": iteration
                    })

                    # Check if done
                    if response_data.get("done", False):
                        return {
                            "success": True,
                            "result": response_data.get("result", "Task completed"),
                            "iterations": iteration,
                            "history": self.history
                        }

                    # Execute command
                    command = response_data.get("command")
                    if not command:
                        return {
                            "success": False,
                            "error": "No command provided",
                            "iterations": iteration,
                            "history": self.history
                        }

                    # Send command execute update
                    self.send_llm_update("command_execute", {
                        "command": command,
                        "iteration": iteration
                    })

                    # Execute command
                    exec_result = self.execute_command(command)

                    # Send execution result
                    self.send_llm_update("command_result", {
                        "result": exec_result
                    })

                    # Add to history
                    self.history.append({
                        "command": command,
                        "result": exec_result,
                        "thought": response_data.get("thought", "")
                    })

                except Exception as e:
                    print(f"ERROR: ShellAgent iteration {iteration} failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "success": False,
                        "error": f"Error in iteration {iteration}: {str(e)}",
                        "iterations": iteration,
                        "history": self.history
                    }

            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": iteration,
                "history": self.history
            }

        except Exception as e:
            print(f"ERROR: ShellAgent failed to process message: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "iterations": 0,
                "history": self.history
            }
