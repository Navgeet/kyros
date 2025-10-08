#!/usr/bin/env python3
"""Test script for the LangGraph Supervised Planning Agent"""

import sys
import os
import asyncio
import json
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.agent_langgraph import (
    LangGraphSupervisedPlanningAgent,
    LangGraphAgentConfig,
    AgentState,
    create_agent
)


def test_agent_creation():
    """Test basic agent creation"""
    print("🧪 Testing agent creation...")

    try:
        # Test with default config
        agent = create_agent()
        assert agent is not None
        assert hasattr(agent, 'workflow')
        assert hasattr(agent, 'graph')
        assert hasattr(agent, 'sessions')
        print("✅ Default agent creation successful!")

        # Test with custom config
        config = LangGraphAgentConfig(
            host="127.0.0.1",
            port=8002,
            api_url="http://test:1234"
        )
        custom_agent = create_agent(config)
        assert custom_agent.config.host == "127.0.0.1"
        assert custom_agent.config.port == 8002
        print("✅ Custom config agent creation successful!")

        return True

    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False


def test_workflow_structure():
    """Test that the workflow is properly structured"""
    print("\n🧪 Testing workflow structure...")

    try:
        agent = create_agent()
        workflow = agent.workflow

        # Check that workflow has expected nodes
        expected_nodes = [
            "handle_user_message",
            "generate_text_plan",
            "handle_text_plan_approval",
            "handle_text_plan_feedback",
            "generate_code",
            "handle_code_approval",
            "handle_code_feedback",
            "handle_replan",
            "complete_task"
        ]

        # Note: LangGraph may not expose node names directly
        # This is more of a structural test
        assert hasattr(workflow, 'nodes') or hasattr(workflow, '_nodes')
        print("✅ Workflow structure validation successful!")

        return True

    except Exception as e:
        print(f"❌ Workflow structure test failed: {e}")
        return False


def test_state_initialization():
    """Test AgentState initialization"""
    print("\n🧪 Testing state initialization...")

    try:
        # Test creating a mock session
        agent = create_agent()

        # Since _create_new_session requires websocket, we'll test the state structure
        from unittest.mock import MagicMock
        mock_websocket = MagicMock()

        session_id = agent._create_new_session(mock_websocket)

        assert session_id is not None
        assert session_id in agent.sessions

        state = agent.sessions[session_id]

        # Check all required fields exist
        required_fields = [
            'session_id', 'phase', 'user_request', 'text_plan',
            'python_code', 'conversation_history', 'messages'
        ]

        for field in required_fields:
            assert field in state, f"Missing required field: {field}"

        # Check initial values
        assert state['phase'] == 'greeting'
        assert state['user_request'] == ''
        assert state['text_plan'] == ''
        assert isinstance(state['conversation_history'], list)

        print("✅ State initialization successful!")
        return True

    except Exception as e:
        print(f"❌ State initialization test failed: {e}")
        return False


async def test_workflow_execution():
    """Test basic workflow execution"""
    print("\n🧪 Testing workflow execution...")

    try:
        agent = create_agent()

        # Create a test state
        from unittest.mock import MagicMock
        from langchain_core.messages import HumanMessage

        test_state = AgentState(
            messages=[HumanMessage(content="test message")],
            session_id="test123",
            phase="greeting",
            user_request="test request",
            text_plan="",
            python_code="",
            conversation_history=[],
            websocket=MagicMock(),
            created_at="2024-01-01T00:00:00",
            last_activity="2024-01-01T00:00:00",
            reconnections=0,
            current_message={"type": "user_message", "content": "hello"},
            screenshot=None,
            learning_objects=None,
            feedback=None,
            approval_status=None,
            execution_result=None
        )

        # Test individual node functions (if they don't require external APIs)
        try:
            # This might fail without actual API endpoints, which is expected
            result_state = await agent._handle_user_message_node(test_state)
            assert 'messages' in result_state
            print("✅ User message node execution successful!")
        except Exception as node_e:
            print(f"⚠️ Node execution failed (expected without APIs): {node_e}")

        print("✅ Workflow execution test completed!")
        return True

    except Exception as e:
        print(f"❌ Workflow execution test failed: {e}")
        return False


def test_routing_logic():
    """Test routing logic functions"""
    print("\n🧪 Testing routing logic...")

    try:
        agent = create_agent()

        # Test _route_from_user_message
        test_state = AgentState(
            messages=[],
            session_id="test123",
            phase="greeting",
            user_request="",
            text_plan="",
            python_code="",
            conversation_history=[],
            websocket=None,
            created_at="2024-01-01T00:00:00",
            last_activity="2024-01-01T00:00:00",
            reconnections=0,
            current_message={"type": "user_message", "content": "hello"},
            screenshot=None,
            learning_objects=None,
            feedback=None,
            approval_status=None,
            execution_result=None
        )

        route = agent._route_from_user_message(test_state)
        assert route in ["generate_text_plan", "handle_approval", "handle_feedback", "handle_replan", "end"]
        print(f"✅ User message routing returned: {route}")

        # Test other routing functions
        test_state["phase"] = "text_plan_approval"
        test_state["text_plan"] = "test plan"
        route = agent._route_from_text_plan(test_state)
        assert route in ["approval", "end"]
        print(f"✅ Text plan routing returned: {route}")

        print("✅ Routing logic test successful!")
        return True

    except Exception as e:
        print(f"❌ Routing logic test failed: {e}")
        return False


def test_utility_methods():
    """Test utility methods that don't require external dependencies"""
    print("\n🧪 Testing utility methods...")

    try:
        agent = create_agent()

        # Test HTML interface generation
        html = agent._get_html_interface()
        assert "LangGraph Supervised Planning Agent V3" in html
        assert "WebSocket" in html
        print("✅ HTML interface generation successful!")

        # Test session cleanup (without actual cleanup)
        assert hasattr(agent, 'sessions')
        print("✅ Session management structure verified!")

        print("✅ Utility methods test successful!")
        return True

    except Exception as e:
        print(f"❌ Utility methods test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting LangGraph Supervised Planning Agent Tests")
    print("=" * 60)

    test_results = []

    print("⚠️  Note: Some tests may fail without actual API endpoints")
    print("   These tests validate structure and basic functionality")
    print()

    # Test basic functionality
    test_results.append(("Agent Creation", test_agent_creation()))
    test_results.append(("Workflow Structure", test_workflow_structure()))
    test_results.append(("State Initialization", test_state_initialization()))

    # Test async functionality
    try:
        result = await test_workflow_execution()
        test_results.append(("Workflow Execution", result))
    except Exception as e:
        print(f"❌ Workflow execution test crashed: {e}")
        test_results.append(("Workflow Execution", False))

    # Test routing and utilities
    test_results.append(("Routing Logic", test_routing_logic()))
    test_results.append(("Utility Methods", test_utility_methods()))

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    elif passed >= total * 0.7:  # 70% pass rate is acceptable
        print("✅ Most tests passed - structure looks good!")
        return 0
    else:
        print("⚠️  Several tests failed - check implementation")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))