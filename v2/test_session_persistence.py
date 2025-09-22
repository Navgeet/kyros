#!/usr/bin/env python3
"""
Test script to verify session persistence works correctly.
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any

class SessionPersistenceTest:
    """Test session persistence functionality."""

    def __init__(self, host: str = "localhost", port: int = 8002):
        self.host = host
        self.port = port
        self.websocket = None
        self.session_id = None

    async def connect(self):
        """Connect to the agent."""
        uri = f"ws://{self.host}:{self.port}/ws"
        print(f"🔌 Connecting to {uri}...")

        try:
            self.websocket = await websockets.connect(uri)
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the agent."""
        if self.websocket:
            await self.websocket.close()
            print("👋 Disconnected")

    async def send_message(self, message: Dict[str, Any]):
        """Send a message to the agent."""
        if not self.websocket:
            print("❌ Not connected")
            return

        message_str = json.dumps(message)
        await self.websocket.send(message_str)
        print(f"📤 Sent: {message.get('type', 'unknown')}")

    async def receive_message(self) -> Dict[str, Any]:
        """Receive a message from the agent."""
        if not self.websocket:
            print("❌ Not connected")
            return {}

        try:
            message_str = await self.websocket.recv()
            message = json.loads(message_str)
            print(f"📥 Received: {message.get('type', 'unknown')}")

            # Track session ID
            if message.get('session_id'):
                self.session_id = message['session_id']
                print(f"💾 Session ID: {self.session_id}")

            return message
        except Exception as e:
            print(f"❌ Error receiving message: {e}")
            return {}

    async def test_session_creation_and_disconnection(self):
        """Test creating a session and simulating disconnection."""
        print("\n🧪 Test 1: Session Creation and Disconnection")
        print("=" * 50)

        # Step 1: Connect and create session
        if not await self.connect():
            return False

        # Step 2: Send new session message
        await self.send_message({"type": "new_session"})
        welcome_msg = await self.receive_message()

        if welcome_msg.get('type') != 'connection':
            print("❌ Expected connection message")
            return False

        original_session_id = self.session_id
        print(f"✅ Created session: {original_session_id}")

        # Step 3: Send a user message to establish some state
        await self.send_message({
            "type": "user_message",
            "content": "Create a simple calculator"
        })

        # Wait for response
        status_msg = await self.receive_message()
        plan_msg = await self.receive_message()

        if plan_msg.get('type') != 'text_plan_review':
            print("❌ Expected text plan review")
            return False

        print("✅ Received text plan, session has state")

        # Step 4: Disconnect to simulate idle timeout
        await self.disconnect()
        print("✅ Simulated connection loss")

        return original_session_id

    async def test_session_resumption(self, session_id: str):
        """Test resuming a previous session."""
        print("\n🧪 Test 2: Session Resumption")
        print("=" * 50)

        # Step 1: Reconnect with resume message
        if not await self.connect():
            return False

        # Step 2: Try to resume session
        await self.send_message({
            "type": "resume_session",
            "session_id": session_id
        })

        resume_msg = await self.receive_message()

        if resume_msg.get('type') == 'session_resumed':
            print(f"✅ Session {session_id} resumed successfully!")

            # Check if we get session state
            state_msg = await self.receive_message()
            if state_msg.get('type') == 'text_plan_review':
                print("✅ Session state restored - found pending plan")
                return True
            else:
                print(f"⚠️  Session resumed but unexpected state: {state_msg.get('type')}")
                return True
        elif resume_msg.get('type') == 'session_not_found':
            print(f"❌ Session {session_id} not found - may have expired")
            return False
        else:
            print(f"❌ Unexpected response: {resume_msg.get('type')}")
            return False

async def run_session_persistence_test():
    """Run the complete session persistence test."""
    print("🚀 Session Persistence Test Suite")
    print("=" * 60)
    print("Testing the agent's ability to maintain sessions across disconnections")
    print("=" * 60)

    tester = SessionPersistenceTest()

    # Test 1: Create session and disconnect
    session_id = await tester.test_session_creation_and_disconnection()
    if not session_id:
        print("❌ Test 1 failed - cannot proceed")
        return False

    # Small delay to simulate real disconnection time
    print("\n⏳ Waiting 2 seconds to simulate realistic reconnection delay...")
    await asyncio.sleep(2)

    # Test 2: Resume session
    resumption_success = await tester.test_session_resumption(session_id)

    await tester.disconnect()

    # Summary
    print("\n📊 Test Results")
    print("=" * 30)
    print(f"Session Creation: {'✅ PASS' if session_id else '❌ FAIL'}")
    print(f"Session Resumption: {'✅ PASS' if resumption_success else '❌ FAIL'}")

    overall_success = bool(session_id) and resumption_success
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

    if overall_success:
        print("\n🎉 Session persistence is working correctly!")
        print("Sessions will survive browser refreshes and temporary disconnections.")
    else:
        print("\n💥 Session persistence has issues that need fixing.")

    return overall_success

if __name__ == "__main__":
    print("🧪 Session Persistence Test")
    print("Make sure the agent is running on localhost:8002 before running this test")
    print("You can start it with: AGENT_PORT=8002 python demo_local.py")
    print()

    try:
        asyncio.run(run_session_persistence_test())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()