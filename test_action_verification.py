#!/usr/bin/env python3
"""
Test script for the action verification system.
Demonstrates the 2-LLM call verification workflow with mock data.
"""

import os
import sys
import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from llm_integration import create_internlm_function
from action_verification import ActionVerifier


def create_mock_screenshot(text: str, size=(800, 600), bg_color=(255, 255, 255)):
    """Create a mock screenshot with text for testing."""
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)

    # Try to use a default font, fall back to basic if needed
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Calculate text position (centered)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    # Draw text
    draw.text((x, y), text, fill=(0, 0, 0), font=font)

    # Convert to bytes
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def test_verification_system():
    """Test the action verification system with mock data."""
    print("🧪 Testing Action Verification System")
    print("=" * 50)

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Check for API configuration
    api_url = os.getenv("INTERNLM_API_URL", "http://localhost:23333")
    api_key = os.getenv("INTERNLM_API_KEY")

    if not api_key:
        print("⚠️  Warning: INTERNLM_API_KEY not set. This test requires API access.")
        print("Set INTERNLM_API_KEY environment variable and try again.")
        return False

    print(f"🌐 Using InternLM API at: {api_url}")

    # Create LLM function
    llm_function = create_internlm_function(
        api_url=api_url,
        api_key=api_key,
        model="internvl3.5-241b-a28b"
    )

    # Create verifier
    verifier = ActionVerifier(gen_func=llm_function, image_size=(800, 600))

    # Test scenarios
    test_scenarios = [
        {
            "name": "Successful Click Action",
            "task": "Click on the 'Submit' button to submit the form",
            "action": "pyautogui.click(400, 300)",
            "before_text": "Form with Submit Button",
            "after_text": "Form Submitted Successfully",
            "action_result": "Clicked at (400, 300)"
        },
        {
            "name": "Failed Text Input",
            "task": "Type 'Hello World' in the text field",
            "action": "pyautogui.typewrite('Hello World')",
            "before_text": "Empty Text Field",
            "after_text": "Empty Text Field",  # No change - failure
            "action_result": "Typed 'Hello World'"
        },
        {
            "name": "Successful Application Launch",
            "task": "Open a text editor application",
            "action": "pyautogui.hotkey('ctrl', 'alt', 't')",
            "before_text": "Desktop with Terminal Icon",
            "after_text": "Terminal Window Open",
            "action_result": "Pressed Ctrl+Alt+T"
        }
    ]

    print(f"\n🔬 Running {len(test_scenarios)} test scenarios...\n")

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"{'='*20} Test {i}: {scenario['name']} {'='*20}")

        # Create mock screenshots
        before_screenshot = create_mock_screenshot(scenario["before_text"])
        after_screenshot = create_mock_screenshot(scenario["after_text"])

        # Run verification
        print("🔍 Running action verification...")
        verification_result = verifier.verify_action(
            task=scenario["task"],
            previous_action=scenario["action"],
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
            action_result=scenario["action_result"]
        )

        print(f"📊 Verification Results:")
        print(f"   Success: {verification_result['success']}")
        print(f"   Changes: {verification_result['changes']}")
        print(f"   Issues: {verification_result['issues']}")
        print(f"   Confidence: {verification_result['confidence']}")

        # Run planning improvement
        print("\n🧠 Running planning improvement...")
        planning_result = verifier.improve_planning(
            task=scenario["task"],
            verification_result=verification_result,
            current_context={"step": i, "scenario": scenario["name"]}
        )

        print(f"📋 Planning Results:")
        print(f"   Strategy: {planning_result['strategy']}")
        print(f"   Corrections: {planning_result['corrections']}")
        print(f"   Risks: {planning_result['risks']}")
        print(f"   Confidence: {planning_result['confidence']}")

        print(f"\n✅ Test {i} completed\n")

    # Print summary
    print("📊 VERIFICATION TEST SUMMARY")
    print("=" * 40)
    history = verifier.get_verification_history()
    if history:
        success_count = len([v for v in history if v.get('success') == 'YES'])
        partial_count = len([v for v in history if v.get('success') == 'PARTIAL'])
        fail_count = len([v for v in history if v.get('success') == 'NO'])

        print(f"Total Tests: {len(history)}")
        print(f"✅ Successful: {success_count}")
        print(f"🟡 Partial: {partial_count}")
        print(f"❌ Failed: {fail_count}")

        print("\nTest Details:")
        for i, v in enumerate(history, 1):
            print(f"{i}. {v.get('action', 'Unknown')[:40]}... -> {v.get('success', 'Unknown')}")

    print("\n✅ Action verification system test completed!")
    return True


if __name__ == "__main__":
    success = test_verification_system()
    sys.exit(0 if success else 1)