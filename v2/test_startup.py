#!/usr/bin/env python3
"""
Test script to verify the agent starts without event loop errors
"""

import os
import sys
from agent_v2 import ConversationalPlanningAgent

def test_agent_creation():
    """Test that the agent can be created without errors."""
    try:
        # Set a dummy API key to avoid the environment check
        os.environ['INTERNLM_API_KEY'] = 'test-key'

        print("🧪 Testing agent creation...")
        agent = ConversationalPlanningAgent(host='localhost', port=8002)
        print("✅ Agent created successfully without event loop errors!")

        # Test that the app is configured properly
        print(f"📡 FastAPI app title: {agent.app.title}")
        print(f"🔧 Routes configured: {len(agent.app.routes)}")
        print(f"💾 Session timeout: {agent.session_timeout_hours} hours")

        return True

    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        return False

if __name__ == "__main__":
    success = test_agent_creation()
    sys.exit(0 if success else 1)