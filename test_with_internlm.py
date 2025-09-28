#!/usr/bin/env python3
"""
Test Kyros with relative coordinates using InternLM API.
"""

import logging
import os
from autoglm import KyrosAgent
from llm_integration import create_internlm_function
from desktop_observation import get_desktop_observation
from action_execution import ActionExecutor

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("kyros.internlm_test")

    print("🤖 Testing Kyros with InternLM and Relative Coordinates")
    print("=" * 55)

    # Configure InternLM API from environment
    api_url = os.getenv("INTERNLM_API_URL", "http://localhost:23333")
    api_key = os.getenv("INTERNLM_API_KEY")

    print(f"🌐 InternLM API URL: {api_url}")
    if api_key:
        print(f"🔑 API Key: {'*' * 20}{api_key[-4:]}")
    else:
        print("⚠️  No API key set")

    # Create LLM function
    llm_function = create_internlm_function(
        api_url=api_url,
        api_key=api_key,
        model="internvl3.5-241b-a28b"
    )

    # Create agent with relative coordinates
    print("\n🎯 Creating agent with relative coordinates...")
    agent = KyrosAgent(
        with_image=True,
        with_atree=True,
        relative_coordinate=True,  # Use relative coordinates for InternLM
        screen_size=(1920, 1200),  # Update to actual screen size
        gen_func=llm_function
    )

    print(f"   ✅ Agent configured with relative coordinates: {agent.relative_coordinate}")

    # Create action executor
    executor = ActionExecutor(screen_size=(1920, 1200))

    # Get observation
    print("\n📸 Getting desktop observation...")
    obs = get_desktop_observation()
    print(f"   Screenshot: {len(obs['screenshot'])} bytes")
    print(f"   A11y tree: {len(obs['accessibility_tree'])} chars")
    print(f"   Current app: {obs['cur_app']}")

    # Test simple task
    instruction = "Click at the center of the screen"
    print(f"\n🎯 Task: {instruction}")

    try:
        print("🧠 Generating action with InternLM...")
        response, actions = agent.predict(instruction, obs)

        print(f"📝 Response: {response[:200]}...")
        print(f"🎬 Actions: {actions}")

        if actions:
            print("⚡ Executing action...")
            result = executor.execute_action(actions[0])
            print(f"📋 Result: {result}")

            # Check if relative coordinates were used
            if "relative" in result.lower() and "absolute" in result.lower():
                print("✅ Relative coordinates working correctly!")
            else:
                print("⚠️  Check coordinate conversion")
        else:
            print("❌ No actions generated")

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")

    print("\n🏁 Test completed!")

if __name__ == "__main__":
    main()