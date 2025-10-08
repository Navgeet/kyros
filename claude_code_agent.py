#!/usr/bin/env python3
"""
Claude Code Agent - Uses Claude Code in background to generate Python code for computer use tasks.

This agent:
1. Takes screenshots and supplies them to Claude Code
2. Uses Claude Code to generate executable Python code plans
3. Executes the generated code
4. Reviews execution results with Claude Code
5. Provides a web interface for user interaction
"""

import os
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import pyautogui
from tools import Tools


class ClaudeCodeAgent:
    """Agent that uses Claude Code for computer use task planning and execution."""

    def __init__(self, claude_code_path: str = "claude"):
        """
        Initialize the Claude Code agent.

        Args:
            claude_code_path: Path to the Claude Code CLI executable
        """
        self.claude_code_path = claude_code_path
        self.screenshots_dir = Path.cwd() / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        self.session_id = str(uuid.uuid4())[:8]
        self.conversation_history = []
        self.tools = Tools()
        self.claude_process = None
        self._start_claude_session()

        # Verify Claude Code is available
        if not self._check_claude_code_available():
            raise RuntimeError("Claude Code CLI not found. Please install it first.")

    def _start_claude_session(self):
        """Start an interactive Claude Code session."""
        try:
            print(f"🚀 Starting interactive Claude Code session...")

            # Start Claude Code in interactive mode
            self.claude_process = subprocess.Popen(
                [self.claude_code_path, "--print"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            print(f"✅ Claude Code session started successfully")

        except Exception as e:
            print(f"❌ Failed to start Claude Code session: {e}")
            self.claude_process = None
            raise

    def _send_to_claude(self, message: str) -> str:
        """Send a message to Claude Code and get response."""
        if not self.claude_process:
            raise RuntimeError("Claude Code session not started")

        try:
            # Send message
            print(f"📤 Sending to Claude: {message[:100]}...")
            self.claude_process.stdin.write(message + "\n")
            self.claude_process.stdin.flush()

            # Read response - simplified approach
            response_lines = []
            timeout_counter = 0
            max_timeout = 60  # 60 iterations of 0.5s = 30s timeout

            while timeout_counter < max_timeout:
                try:
                    # Try to read a line with timeout
                    import fcntl
                    import os

                    # Set non-blocking
                    fd = self.claude_process.stdout.fileno()
                    flag = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

                    line = self.claude_process.stdout.readline()
                    if line:
                        line = line.rstrip()
                        response_lines.append(line)
                        print(f"📥 Claude line: {line}")

                        # Check if we have a complete response (ends with closing ```)
                        if line.strip() == "```" and len(response_lines) > 1:
                            break
                    else:
                        import time
                        time.sleep(0.5)
                        timeout_counter += 1

                except IOError:
                    # No data available
                    import time
                    time.sleep(0.5)
                    timeout_counter += 1

            response = "\n".join(response_lines)
            print(f"📥 Claude response ({len(response_lines)} lines): {response[:300]}...")
            return response

        except Exception as e:
            print(f"❌ Error communicating with Claude: {e}")
            return ""

    def _cleanup_claude_session(self):
        """Clean up the Claude Code session."""
        if self.claude_process:
            try:
                self.claude_process.terminate()
                self.claude_process.wait(timeout=5)
            except:
                self.claude_process.kill()
            self.claude_process = None

    def __del__(self):
        """Cleanup when agent is destroyed."""
        self._cleanup_claude_session()

    def _check_claude_code_available(self) -> bool:
        """Check if Claude Code CLI is available."""
        try:
            result = subprocess.run(
                [self.claude_code_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def take_screenshot(self, name: Optional[str] = None) -> str:
        """
        Take a screenshot and save it to screenshots directory.

        Args:
            name: Optional name for the screenshot. If None, generates timestamp-based name.

        Returns:
            Filename of the saved screenshot
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{self.session_id}_{timestamp}"

        # Ensure we have a clean filename
        name = name.replace(" ", "_").replace(":", "_")

        screenshot_path = self.screenshots_dir / f"{name}.png"

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(screenshot_path))
            print(f"📸 Screenshot saved: {screenshot_path}")
            return f"{name}.png"
        except Exception as e:
            print(f"❌ Failed to take screenshot: {e}")
            raise

    def generate_plan_with_claude_code(self, user_request: str, screenshot_filename: str) -> Dict:
        """
        Use Claude Code to generate a Python code plan for the user request.

        Args:
            user_request: The user's task request
            screenshot_filename: Filename of the current screenshot

        Returns:
            Dictionary containing the generated plan and metadata
        """
        screenshot_path = self.screenshots_dir / screenshot_filename

        # Create a prompt for Claude Code
        claude_prompt = f"""
TASK: Generate executable Python code for: {user_request}

You must respond with ONLY executable Python code wrapped in ```python code blocks. Do not include explanations or descriptions.
First you must call the 

The code should use the tools module with this exact pattern:

```python
import tools

def main_task():
    # Your code here using tools.function_name()
    tools.screenshot("completion")

main_task()
```

Available tools:
- tools.focus_window(name): Focus window by name
- tools.hotkey(keys): Send keyboard shortcuts
- tools.type(text): Type text
- tools.click(x, y): Click at coordinates. Use RELATIVE coordinates (0.0-1.0). Obtain using query_screen.py
- tools.move_to(x, y): Move mouse to coordinates Use RELATIVE coordinates (0.0-1.0). Obtain using query_screen.py
- tools.run_shell_command(args): Run commands
- tools.screenshot(name): Take screenshot

PRECISE CLICKING:
To get accurate coordinates for UI elements, use the query_screen.py script:

Example: python3 query_screen.py "Find the submit button, return relative coordinates (0-1). No explanation text needed." 
Returns: 0.75,0.85
Example: python3 query_screen.py "Describe the image. Be concise." 

IMPORTANT:
- First describe the screen and check, then proceed with code generation.
- Respond with ONLY Python code in ```python blocks
- No explanations, just executable code
- Use the query_image.py script for precise clicking, don't 
- Always end with tools.screenshot("completion")

Task: {user_request}
"""

        try:
            # Include screenshot path in the prompt
            full_prompt = f"Please read the screenshot at {screenshot_path} and then: {claude_prompt}"

            print(f"🤖 Using interactive Claude Code session...")
            print(f"📝 Prompt: {full_prompt[:200]}...")

            # Send to interactive Claude session
            response = self._send_to_claude(full_prompt)

            # Extract Python code from the response
            code = self._extract_python_code(response)
            print(f"🐍 Extracted Python code: {code[:200]}...")

            return {
                "type": "python_code",
                "code": code,
                "full_response": response,
                "timestamp": datetime.now().isoformat(),
                "screenshot": screenshot_filename
            }

        except Exception as e:
            print(f"❌ Error generating plan with Claude Code: {e}")
            raise

    def _extract_python_code(self, response: str) -> str:
        """Extract Python code from Claude Code response."""
        lines = response.split('\n')
        in_code_block = False
        code_lines = []

        for line in lines:
            if line.strip().startswith('```python'):
                in_code_block = True
                continue
            elif line.strip() == '```' and in_code_block:
                break
            elif in_code_block:
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines)
        else:
            # If no code blocks found, look for lines that seem like Python code
            # This is a fallback for cases where Claude Code doesn't use markdown
            potential_code = []
            for line in lines:
                stripped = line.strip()
                if (stripped.startswith('import ') or
                    stripped.startswith('def ') or
                    stripped.startswith('tools.') or
                    stripped.startswith('    ') or  # Indented lines
                    stripped.endswith(':')):
                    potential_code.append(line)

            if potential_code:
                return '\n'.join(potential_code)
            else:
                # If no Python code found, generate a simple screenshot task
                print("⚠️  No Python code detected in response, generating fallback code")
                return """import kyros.tools

def take_screenshot():
    tools.screenshot("task_completion")
    print("Task completed - screenshot taken")

take_screenshot()"""

    def execute_generated_code(self, plan: Dict) -> Tuple[bool, str, str]:
        """
        Execute the generated Python code plan.

        Args:
            plan: Plan dictionary containing the code to execute

        Returns:
            Tuple of (success, stdout, stderr)
        """
        code = plan.get("code", "")

        if not code:
            return False, "", "No code to execute"

        try:
            print("🐍 Executing generated Python code...")
            print(f"Code:\n{code}\n")

            # Create execution namespace with access to tools
            import sys
            import os
            import types

            # Create a proper kyros module and tools submodule
            kyros_module = types.ModuleType('kyros')
            tools_module = types.ModuleType('kyros.tools')

            # Add all tool methods to the tools module
            for attr_name in dir(self.tools):
                if not attr_name.startswith('_'):
                    setattr(tools_module, attr_name, getattr(self.tools, attr_name))

            # Set up the module hierarchy
            kyros_module.tools = tools_module
            sys.modules['kyros'] = kyros_module
            sys.modules['kyros.tools'] = tools_module

            # Create execution namespace
            exec_namespace = {
                'kyros': kyros_module,
                'tools': self.tools,
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'time': __import__('time'),
                    '__import__': __import__,  # Allow imports
                    '__name__': '__main__',
                    '__file__': '<executed_code>',
                }
            }

            # Capture stdout for execution feedback
            import io
            import sys

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                # Execute the code
                exec(code, exec_namespace)

                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr

                stdout_content = stdout_capture.getvalue()
                stderr_content = stderr_capture.getvalue()

                print("✅ Code executed successfully")
                if stdout_content:
                    print(f"Output: {stdout_content}")

                return True, stdout_content, stderr_content

            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        except Exception as e:
            print(f"❌ Error executing code: {e}")
            return False, "", str(e)

    def review_execution_with_claude_code(self,
                                        plan: Dict,
                                        execution_result: Tuple[bool, str, str],
                                        post_screenshot_filename: str) -> str:
        """
        Ask Claude Code to review the execution results.

        Args:
            plan: The original plan that was executed
            execution_result: Tuple of (success, stdout, stderr)
            post_screenshot_filename: Screenshot taken after execution

        Returns:
            Claude Code's assessment of the execution
        """
        success, stdout, stderr = execution_result
        post_screenshot_path = self.screenshots_dir / post_screenshot_filename

        review_prompt = f"""
Please review the execution of this computer use task:

**Original Task:** (from the plan context)

**Generated Code:**
```python
{plan.get('code', 'No code available')}
```

**Execution Results:**
- Success: {success}
- Output: {stdout if stdout else 'No output'}
- Errors: {stderr if stderr else 'No errors'}

**Post-execution Screenshot:** I'm providing a screenshot taken after the code was executed.

Please analyze:
1. Did the task appear to complete successfully?
2. Are there any visible changes in the UI that indicate progress?
3. Are there any error conditions visible on screen?
4. What should be the next steps (if any)?

Provide a clear assessment of whether the task was completed successfully and any recommendations for improvement.
"""

        try:
            # Call Claude Code to review the screenshot
            cmd = [
                self.claude_code_path,
                "--print"
            ]

            # Include screenshot path in the prompt
            full_review_prompt = f"Please read the screenshot at {post_screenshot_path} and then: {review_prompt}"

            print(f"🔍 Asking Claude Code to review execution...")
            result = subprocess.run(
                cmd,
                input=full_review_prompt,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return f"Failed to get review: {result.stderr}"

            return result.stdout.strip()

        except Exception as e:
            return f"Error during review: {e}"

    def process_user_request(self, user_request: str) -> Dict:
        """
        Process a user request end-to-end.

        Args:
            user_request: The user's task request

        Returns:
            Dictionary containing the complete execution results
        """
        session_start = datetime.now()

        try:
            # Step 1: Take initial screenshot
            initial_screenshot = self.take_screenshot("before_execution")

            # Step 2: Generate plan with Claude Code
            plan = self.generate_plan_with_claude_code(user_request, initial_screenshot)

            # Step 3: Execute the generated code
            execution_result = self.execute_generated_code(plan)

            # Step 4: Take post-execution screenshot
            time.sleep(1)  # Brief pause to let UI settle
            post_screenshot = self.take_screenshot("after_execution")

            # Step 5: Review execution with Claude Code
            review = self.review_execution_with_claude_code(plan, execution_result, post_screenshot)

            # Compile results
            result = {
                "session_id": self.session_id,
                "user_request": user_request,
                "timestamp": session_start.isoformat(),
                "initial_screenshot": initial_screenshot,
                "post_screenshot": post_screenshot,
                "plan": plan,
                "execution": {
                    "success": execution_result[0],
                    "stdout": execution_result[1],
                    "stderr": execution_result[2]
                },
                "review": review,
                "duration": (datetime.now() - session_start).total_seconds()
            }

            # Add to conversation history
            self.conversation_history.append(result)

            return result

        except Exception as e:
            error_result = {
                "session_id": self.session_id,
                "user_request": user_request,
                "timestamp": session_start.isoformat(),
                "error": str(e),
                "duration": (datetime.now() - session_start).total_seconds()
            }

            self.conversation_history.append(error_result)
            return error_result


if __name__ == "__main__":
    # Example usage
    agent = ClaudeCodeAgent()

    # Example request
    request = "search google for restaurants near me"
    result = agent.process_user_request(request)

    print("\n" + "="*50)
    print("EXECUTION SUMMARY")
    print("="*50)
    print(f"Request: {result['user_request']}")
    print(f"Success: {result.get('execution', {}).get('success', False)}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Review: {result.get('review', 'No review available')}")