#!/usr/bin/env python3
"""
Simple test of the agent that doesn't rely on Claude Code working perfectly.
This creates a mock version to test the web interface.
"""

from claude_code_agent import ClaudeCodeAgent
from typing import Dict, Tuple
import time


class MockClaudeCodeAgent(ClaudeCodeAgent):
    """Mock agent for testing without Claude Code dependency."""

    def generate_plan_with_claude_code(self, user_request: str, screenshot_filename: str) -> Dict:
        """Generate a mock plan for testing."""
        print(f"🤖 Generating mock plan for: {user_request}")

        # Generate simple Python code based on the request
        if "screenshot" in user_request.lower():
            code = """import kyros.tools

def take_screenshot():
    tools.screenshot("task_completion")
    print("Screenshot taken successfully")

take_screenshot()"""
        elif "search" in user_request.lower() and "google" in user_request.lower():
            code = """import kyros.tools

def search_google():
    tools.focus_window("chrome")
    tools.hotkey("ctrl+t")
    tools.type("restaurants near me")
    tools.hotkey("enter")
    tools.screenshot("search_completion")

search_google()"""
        elif "tab" in user_request.lower():
            code = """import kyros.tools

def open_new_tab():
    tools.focus_window("chrome")
    tools.hotkey("ctrl+t")
    tools.screenshot("tab_opened")

open_new_tab()"""
        else:
            code = f"""import kyros.tools

def execute_task():
    # Task: {user_request}
    print("Executing task: {user_request}")
    tools.screenshot("task_completion")

execute_task()"""

        return {
            "type": "python_code",
            "code": code,
            "full_response": f"Generated code for: {user_request}",
            "timestamp": time.time(),
            "screenshot": screenshot_filename
        }

    def review_execution_with_claude_code(self, plan: Dict, execution_result: Tuple[bool, str, str], post_screenshot_filename: str) -> str:
        """Generate a mock review."""
        success, stdout, stderr = execution_result

        if success:
            return f"""✅ Task execution completed successfully!

**Analysis:**
- The generated code executed without errors
- Output: {stdout if stdout else 'Task completed silently'}
- Screenshots captured for verification

**Assessment:**
The task appears to have been completed successfully. The code executed the intended actions and captured a screenshot for verification.

**Recommendations:**
- Task completed as requested
- No further action needed"""
        else:
            return f"""❌ Task execution encountered issues.

**Problems Detected:**
- Execution failed with error: {stderr if stderr else 'Unknown error'}
- Output: {stdout if stdout else 'No output'}

**Recommendations:**
- Check if the required applications are running
- Verify screen is accessible
- Consider simplifying the task or trying again"""


def test_mock_agent():
    """Test the mock agent functionality."""
    print("🧪 Testing Mock Claude Code Agent")
    print("=" * 40)

    agent = MockClaudeCodeAgent()

    test_requests = [
        "take a screenshot",
        "search google for restaurants near me",
        "open a new browser tab"
    ]

    for request in test_requests:
        print(f"\n📝 Testing: {request}")
        result = agent.process_user_request(request)

        print(f"   Success: {result.get('execution', {}).get('success', False)}")
        print(f"   Duration: {result.get('duration', 0):.2f}s")

        if result.get('review'):
            print(f"   Review: {result['review'][:100]}...")

    print(f"\n✅ Mock agent test completed!")
    return agent


if __name__ == "__main__":
    test_mock_agent()