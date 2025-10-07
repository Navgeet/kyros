#!/usr/bin/env python3
"""
Enhanced Kyros AutoGLM agent with 2-LLM action verification system.

This demonstrates how to use the Kyros agent with:
- InternLM API for LLM calls
- Real desktop observation functions
- Action execution system
- Action verification using before/after screenshots
- Planning improvement based on verification results
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
from action_verification import ActionVerifier


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
    """Main function demonstrating the enhanced Kyros agent with verification."""
    logger = setup_logging()

    print("🤖 Kyros AutoGLM Agent - Enhanced with Action Verification")
    print("=" * 60)

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

    # Create action verifier
    verifier = ActionVerifier(gen_func=llm_function, image_size=(1920, 1080))

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

    # Main interaction loop with verification
    max_steps = 10
    previous_action = None
    previous_screenshot = None
    command_output_log = []  # Store shell command outputs for observation
    verification_context = {}  # Store verification results for planning

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

            # Add previous action and screenshot to observation
            if previous_action is not None:
                obs["previous_action"] = previous_action
            if previous_screenshot is not None:
                obs["previous_screenshot"] = previous_screenshot

            # Add command output log to observation
            if command_output_log:
                # Include last 5 command outputs to keep context manageable
                obs["command_history"] = command_output_log[-5:]

            # Add verification context to observation if available
            if verification_context:
                obs["verification_context"] = verification_context

            print(f"📊 Observation: Screenshot={len(obs['screenshot'])} bytes, "
                  f"Apps={len(obs['apps'])}, Current={obs['cur_app']}")

            # ACTION VERIFICATION PHASE
            # If we have previous action and screenshots, verify the action first
            if (previous_action is not None and
                previous_screenshot is not None and
                previous_action not in ["WAIT", "DONE", "FAIL"]):

                print("🔍 Verifying previous action...")
                verification_result = verifier.verify_action(
                    task=instruction,
                    previous_action=previous_action,
                    before_screenshot=previous_screenshot,
                    after_screenshot=obs['screenshot'],
                    action_result=executor.get_last_result()
                )

                print(f"📊 Verification: Success={verification_result['success']}, "
                      f"Confidence={verification_result['confidence']}")

                # PLANNING IMPROVEMENT PHASE
                print("🧠 Improving planning based on verification...")
                planning_result = verifier.improve_planning(
                    task=instruction,
                    verification_result=verification_result,
                    current_context=obs,
                    agent_history=agent.format_history()
                )

                print(f"📋 Planning: Strategy={planning_result['strategy'][:50]}...")

                # Store verification context for next iteration
                verification_context = {
                    "last_verification": verification_result,
                    "last_planning": planning_result,
                    "success_rate": len([v for v in verifier.get_verification_history()
                                       if v.get('success') == 'YES']) / len(verifier.get_verification_history())
                    if verifier.get_verification_history() else 0
                }

                # Add planning guidance to observation
                obs["planning_guidance"] = {
                    "strategy": planning_result["strategy"],
                    "corrections": planning_result["corrections"],
                    "risks": planning_result["risks"],
                    "success_indicators": planning_result["success_indicators"]
                }

            # Generate next action
            print("🎭 Generating next action with LLM...")
            response, actions = agent.predict(instruction, obs)

            if not actions:
                logger.error("No valid actions generated")
                print("❌ No valid actions generated. Stopping.")
                break

            action = actions[0]
            print(f"🎬 Next Action: {action}")
            logger.info(f"Generated action: {action}")

            # Check for terminal actions
            if action in ["DONE", "FAIL"]:
                print(f"🏁 Task completed with status: {action}")
                logger.info(f"Task completed with status: {action}")

                # Final verification if we have before/after screenshots
                if previous_action and previous_screenshot:
                    print("🔍 Final verification...")
                    final_verification = verifier.verify_action(
                        task=instruction,
                        previous_action=previous_action,
                        before_screenshot=previous_screenshot,
                        after_screenshot=obs['screenshot'],
                        action_result=executor.get_last_result()
                    )
                    print(f"📊 Final result: {final_verification['success']} - {final_verification['reasoning'][:100]}...")
                break
            elif action == "WAIT":
                print("⏸️  Waiting...")
                logger.info("Waiting...")
                time.sleep(2)
                continue

            # Store current state before executing action
            current_screenshot = obs.get('screenshot')

            # Execute the action
            print("⚡ Executing action...")
            result = executor.execute_action(action)
            print(f"📋 Execution Result: {result}")

            # Update state for next iteration
            previous_action = action
            previous_screenshot = current_screenshot

            # Check if this was a shell command and capture its output
            if "run_shell_cmd" in str(action) or "Executing shell command:" in str(result):
                command_entry = {
                    "step": step + 1,
                    "action": action,
                    "output": result,
                    "timestamp": time.strftime("%H:%M:%S")
                }
                command_output_log.append(command_entry)
                print(f"🐚 Shell command logged: {len(command_output_log)} total commands")

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

    # Print verification summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 40)
    history = verifier.get_verification_history()
    if history:
        success_count = len([v for v in history if v.get('success') == 'YES'])
        partial_count = len([v for v in history if v.get('success') == 'PARTIAL'])
        fail_count = len([v for v in history if v.get('success') == 'NO'])

        print(f"Total Actions Verified: {len(history)}")
        print(f"✅ Successful: {success_count}")
        print(f"🟡 Partial: {partial_count}")
        print(f"❌ Failed: {fail_count}")
        print(f"Success Rate: {(success_count / len(history) * 100):.1f}%")

        print("\nVerification Details:")
        for i, v in enumerate(history[-3:], 1):  # Show last 3
            print(f"{i}. {v.get('action', 'Unknown')[:30]}... -> {v.get('success', 'Unknown')}")
    else:
        print("No actions were verified.")

    print(f"\n🏁 Enhanced example completed after {step + 1} steps")
    logger.info("Enhanced example completed")


if __name__ == "__main__":
    main()