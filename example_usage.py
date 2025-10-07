#!/usr/bin/env python3
"""
Example usage of the Kyros AutoGLM agent.

This demonstrates how to use the standalone AutoGLM agent for desktop automation.
"""

import logging
import time
from typing import Dict

from autoglm import KyrosAgent


def mock_llm_function(messages):
    """
    Mock LLM function for testing. Replace this with your actual LLM call.

    Args:
        messages: List of message dictionaries in OpenAI format

    Returns:
        str: Generated response from the LLM
    """
    # This is a mock function - replace with actual LLM call
    # Example using OpenAI:
    # import openai
    # client = openai.OpenAI()
    # response = client.chat.completions.create(
    #     model="gpt-4-vision-preview",
    #     messages=messages,
    #     max_tokens=1000
    # )
    # return response.choices[0].message.content

    # For now, return a simple mock response
    return """<think>
I need to click on the desktop to start. Let me click at a safe location.
</think>
```python
Agent.click([960, 540])
```"""


def mock_get_observation() -> Dict:
    """
    Mock function to get desktop observation. Replace with actual implementation.

    Returns:
        Dict: Observation containing screenshot, accessibility tree, etc.
    """
    # This would normally capture the desktop state
    # You'll need to implement:
    # - Screenshot capture (using pyautogui, PIL, etc.)
    # - Accessibility tree capture (using AT-SPI on Linux)
    # - Current application detection

    return {
        "screenshot": b"",  # PNG bytes of screenshot
        "accessibility_tree": "",  # XML string of accessibility tree
        "apps": {},  # Dictionary of running applications
        "cur_window_id": "",  # Current active window ID
        "cur_app": "",  # Current application name
        "app_info": "",  # Application-specific information
        "exe_result": ""  # Result of last executed action
    }


def mock_execute_action(action):
    """
    Mock function to execute actions. Replace with actual implementation.

    Args:
        action: The action command to execute

    Returns:
        str: Result of the action execution
    """
    # This would normally execute the action using pyautogui or similar
    # For now, just return a mock result
    print(f"Executing action: {action}")
    time.sleep(0.5)  # Simulate action execution time
    return "Action executed successfully"


def main():
    """Main example function."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("kyros.example")

    # Create the agent
    agent = KyrosAgent(
        with_image=True,
        image_size=(1920, 1080),
        gen_func=mock_llm_function,
        client_password="password"
    )

    # Example task instruction
    instruction = "Open a text editor and type 'Hello World'"

    logger.info(f"Starting task: {instruction}")

    # Main interaction loop
    max_steps = 10
    for step in range(max_steps):
        logger.info(f"Step {step + 1}/{max_steps}")

        # Get current observation
        obs = mock_get_observation()

        # Generate next action
        response, actions = agent.predict(instruction, obs)

        if not actions:
            logger.error("No valid actions generated")
            break

        action = actions[0]
        # logger.info(f"Generated action: {action}")

        # Check for terminal actions
        if action in ["DONE", "FAIL"]:
            logger.info(f"Task completed with status: {action}")
            break
        elif action == "WAIT":
            logger.info("Waiting...")
            time.sleep(2)
            continue

        # Execute the action
        result = mock_execute_action(action)

        # Update observation with execution result
        obs["exe_result"] = result

        # Brief pause between actions
        time.sleep(1)

    logger.info("Example completed")


if __name__ == "__main__":
    main()