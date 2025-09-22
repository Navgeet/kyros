#!/usr/bin/env python3
"""
Test script for the Conversational Planning Agent V2
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any

class AgentV2Tester:
    """Test client for the V2 agent."""

    def __init__(self, host: str = "localhost", port: int = 8001):
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
        print(f"📤 Sent: {message}")

    async def receive_message(self) -> Dict[str, Any]:
        """Receive a message from the agent."""
        if not self.websocket:
            print("❌ Not connected")
            return {}

        try:
            message_str = await self.websocket.recv()
            message = json.loads(message_str)
            print(f"📥 Received: {message['type']}")
            if message.get('session_id'):
                self.session_id = message['session_id']
            return message
        except Exception as e:
            print(f"❌ Error receiving message: {e}")
            return {}

    async def test_basic_workflow(self):
        """Test the basic planning workflow."""
        print("\n🧪 Testing Basic Workflow")
        print("=" * 40)

        # Step 1: Initial connection
        if not await self.connect():
            return False

        # Step 2: Wait for welcome message
        welcome_msg = await self.receive_message()
        if welcome_msg.get('type') != 'connection':
            print("❌ Expected connection message")
            return False

        # Step 3: Send user request
        await self.send_message({
            "type": "user_message",
            "content": "Help me create a simple hello world program"
        })

        # Step 4: Wait for text plan
        plan_msg = await self.receive_message()
        if plan_msg.get('type') != 'text_plan_review':
            print("❌ Expected text plan review")
            return False

        print("✅ Received text plan")

        # Step 5: Approve text plan
        await self.send_message({
            "type": "approval",
            "approved": True
        })

        # Step 6: Wait for code generation
        code_msg = await self.receive_message()
        if code_msg.get('type') != 'code_review':
            print("❌ Expected code review")
            return False

        print("✅ Received generated code")

        # Step 7: Approve code
        await self.send_message({
            "type": "approval",
            "approved": True
        })

        # Step 8: Wait for completion
        completion_msg = await self.receive_message()
        if completion_msg.get('type') != 'completion':
            print("❌ Expected completion message")
            return False

        print("✅ Workflow completed successfully!")

        await self.disconnect()
        return True

    async def test_feedback_workflow(self):
        """Test the feedback and improvement workflow."""
        print("\n🧪 Testing Feedback Workflow")
        print("=" * 40)

        # Step 1: Connect and start conversation
        if not await self.connect():
            return False

        welcome_msg = await self.receive_message()

        # Step 2: Send user request
        await self.send_message({
            "type": "user_message",
            "content": "Create a calculator program"
        })

        # Step 3: Get text plan
        plan_msg = await self.receive_message()
        if plan_msg.get('type') != 'text_plan_review':
            print("❌ Expected text plan review")
            return False

        # Step 4: Request feedback (reject plan)
        await self.send_message({
            "type": "approval",
            "approved": False
        })

        # Step 5: Wait for feedback request
        feedback_request = await self.receive_message()
        if feedback_request.get('type') != 'feedback_request':
            print("❌ Expected feedback request")
            return False

        print("✅ Received feedback request")

        # Step 6: Provide feedback
        await self.send_message({
            "type": "feedback",
            "content": "Please add support for advanced operations like square root and power functions"
        })

        # Step 7: Wait for improved plan
        improved_plan = await self.receive_message()
        if improved_plan.get('type') != 'text_plan_review':
            print("❌ Expected improved text plan")
            return False

        print("✅ Received improved plan")

        await self.disconnect()
        return True

    async def test_replanning_workflow(self):
        """Test the replanning workflow."""
        print("\n🧪 Testing Replanning Workflow")
        print("=" * 40)

        # Step 1: Connect and start conversation
        if not await self.connect():
            return False

        welcome_msg = await self.receive_message()

        # Step 2: Send user request
        await self.send_message({
            "type": "user_message",
            "content": "Create a file organizer"
        })

        # Step 3: Get text plan
        plan_msg = await self.receive_message()
        if plan_msg.get('type') != 'text_plan_review':
            print("❌ Expected text plan review")
            return False

        # Step 4: Request replanning
        await self.send_message({
            "type": "replan",
            "plan_type": "text"
        })

        # Step 5: Wait for new plan
        new_plan = await self.receive_message()
        if new_plan.get('type') != 'text_plan_review':
            print("❌ Expected new text plan")
            return False

        print("✅ Received new plan from replanning")

        await self.disconnect()
        return True

async def run_tests():
    """Run all tests."""
    tester = AgentV2Tester()

    print("🚀 Starting Agent V2 Tests")
    print("=" * 50)

    # Test 1: Basic workflow
    test1_result = await tester.test_basic_workflow()

    # Add delay between tests
    await asyncio.sleep(2)

    # Test 2: Feedback workflow
    test2_result = await tester.test_feedback_workflow()

    # Add delay between tests
    await asyncio.sleep(2)

    # Test 3: Replanning workflow
    test3_result = await tester.test_replanning_workflow()

    # Summary
    print("\n📊 Test Results")
    print("=" * 30)
    print(f"Basic Workflow: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Feedback Workflow: {'✅ PASS' if test2_result else '❌ FAIL'}")
    print(f"Replanning Workflow: {'✅ PASS' if test3_result else '❌ FAIL'}")

    all_passed = test1_result and test2_result and test3_result
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

def main():
    """Main function."""
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    print("🧪 Agent V2 Test Suite")
    print("Make sure the agent is running on localhost:8001 before running tests")
    print("Press Ctrl+C to stop tests")
    print()

    try:
        main()
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")