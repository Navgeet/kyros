#!/usr/bin/env python3
"""
Simple test to verify JSON structure without requiring actual tools
"""

import tempfile
import subprocess
import json
import os
import time

def test_simple_json_return():
    """Test with a simple main function that returns the expected JSON structure"""

    # Simple test code that doesn't require external tools
    test_code = '''import json

def main():
    messages = []
    context = []

    # Simulate some work
    messages.append("Starting simple test...")
    messages.append("Performing calculation: 2 + 2")
    result = 2 + 2
    context.append(f"calculation_result: {result}")

    if result == 4:
        messages.append("Test successful: 2 + 2 equals 4")
        done = True
    else:
        messages.append(f"Test failed: Expected 4 but got {result}")
        done = False

    return {"messages": messages, "context": context, "done": done}

if __name__ == "__main__":
    import json
    result = main()
    print(json.dumps(result))
'''

    print("🧪 Testing simple JSON return structure...")
    print("=" * 50)

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(test_code)
        temp_file_path = temp_file.name

    try:
        # Execute the code
        result = subprocess.run(
            ['python', temp_file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        if result.returncode == 0:
            # Try to parse JSON
            try:
                json_output = json.loads(result.stdout.strip())
                print("✅ JSON parsing successful!")
                print(f"Parsed JSON: {json_output}")

                # Validate structure
                required_keys = ['messages', 'context', 'done']
                has_all_keys = all(key in json_output for key in required_keys)
                print(f"Has all required keys: {has_all_keys}")

                if has_all_keys:
                    print("✅ JSON structure is valid!")
                    return True
                else:
                    print("❌ JSON structure is invalid!")
                    return False

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                return False
        else:
            print("❌ Code execution failed!")
            return False

    finally:
        # Clean up
        os.unlink(temp_file_path)

def test_with_mock_tools():
    """Test with mock tools to simulate real scenario"""

    # Test code with mock tools
    test_code = '''
# Mock tools module for testing
class MockTools:
    @staticmethod
    def focus_window(name):
        print(f"Mock: Focusing window '{name}'")
        return True  # Simulate successful focus

    @staticmethod
    def click(x, y):
        print(f"Mock: Clicking at ({x}, {y})")
        return True

    @staticmethod
    def type(text):
        print(f"Mock: Typing '{text}'")
        return True

    @staticmethod
    def query_screen(query):
        print(f"Mock: Querying screen: '{query}'")
        # Simulate different responses based on query
        if "Answer field" in query:
            return "4"  # Simulate successful calculation
        elif "Basic Calculator" in query:
            return ["Calculator Window"]
        return "Mock response"

# Use mock tools
tools = MockTools()
import json

def main():
    messages = []
    context = []

    # Step 1: Focus window with error handling using return value
    focused = tools.focus_window("Basic Calculator")
    if not focused:
        candidates = tools.query_screen("List all open browser tabs containing 'Basic Calculator'")
        if candidates:
            tools.focus_window(candidates[0])
            messages.append(f"Focused on candidate window: {candidates[0]}")
        else:
            messages.append("ERROR: Basic Calculator window not found")
            return {"messages": messages, "context": context, "done": False}
    messages.append("Successfully focused Basic Calculator window")

    # Steps 2-6: Input numbers and calculate
    try:
        tools.click(x=0.4000, y=0.7122)
        tools.type("2")
        tools.click(x=0.4000, y=0.7422)
        tools.type("2")
        tools.click(x=0.3800, y=0.7922)
    except Exception as e:
        messages.append(f"Error: Element interaction failed - {e}")
        return {"messages": messages, "context": context, "done": False}

    # Step 7: Get calculation result
    answer = tools.query_screen("What is the current value in the Answer field?")
    context.append(answer)

    # Step 8: Validate result
    if answer.strip() == "4":
        messages.append("Test successful: 2 + 2 equals 4")
    else:
        messages.append(f"Test failed: Expected 4 but got {answer}")

    return {"messages": messages, "context": context, "done": True}

if __name__ == "__main__":
    import json
    result = main()
    print(json.dumps(result))
'''

    print("\n🧪 Testing with mock tools...")
    print("=" * 50)

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(test_code)
        temp_file_path = temp_file.name

    try:
        # Execute the code
        result = subprocess.run(
            ['python', temp_file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        if result.returncode == 0:
            # Try to parse JSON from the output
            stdout_lines = result.stdout.strip().split('\n')
            json_line = stdout_lines[-1]  # JSON should be the last line

            try:
                json_output = json.loads(json_line)
                print("✅ JSON parsing successful!")
                print(f"Parsed JSON: {json_output}")

                # Validate structure
                required_keys = ['messages', 'context', 'done']
                has_all_keys = all(key in json_output for key in required_keys)
                print(f"Has all required keys: {has_all_keys}")

                if has_all_keys:
                    print("✅ JSON structure is valid!")
                    print(f"Messages: {json_output['messages']}")
                    print(f"Context: {json_output['context']}")
                    print(f"Done: {json_output['done']}")
                    return True
                else:
                    print("❌ JSON structure is invalid!")
                    return False

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Attempted to parse: '{json_line}'")
                return False
        else:
            print("❌ Code execution failed!")
            return False

    finally:
        # Clean up
        os.unlink(temp_file_path)

def main():
    print("🧪 Simple Code Execution Tests")
    print("=" * 50)

    # Test 1: Simple JSON structure
    print("Test 1: Simple JSON structure")
    test1_passed = test_simple_json_return()

    # Test 2: Mock tools simulation
    print("\nTest 2: Mock tools simulation")
    test2_passed = test_with_mock_tools()

    print("\n" + "=" * 50)
    print("📊 RESULTS:")
    print(f"Test 1 (Simple JSON): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Mock Tools): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! JSON structure is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")

if __name__ == "__main__":
    main()