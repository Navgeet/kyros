#!/usr/bin/env python3
"""Test script for the LangGraph planner"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.planner_langgraph import LangGraphPlanner, LangGraphPlannerConfig


def test_basic_planning():
    """Test basic planning functionality"""
    print("🧪 Testing basic planning functionality...")

    # Create planner instance
    config = LangGraphPlannerConfig(
        ollama_url="http://localhost:11434",
        vllm_url="http://localhost:11434",  # Using local LLM for testing
        max_iterations=3
    )

    planner = LangGraphPlanner(config)

    # Test simple user input
    user_input = "search google for restaurants near me"

    try:
        result = planner.generate_plan(user_input)

        print("✅ Plan generation successful!")
        print(f"Plan type: {result['type']}")
        print(f"Text plan: {result['text_plan']}")
        print(f"Generated code:\n{result['code']}")

        return True

    except Exception as e:
        print(f"❌ Plan generation failed: {e}")
        return False


def test_legacy_compatibility():
    """Test backwards compatibility with legacy methods"""
    print("\n🧪 Testing legacy compatibility...")

    config = LangGraphPlannerConfig()
    planner = LangGraphPlanner(config)

    try:
        # Test legacy generate_single_plan method
        result = planner.generate_single_plan(
            user_input="open calculator",
            conversation_history=[],
            screen_context="Desktop visible with taskbar"
        )

        print("✅ Legacy method compatibility successful!")
        print(f"Legacy result preview: {result[:200]}...")

        return True

    except Exception as e:
        print(f"❌ Legacy compatibility test failed: {e}")
        return False


def test_streaming_callback():
    """Test streaming callback functionality"""
    print("\n🧪 Testing streaming callback...")

    received_callbacks = []

    def test_callback(callback_type, content):
        received_callbacks.append((callback_type, content))
        print(f"📡 Callback received: {callback_type} - {content[:50]}...")

    config = LangGraphPlannerConfig(max_iterations=1)
    planner = LangGraphPlanner(config)
    planner.set_streaming_callback(test_callback)

    try:
        # This test might not work without actual LLM endpoint
        # but we can verify the callback was set
        assert planner.streaming_callback == test_callback
        print("✅ Streaming callback setup successful!")
        return True

    except Exception as e:
        print(f"❌ Streaming callback test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting LangGraph Planner Tests")
    print("=" * 50)

    test_results = []

    # Note: These tests may fail without actual LLM endpoints
    # They are primarily for structure validation

    print("⚠️  Note: Tests may fail without actual LLM endpoints running")
    print("   These tests validate structure and basic functionality")
    print()

    # Test basic functionality (will likely fail without LLM)
    try:
        test_results.append(("Basic Planning", test_basic_planning()))
    except Exception as e:
        print(f"❌ Basic planning test crashed: {e}")
        test_results.append(("Basic Planning", False))

    # Test legacy compatibility
    try:
        test_results.append(("Legacy Compatibility", test_legacy_compatibility()))
    except Exception as e:
        print(f"❌ Legacy compatibility test crashed: {e}")
        test_results.append(("Legacy Compatibility", False))

    # Test streaming callback
    test_results.append(("Streaming Callback", test_streaming_callback()))

    # Print summary
    print("\n" + "=" * 50)
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
    else:
        print("⚠️  Some tests failed (expected without LLM endpoints)")
        return 1


if __name__ == "__main__":
    exit(main())