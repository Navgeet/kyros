#!/usr/bin/env python3
"""
Startup script for the Conversational Planning Agent V2
"""

import os
import sys
from agent_v2 import ConversationalPlanningAgent

def main():
    """Main function to start the agent."""

    # Check for required environment variables
    api_key = os.getenv('INTERNLM_API_KEY')
    if not api_key:
        print("❌ Error: INTERNLM_API_KEY environment variable not set.")
        print("Please set your InternLM API key:")
        print("export INTERNLM_API_KEY='your-api-key-here'")
        print("Optionally set custom API URL:")
        print("export INTERNLM_API_URL='your-api-url-here'")
        return

    # Get optional configuration
    host = os.getenv('AGENT_HOST', '0.0.0.0')
    port = int(os.getenv('AGENT_PORT', '8001'))

    try:
        # Create and run the agent
        print("🚀 Starting Conversational Planning Agent V2...")
        print(f"📡 Host: {host}")
        print(f"🔌 Port: {port}")
        print(f"🤖 API Key configured: {'✅' if api_key else '❌'}")
        print("=" * 50)

        agent = ConversationalPlanningAgent(host=host, port=port)
        agent.run()

    except KeyboardInterrupt:
        print("\n👋 Agent shutdown requested by user")
    except Exception as e:
        print(f"❌ Failed to start the agent: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
