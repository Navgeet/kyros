#!/usr/bin/env python3
"""
Test the web server with the mock agent.
"""

from claude_code_web_server import ClaudeCodeWebServer
from test_simple_agent import MockClaudeCodeAgent
import asyncio


# Monkey patch the web server to use our mock agent
class TestWebServer(ClaudeCodeWebServer):
    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__(host, port)
        # Replace the agent with our mock version
        self.agent = MockClaudeCodeAgent()


if __name__ == "__main__":
    print("🌐 Starting Test Web Server with Mock Agent")
    print("=" * 50)
    print("Open your browser to: http://localhost:8000")
    print("Try these test requests:")
    print("  • take a screenshot")
    print("  • search google for restaurants")
    print("  • open a new browser tab")
    print("\nPress Ctrl+C to stop")
    print("=" * 50)

    server = TestWebServer()
    server.run()