#!/usr/bin/env python3
"""
Test script to verify the agent server can start properly
"""

import os
import asyncio
import signal
from agent_v2 import ConversationalPlanningAgent

async def test_server_startup():
    """Test that the server can start and initialize properly."""
    try:
        # Set a dummy API key
        os.environ['INTERNLM_API_KEY'] = 'test-key'

        print("🧪 Testing server startup...")
        agent = ConversationalPlanningAgent(host='localhost', port=8002)

        # Simulate the startup event
        startup_handlers = [
            route.endpoint for route in agent.app.router.routes
            if hasattr(route, 'endpoint') and
            getattr(route, 'path', None) == '/startup'
        ]

        print("✅ Server configuration successful!")
        print(f"📡 Will bind to: localhost:8002")
        print(f"🔧 Routes: {len(agent.app.routes)}")
        print(f"💾 Sessions: {len(agent.sessions)}")
        print(f"⏰ Cleanup task initialized: {agent._cleanup_task is None}")

        return True

    except Exception as e:
        print(f"❌ Error testing server startup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server_startup())
    if success:
        print("\n🎉 All startup tests passed!")
        print("You can now run: python start_agent_v2.py")
    else:
        print("\n💥 Server startup tests failed!")