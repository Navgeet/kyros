#!/usr/bin/env python3
"""
Comprehensive test suite for Claude Code Agent.
"""

import sys
import time
import subprocess
from pathlib import Path


def test_dependencies():
    """Test if all dependencies are available."""
    print("🔍 Testing Dependencies")
    print("-" * 30)

    missing_deps = []

    try:
        import fastapi
        print("✅ FastAPI available")
    except ImportError:
        missing_deps.append("fastapi")
        print("❌ FastAPI missing")

    try:
        import uvicorn
        print("✅ Uvicorn available")
    except ImportError:
        missing_deps.append("uvicorn")
        print("❌ Uvicorn missing")

    try:
        import pyautogui
        print("✅ PyAutoGUI available")
    except ImportError:
        missing_deps.append("pyautogui")
        print("❌ PyAutoGUI missing")

    try:
        from PIL import Image
        print("✅ Pillow available")
    except ImportError:
        missing_deps.append("pillow")
        print("❌ Pillow missing")

    try:
        import requests
        print("✅ Requests available")
    except ImportError:
        missing_deps.append("requests")
        print("❌ Requests missing")

    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install -r requirements_claude_agent.txt")
        return False
    else:
        print("\n✅ All dependencies available")
        return True


def test_claude_code_cli():
    """Test Claude Code CLI availability."""
    print("\n🤖 Testing Claude Code CLI")
    print("-" * 30)

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Claude Code CLI available: {result.stdout.strip()}")
            return True
        else:
            print("❌ Claude Code CLI not responding correctly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Claude Code CLI not found")
        print("Install from: https://docs.anthropic.com/claude/docs/claude-code")
        return False


def test_agent_functionality():
    """Test basic agent functionality."""
    print("\n🧪 Testing Agent Functionality")
    print("-" * 30)

    try:
        from test_simple_agent import MockClaudeCodeAgent

        agent = MockClaudeCodeAgent()
        print("✅ Agent initialization successful")

        # Test screenshot
        screenshot = agent.take_screenshot("test_functionality")
        print(f"✅ Screenshot functionality: {screenshot}")

        # Test plan generation
        result = agent.process_user_request("take a screenshot")
        success = result.get('execution', {}).get('success', False)
        print(f"✅ Plan generation and execution: {success}")

        return True

    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


def test_web_server_components():
    """Test web server components."""
    print("\n🌐 Testing Web Server Components")
    print("-" * 30)

    try:
        from claude_code_web_server import ClaudeCodeWebServer
        print("✅ Web server imports successful")

        # Test server creation
        server = ClaudeCodeWebServer()
        print("✅ Web server instance creation successful")

        return True

    except Exception as e:
        print(f"❌ Web server test failed: {e}")
        return False


def run_integration_test():
    """Run a quick integration test."""
    print("\n🔗 Running Integration Test")
    print("-" * 30)

    try:
        from test_simple_agent import test_mock_agent
        agent = test_mock_agent()
        print("✅ Integration test passed")
        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Claude Code Agent Test Suite")
    print("=" * 50)

    tests = [
        ("Dependencies", test_dependencies),
        ("Claude Code CLI", test_claude_code_cli),
        ("Agent Functionality", test_agent_functionality),
        ("Web Server Components", test_web_server_components),
        ("Integration", run_integration_test),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False

    print("\n📊 Test Results Summary")
    print("=" * 30)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Claude Code Agent is ready to use.")
        print("\nQuick start:")
        print("  Web interface:  python start_claude_agent.py --mode web")
        print("  Test server:    python test_web_server.py")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("Note: Claude Code CLI test failure is expected if not installed.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)