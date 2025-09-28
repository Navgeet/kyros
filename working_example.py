#!/usr/bin/env python3
"""
Working example of the Kyros AutoGLM agent with real implementations.

This demonstrates how to use the Kyros agent with:
- InternLM API for LLM calls
- Real desktop observation functions
- Action execution system
"""

import logging
import time
import os
import sys
from typing import Dict

from autoglm import KyrosAgent
from llm_integration import create_internlm_function
from desktop_observation import get_desktop_observation, check_dependencies
from action_execution import ActionExecutor, check_automation_dependencies


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("kyros.main")


def check_all_dependencies():
    """Check all required dependencies."""
    print("🔍 Checking dependencies...")

    # Check observation dependencies
    obs_missing = check_dependencies()
    if obs_missing:
        print("❌ Missing observation dependencies:")
        for dep in obs_missing:
            print(f"  - {dep}")

    # Check automation dependencies
    auto_missing = check_automation_dependencies()
    if auto_missing:
        print("❌ Missing automation dependencies:")
        for dep in auto_missing:
            print(f"  - {dep}")

    all_missing = obs_missing + auto_missing
    if all_missing:
        print(f"\n❌ Please install {len(all_missing)} missing dependencies before running.")
        return False
    else:
        print("✅ All dependencies available")
        return True


def main():
    """Main function demonstrating the working Kyros agent."""
    logger = setup_logging()

    print("🤖 Kyros AutoGLM Agent - Working Example")
    print("=" * 50)

    # Check dependencies
    if not check_all_dependencies():
        print("\n⚠️  Some dependencies are missing, but continuing anyway...")
        print("Note: Some features (like accessibility tree) may not work properly.")

    # Configure InternLM API
    api_url = os.getenv("INTERNLM_API_URL", "http://localhost:23333")
    api_key = os.getenv("INTERNLM_API_KEY")

    if not api_key:
        print("⚠️  Warning: INTERNLM_API_KEY not set. API calls may fail if authentication is required.")

    print(f"🌐 Using InternLM API at: {api_url}")

    # Create LLM function
    llm_function = create_internlm_function(
        api_url=api_url,
        api_key=api_key,
        model="internvl3.5-241b-a28b"
    )

    # Create the agent
    logger.info("Creating Kyros agent...")
    agent = KyrosAgent(
        with_image=True,
        with_atree=True,  # Enable accessibility tree
        image_size=(1920, 1080),
        gen_func=llm_function,
        client_password="password",
        a11y_tree_max_items=300
    )

    # Create action executor
    executor = ActionExecutor(screen_size=(1920, 1080))

    # Get task from user or use default
    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
    else:
        # Example tasks - you can modify these
        example_tasks = [
            "Take a screenshot and save it",
            "Open a text editor and type 'Hello from Kyros!'",
            "Click on the desktop and then wait 2 seconds",
            "Open a terminal window",
            "Show me what applications are currently running"
        ]

        print("\n📝 Example tasks:")
        for i, task in enumerate(example_tasks, 1):
            print(f"  {i}. {task}")

        try:
            choice = input(f"\nSelect a task (1-{len(example_tasks)}) or type your own: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(example_tasks):
                instruction = example_tasks[int(choice) - 1]
            else:
                instruction = choice
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)

    print(f"\n🎯 Task: {instruction}")
    logger.info(f"Starting task: {instruction}")

    # Main interaction loop
    max_steps = 10
    for step in range(max_steps):
        print(f"\n{'='*20} Step {step + 1}/{max_steps} {'='*20}")
        logger.info(f"Step {step + 1}/{max_steps}")

        try:
            # Get current observation
            print("📸 Capturing desktop observation...")
            obs = get_desktop_observation()

            # Add previous execution result if available
            if hasattr(executor, 'last_result') and executor.last_result:
                obs["exe_result"] = executor.last_result

            print(f"📊 Observation: Screenshot={len(obs['screenshot'])} bytes, "
                  f"Apps={len(obs['apps'])}, Current={obs['cur_app']}")

            # Generate next action
            print("🧠 Generating action with LLM...")
            response, actions = agent.predict(instruction, obs)

            if not actions:
                logger.error("No valid actions generated")
                print("❌ No valid actions generated. Stopping.")
                break

            action = actions[0]
            print(f"🎬 Action: {action}")
            logger.info(f"Generated action: {action}")

            # Check for terminal actions
            if action in ["DONE", "FAIL"]:
                print(f"🏁 Task completed with status: {action}")
                logger.info(f"Task completed with status: {action}")
                break
            elif action == "WAIT":
                print("⏸️  Waiting...")
                logger.info("Waiting...")
                time.sleep(2)
                continue

            # Execute the action
            print("⚡ Executing action...")
            result = executor.execute_action(action)
            print(f"📋 Result: {result}")

            # Brief pause between actions
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by user")
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in step {step + 1}: {e}")
            print(f"❌ Error: {e}")
            # Continue to next step rather than failing completely
            time.sleep(1)

    print(f"\n🏁 Example completed after {step + 1} steps")
    logger.info("Example completed")


if __name__ == "__main__":
    main()