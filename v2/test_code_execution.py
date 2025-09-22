#!/usr/bin/env python3
"""
Test script to debug code execution issues in agent_v2.py
Uses the same code execution logic as the agent to test generated code.
"""

import asyncio
import sys
import os
import tempfile
import subprocess
import time
import json

# Add parent directory to path to import agent modules
sys.path.append('..')
sys.path.append('.')

def test_code_execution(python_code: str) -> dict:
    """
    Test code execution using the same logic as agent_v2.py
    """
    print("🧪 Starting code execution test...")
    start_time = time.time()

    try:
        # Ensure the code calls the main function if it's defined
        code_to_execute = python_code
        print(f"🐍 Original code length: {len(python_code)} characters")
        print(f"🔍 Checking for main function definition...")

        if 'def main(' in python_code:
            print(f"✅ Found main function definition")
            # Check if main() is already called
            after_main_def = python_code.split('def main(')[1]
            if 'main(' not in after_main_def:
                print(f"📝 Adding main function call...")
                # Add main function call if it's defined but not called
                # The new main function takes no arguments and returns JSON
                code_to_execute += '\n\nif __name__ == "__main__":\n    import json\n    result = main()\n    print(json.dumps(result))\n'
                print(f"✅ Added main function call")
            else:
                print(f"✅ Main function already called in code")
        else:
            print(f"⚠️ No main function definition found")

        print(f"🐍 Final code length: {len(code_to_execute)} characters")
        print(f"📄 Code to execute:")
        print("-" * 60)
        print(code_to_execute)
        print("-" * 60)

        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code_to_execute)
            temp_file_path = temp_file.name
            print(f"💾 Code written to temporary file: {temp_file_path}")

        try:
            # Execute the code with timeout
            print(f"🚀 Executing Python code with 30s timeout...")
            print(f"📂 Working directory: {os.path.dirname(temp_file_path)}")

            result = subprocess.run(
                ['python', temp_file_path],
                capture_output=True,
                text=True,
                timeout=300,  # 30 second timeout
                cwd=os.path.dirname(temp_file_path)
            )

            execution_time = time.time() - start_time
            print(f"⏱️ Execution completed in {execution_time:.2f}s")
            print(f"🔢 Return code: {result.returncode}")
            print(f"📤 STDOUT ({len(result.stdout)} chars):")
            print(result.stdout)
            print(f"⚠️ STDERR ({len(result.stderr)} chars):")
            print(result.stderr)

            if result.returncode == 0:
                # Try to parse JSON output from the main function
                print(f"✅ Code executed successfully")
                try:
                    stdout_clean = result.stdout.strip()
                    print(f"🔍 Attempting to parse JSON from stdout: '{stdout_clean}'")
                    json_output = json.loads(stdout_clean)
                    print(f"✅ Successfully parsed JSON: {json_output}")

                    # Validate the expected JSON structure
                    required_keys = ['messages', 'context', 'done']
                    has_all_keys = all(key in json_output for key in required_keys)
                    print(f"🔍 JSON validation - has all keys {required_keys}: {has_all_keys}")

                    if isinstance(json_output, dict) and has_all_keys:
                        print(f"✅ JSON structure is valid")
                        return {
                            "success": True,
                            "output": result.stdout,
                            "error": result.stderr if result.stderr else None,
                            "execution_time": round(execution_time, 2),
                            "json_result": json_output,
                            "task_done": json_output.get('done', False),
                            "task_messages": json_output.get('messages', []),
                            "task_context": json_output.get('context', [])
                        }
                    else:
                        # JSON doesn't have expected structure, treat as regular output
                        print(f"⚠️ JSON doesn't have expected structure, treating as regular output")
                        return {
                            "success": True,
                            "output": result.stdout,
                            "error": result.stderr if result.stderr else None,
                            "execution_time": round(execution_time, 2)
                        }
                except json.JSONDecodeError as e:
                    # Not valid JSON, treat as regular output
                    print(f"⚠️ JSON parsing failed: {e}")
                    return {
                        "success": True,
                        "output": result.stdout,
                        "error": result.stderr if result.stderr else None,
                        "execution_time": round(execution_time, 2)
                    }
            else:
                print(f"❌ Code execution failed with return code: {result.returncode}")
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr,
                    "execution_time": round(execution_time, 2)
                }

        finally:
            # Clean up temp file
            try:
                print(f"🧹 Cleaning up temp file: {temp_file_path}")
                os.unlink(temp_file_path)
            except:
                pass

    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        print(f"⏰ Code execution timed out after 30 seconds")
        return {
            "success": False,
            "output": "",
            "error": "Code execution timed out after 30 seconds",
            "execution_time": round(execution_time, 2)
        }
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"💥 Execution error: {e}")
        return {
            "success": False,
            "output": "",
            "error": f"Execution error: {str(e)}",
            "execution_time": round(execution_time, 2)
        }

def main():
    print("🧪 Code Execution Test Script")
    print("=" * 50)

    # Test code from conversation - the final approved version
    test_code = '''import tools
import json
import time

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
    except:
        messages.append("Error: Element interaction failed - trigger replanning")
        return {"messages": messages, "context": context, "done": False}

    time.sleep(2)
    # Step 7: Get calculation result
    answer = tools.query_screen("What is the current value in the Answer field?")
    context.append(answer)

    # Step 8: Validate result (test outcome doesn't affect task completion status)
    if answer.strip() == "4":
        messages.append("Test successful: 2 + 2 equals 4")
    else:
        messages.append(f"Test failed: Expected 4 but got {answer}")

    return {"messages": messages, "context": context, "done": True}'''

    print("Testing with example code from conversation...")
    print("=" * 50)

    result = test_code_execution(test_code)

    print("\n" + "=" * 50)
    print("🔍 FINAL RESULT:")
    print("=" * 50)
    for key, value in result.items():
        print(f"{key}: {value}")

    if result["success"]:
        print("\n✅ Test completed successfully!")
        if "json_result" in result:
            print("✅ JSON parsing successful!")
            print(f"Task done: {result['task_done']}")
            print(f"Messages: {result['task_messages']}")
            print(f"Context: {result['task_context']}")
        else:
            print("⚠️ No JSON result - treating as regular output")
    else:
        print("\n❌ Test failed!")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()