#!/usr/bin/env python3
"""
Startup script for Claude Code Agent.

This script provides a simple way to start the Claude Code Agent with different options.
"""

import argparse
import sys
import subprocess
from pathlib import Path


def check_requirements():
    """Check if required packages are installed."""
    try:
        import fastapi
        import uvicorn
        import pyautogui
        from PIL import Image
        print("✅ All required packages are available")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements: pip install -r requirements_claude_agent.txt")
        return False


def check_claude_code():
    """Check if Claude Code CLI is available."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Claude Code CLI found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Claude Code CLI not responding correctly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Claude Code CLI not found")
        print("Please install Claude Code CLI: https://docs.anthropic.com/claude/docs/claude-code")
        return False


def run_agent_standalone():
    """Run the agent in standalone mode (command line)."""
    print("🤖 Starting Claude Code Agent in standalone mode...")

    from claude_code_agent import ClaudeCodeAgent

    agent = ClaudeCodeAgent()

    print("\nAgent ready! Enter your task requests (or 'quit' to exit):")

    while True:
        try:
            user_input = input("\n👤 You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            print("\n🤖 Processing your request...")
            result = agent.process_user_request(user_input)

            print(f"\n📊 Results:")
            print(f"Success: {result.get('execution', {}).get('success', False)}")
            print(f"Duration: {result.get('duration', 0):.2f}s")

            if 'review' in result:
                print(f"\nClaude Code Review:\n{result['review']}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def run_web_server(host="localhost", port=8000):
    """Run the web server."""
    print(f"🌐 Starting Claude Code Agent Web Server on {host}:{port}...")

    from claude_code_web_server import ClaudeCodeWebServer

    server = ClaudeCodeWebServer(host=host, port=port)
    server.run()


def main():
    parser = argparse.ArgumentParser(description="Claude Code Agent Startup Script")
    parser.add_argument(
        "--mode",
        choices=["web", "standalone"],
        default="web",
        help="Run mode: web server or standalone CLI"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for web server (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for web server (default: 8000)"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip dependency and Claude Code checks"
    )

    args = parser.parse_args()

    print("🚀 Claude Code Agent Startup")
    print("=" * 40)

    if not args.skip_checks:
        print("🔍 Checking requirements...")

        if not check_requirements():
            sys.exit(1)

        if not check_claude_code():
            print("\n⚠️  Warning: Claude Code CLI not found. Agent may not work correctly.")
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                sys.exit(1)

    print(f"\n🎯 Starting in {args.mode} mode...")

    try:
        if args.mode == "web":
            run_web_server(args.host, args.port)
        else:
            run_agent_standalone()
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Error starting agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()