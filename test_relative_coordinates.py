#!/usr/bin/env python3
"""
Test the relative coordinate functionality of Kyros.
"""

import logging
from autoglm import KyrosAgent
from desktop_observation import get_desktop_observation
from action_execution import ActionExecutor

def mock_llm_function_relative(messages):
    """Mock LLM that returns a relative coordinate click action."""
    print("🤖 Mock LLM received messages:")
    for i, msg in enumerate(messages):
        if msg['role'] == 'system':
            print(f"  {i+1}. System: {msg['content'][:200]}...")
        elif msg['role'] == 'user':
            if isinstance(msg['content'], list):
                print(f"  {i+1}. User: [multimodal content with {len(msg['content'])} parts]")
            else:
                print(f"  {i+1}. User: {msg['content'][:200]}...")

    # Return a relative coordinate action (center of screen)
    return """I'll click at the center of the screen using relative coordinates.

<think>
The screen center should be at relative coordinates [0.5, 0.5]. I'll use this to click.
</think>

```python
Agent.click([0.5, 0.5])
```"""

def test_relative_coordinates():
    """Test relative coordinate functionality."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("kyros.test_relative")

    print("🧪 Testing Relative Coordinates")
    print("=" * 40)

    # Create agent with relative coordinates enabled
    print("1. Creating agent with relative coordinates...")
    agent = KyrosAgent(
        with_image=True,
        with_atree=True,
        relative_coordinate=True,  # Enable relative coordinates
        screen_size=(1920, 1080),
        gen_func=mock_llm_function_relative
    )

    # Verify agent settings
    print(f"   Agent relative_coordinate: {agent.relative_coordinate}")
    print(f"   Agent screen_size: {agent.screen_size}")
    print(f"   GroundingAgent relative_coordinate: {agent.Agent.relative_coordinate}")

    # Create action executor
    executor = ActionExecutor()

    print("\n2. Getting desktop observation...")
    obs = get_desktop_observation()
    print(f"   Screenshot: {len(obs['screenshot'])} bytes")
    print(f"   A11y tree: {len(obs['accessibility_tree'])} chars")
    print(f"   Current app: {obs['cur_app']}")

    print("\n3. Generating action with relative coordinates...")
    instruction = "Click at the center of the screen"
    response, actions = agent.predict(instruction, obs)

    print(f"\n4. LLM Response: {response[:300]}...")
    print(f"   Actions: {actions}")

    if actions:
        print("\n5. Executing relative coordinate action...")
        result = executor.execute_action(actions[0])
        print(f"   Result: {result}")

        # Print expected vs actual coordinate conversion
        print("\n6. Coordinate Analysis:")
        print("   Expected: Center click at relative [0.5, 0.5]")
        print("   Should convert to absolute [960, 540] for 1920x1080 screen")
        if "960" in result and "540" in result:
            print("   ✅ Coordinate conversion appears correct!")
        else:
            print("   ⚠️  Coordinate conversion may need verification")
    else:
        print("\n5. No actions to execute")

    print("\n✅ Relative coordinate test completed!")

def test_accessibility_tree_coordinates():
    """Test that accessibility tree shows relative coordinates."""
    print("\n🔍 Testing Accessibility Tree Coordinates")
    print("=" * 40)

    from autoglm.prompt.accessibility_tree_handle import linearize_accessibility_tree

    # Create a simple mock accessibility tree
    mock_tree = """<?xml version="1.0"?>
<accessibility-tree>
  <application name="test-app">
    <frame name="window" screencoord="(100, 200)" size="(800, 600)">
      <button name="OK" screencoord="(400, 400)" size="(100, 50)"/>
    </frame>
  </application>
</accessibility-tree>"""

    print("1. Testing absolute coordinates...")
    abs_result = linearize_accessibility_tree(
        mock_tree,
        use_relative_coordinates=False,
        screen_size=(1920, 1080)
    )
    print("   Absolute result:")
    for line in abs_result.split('\n')[:5]:  # Show first few lines
        print(f"     {line}")

    print("\n2. Testing relative coordinates...")
    rel_result = linearize_accessibility_tree(
        mock_tree,
        use_relative_coordinates=True,
        screen_size=(1920, 1080)
    )
    print("   Relative result:")
    for line in rel_result.split('\n')[:5]:  # Show first few lines
        print(f"     {line}")

    # Check if coordinates are in 0-1 range
    if "0." in rel_result and not any(coord in rel_result for coord in ["100", "200", "400", "800"]):
        print("   ✅ Accessibility tree coordinates converted to relative!")
    else:
        print("   ⚠️  Accessibility tree coordinates may not be properly converted")

if __name__ == "__main__":
    test_relative_coordinates()
    test_accessibility_tree_coordinates()