#!/usr/bin/env python3
"""
Test the full Kyros pipeline with a mock LLM to verify everything works.
"""

import logging
from autoglm import KyrosAgent
from desktop_observation import get_desktop_observation
from action_execution import ActionExecutor

def mock_llm_function(messages):
    """Mock LLM that returns a simple click action."""
    print("🤖 Mock LLM received messages:")
    for i, msg in enumerate(messages):
        if msg['role'] == 'system':
            print(f"  {i+1}. System: {msg['content'][:100]}...")
        elif msg['role'] == 'user':
            if isinstance(msg['content'], list):
                print(f"  {i+1}. User: [multimodal content with {len(msg['content'])} parts]")
            else:
                print(f"  {i+1}. User: {msg['content'][:100]}...")

    # Return a simple action
    return """I'll click on the center of the screen to complete this task.

```python
Agent.click([960, 540])
```"""

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("kyros.test")

    print("🧪 Testing Full Kyros Pipeline")
    print("=" * 40)

    # Create agent with mock LLM
    print("1. Creating agent...")
    agent = KyrosAgent(
        with_image=True,
        with_atree=True,
        gen_func=mock_llm_function
    )

    # Create action executor
    executor = ActionExecutor()

    print("\n2. Getting desktop observation...")
    obs = get_desktop_observation()
    print(f"   Screenshot: {len(obs['screenshot'])} bytes")
    print(f"   A11y tree: {len(obs['accessibility_tree'])} chars")
    print(f"   Current app: {obs['cur_app']}")

    print("\n3. Generating action...")
    instruction = "Click on the center of the screen"
    response, actions = agent.predict(instruction, obs)

    print(f"\n4. LLM Response: {response[:200]}...")
    print(f"   Actions: {actions}")

    if actions:
        print("\n5. Executing action...")
        result = executor.execute_action(actions[0])
        print(f"   Result: {result}")
    else:
        print("\n5. No actions to execute")

    print("\n✅ Full pipeline test completed!")

if __name__ == "__main__":
    main()