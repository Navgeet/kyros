#!/usr/bin/env python3
"""
Demo script for the Conversational Planning Agent V2
Shows example usage and capabilities
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any

class AgentV2Demo:
    """Demo client for the V2 agent."""

    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.websocket = None

    async def connect(self):
        """Connect to the agent."""
        uri = f"ws://{self.host}:{self.port}/ws"
        print(f"🔌 Connecting to Agent V2 at {uri}...")

        try:
            self.websocket = await websockets.connect(uri)
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("Make sure the agent is running with: python start_agent_v2.py")
            return False

    async def disconnect(self):
        """Disconnect from the agent."""
        if self.websocket:
            await self.websocket.close()
            print("👋 Disconnected from agent")

    async def send_message(self, message: Dict[str, Any]):
        """Send a message to the agent."""
        if not self.websocket:
            return

        await self.websocket.send(json.dumps(message))
        print(f"📤 You: {message.get('content', message.get('type'))}")

    async def receive_message(self) -> Dict[str, Any]:
        """Receive and display a message from the agent."""
        if not self.websocket:
            return {}

        try:
            message_str = await self.websocket.recv()
            message = json.loads(message_str)

            msg_type = message.get('type')
            if msg_type == 'agent_message':
                print(f"🤖 Agent: {message.get('message')}")
            elif msg_type == 'text_plan_review':
                print(f"🤖 Agent: {message.get('message')}")
                print("📋 Generated Plan:")
                print("-" * 40)
                print(message.get('plan'))
                print("-" * 40)
            elif msg_type == 'code_review':
                print(f"🤖 Agent: {message.get('message')}")
                print("🐍 Generated Code:")
                print("-" * 40)
                print(message.get('code'))
                print("-" * 40)
            elif msg_type == 'status':
                print(f"⏳ Status: {message.get('message')}")
            elif msg_type == 'completion':
                print(f"🎉 Agent: {message.get('message')}")
            elif msg_type == 'feedback_request':
                print(f"💭 Agent: {message.get('message')}")
            elif msg_type == 'connection':
                print(f"🤖 Agent: {message.get('message')}")

            return message
        except Exception as e:
            print(f"❌ Error receiving message: {e}")
            return {}

    async def demo_complete_workflow(self):
        """Demonstrate a complete workflow with approval."""
        print("\n🎬 Demo: Complete Workflow with Approval")
        print("=" * 50)

        if not await self.connect():
            return

        # Wait for welcome
        await self.receive_message()
        await asyncio.sleep(1)

        # Send request
        await self.send_message({
            "type": "user_message",
            "content": "Create a simple temperature converter that converts between Celsius and Fahrenheit"
        })

        # Receive text plan
        await self.receive_message()  # status
        await self.receive_message()  # plan review
        await asyncio.sleep(2)

        print("\n✅ Approving the text plan...")
        await self.send_message({"type": "approval", "approved": True})

        # Receive code
        await self.receive_message()  # status
        await self.receive_message()  # code review
        await asyncio.sleep(2)

        print("\n✅ Approving the generated code...")
        await self.send_message({"type": "approval", "approved": True})

        # Receive completion
        await self.receive_message()  # completion

        await self.disconnect()

    async def demo_feedback_workflow(self):
        """Demonstrate the feedback and improvement workflow."""
        print("\n🎬 Demo: Feedback and Improvement Workflow")
        print("=" * 50)

        if not await self.connect():
            return

        # Wait for welcome
        await self.receive_message()
        await asyncio.sleep(1)

        # Send request
        await self.send_message({
            "type": "user_message",
            "content": "Create a simple todo list application"
        })

        # Receive text plan
        await self.receive_message()  # status
        await self.receive_message()  # plan review
        await asyncio.sleep(2)

        print("\n❌ Rejecting the plan to request improvements...")
        await self.send_message({"type": "approval", "approved": False})

        # Receive feedback request
        await self.receive_message()  # feedback request
        await asyncio.sleep(1)

        print("\n💭 Providing feedback for improvement...")
        await self.send_message({
            "type": "feedback",
            "content": "Please add functionality to mark tasks as completed, set priorities, and save tasks to a file"
        })

        # Receive improved plan
        await self.receive_message()  # status
        await self.receive_message()  # improved plan
        await asyncio.sleep(2)

        print("\n✅ Approving the improved plan...")
        await self.send_message({"type": "approval", "approved": True})

        # Continue with code generation...
        await self.receive_message()  # status
        code_msg = await self.receive_message()  # code review

        if code_msg.get('type') == 'code_review':
            await asyncio.sleep(2)
            print("\n✅ Approving the generated code...")
            await self.send_message({"type": "approval", "approved": True})
            await self.receive_message()  # completion

        await self.disconnect()

    async def demo_replanning_workflow(self):
        """Demonstrate the replanning workflow."""
        print("\n🎬 Demo: Replanning Workflow")
        print("=" * 50)

        if not await self.connect():
            return

        # Wait for welcome
        await self.receive_message()
        await asyncio.sleep(1)

        # Send request
        await self.send_message({
            "type": "user_message",
            "content": "Help me build a web scraper"
        })

        # Receive text plan
        await self.receive_message()  # status
        await self.receive_message()  # plan review
        await asyncio.sleep(2)

        print("\n🔄 Requesting a completely new plan...")
        await self.send_message({"type": "replan", "plan_type": "text"})

        # Receive new plan
        await self.receive_message()  # status
        await self.receive_message()  # new plan
        await asyncio.sleep(2)

        print("\n✅ Approving the new plan...")
        await self.send_message({"type": "approval", "approved": True})

        # Continue with code generation...
        await self.receive_message()  # status
        code_msg = await self.receive_message()  # code review

        if code_msg.get('type') == 'code_review':
            await asyncio.sleep(2)
            print("\n🔄 Requesting new code generation...")
            await self.send_message({"type": "replan", "plan_type": "code"})

            # Receive new code
            await self.receive_message()  # status
            await self.receive_message()  # new code
            await asyncio.sleep(2)

            print("\n✅ Approving the new code...")
            await self.send_message({"type": "approval", "approved": True})
            await self.receive_message()  # completion

        await self.disconnect()

async def run_demos():
    """Run all demo scenarios."""
    demo = AgentV2Demo()

    print("🎬 Conversational Planning Agent V2 - Demo Suite")
    print("=" * 60)
    print("This demo shows the agent's capabilities:")
    print("1. Complete workflow with approvals")
    print("2. Feedback and improvement workflow")
    print("3. Replanning at different stages")
    print("=" * 60)

    # Demo 1: Complete workflow
    await demo.demo_complete_workflow()
    await asyncio.sleep(3)

    # Demo 2: Feedback workflow
    await demo.demo_feedback_workflow()
    await asyncio.sleep(3)

    # Demo 3: Replanning workflow
    await demo.demo_replanning_workflow()

    print("\n🎉 All demos completed!")
    print("\nTo interact with the agent manually, open: http://localhost:8001")

def main():
    """Main function."""
    print("🎬 Agent V2 Demo")
    print("Make sure the agent is running before starting the demo:")
    print("  python start_agent_v2.py")
    print()

    try:
        asyncio.run(run_demos())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")

if __name__ == "__main__":
    main()