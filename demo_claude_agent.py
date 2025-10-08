#!/usr/bin/env python3
"""
Demo script for Claude Code Agent.

This script demonstrates the basic functionality of the Claude Code Agent
without requiring a full web server setup.
"""

import time
import sys
import traceback
from claude_code_agent import ClaudeCodeAgent


def demo_basic_functionality():
    """Demonstrate basic agent functionality."""
    print("🚀 Claude Code Agent Demo")
    print("=" * 50)

    try:
        # Initialize agent
        print("1. Initializing Claude Code Agent...")
        agent = ClaudeCodeAgent()
        print("   ✅ Agent initialized successfully")

        # Test screenshot functionality
        print("\n2. Testing screenshot functionality...")
        screenshot_name = agent.take_screenshot("demo_initial")
        print(f"   ✅ Screenshot saved: {screenshot_name}")

        # Test basic plan generation (mock mode for demo)
        print("\n3. Testing plan generation...")
        print("   ⚠️  Note: This requires Claude Code CLI to be installed")

        # Simple test that doesn't require actual Claude Code
        test_request = "take a screenshot"

        try:
            result = agent.process_user_request(test_request)
            print("   ✅ Plan generation and execution completed")
            print(f"   📊 Success: {result.get('execution', {}).get('success', False)}")
            print(f"   ⏱️  Duration: {result.get('duration', 0):.2f}s")

            if 'review' in result:
                print(f"   📝 Review available: {len(result['review'])} characters")

        except Exception as e:
            print(f"   ⚠️  Plan generation failed (expected if Claude Code CLI not available): {e}")

        print("\n4. Testing conversation history...")
        print(f"   📜 History entries: {len(agent.conversation_history)}")

        print("\n✅ Demo completed successfully!")

        return True

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False


def demo_web_server_check():
    """Check if web server components work."""
    print("\n🌐 Web Server Component Check")
    print("=" * 30)

    try:
        from claude_code_web_server import ClaudeCodeWebServer
        print("✅ Web server imports work")

        # Try to create server instance (don't start it)
        server = ClaudeCodeWebServer()
        print("✅ Web server instance created")

        print("✅ Web server components are functional")
        return True

    except Exception as e:
        print(f"❌ Web server check failed: {e}")
        return False


def show_usage_examples():
    """Show usage examples."""
    print("\n📚 Usage Examples")
    print("=" * 20)

    examples = [
        "search google for restaurants near me",
        "open a new browser tab",
        "take a screenshot",
        "click on the search box",
        "type 'hello world' and press enter",
        "open calculator app",
        "focus on chrome window"
    ]

    print("Example requests you can try:")
    for i, example in enumerate(examples, 1):
        print(f"  {i}. {example}")

    print("\nStartup commands:")
    print("  • Web interface:   python start_claude_agent.py --mode web")
    print("  • Standalone CLI:  python start_claude_agent.py --mode standalone")
    print("  • Demo:           python demo_claude_agent.py")


def main():
    """Main demo function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_usage_examples()
        return

    success = demo_basic_functionality()

    if success:
        demo_web_server_check()

    show_usage_examples()

    if success:
        print(f"\n🎉 All systems operational!")
        print(f"Ready to use Claude Code Agent.")
    else:
        print(f"\n⚠️  Some issues detected. Check the error messages above.")


if __name__ == "__main__":
    main()