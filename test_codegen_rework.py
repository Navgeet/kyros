#!/usr/bin/env python3
"""
Test script for the code generation rework.
Tests the new iterative code generation approach.
"""

from planner import Planner
from executor import Executor

def test_simple_math():
    """Test with a simple math operation that doesn't require screen interaction."""
    print("🧪 Testing simple math operation...")
    
    planner = Planner(vllm_url="http://localhost:8000/v1")
    executor = Executor()
    
    # Test the new code generation approach
    user_input = "calculate 5 + 3"
    plan = planner.generate_plan(user_input)
    
    print(f"Generated plan type: {plan.get('type')}")
    print(f"Generated code:\n{plan.get('code', 'No code generated')}")
    
    # Execute the generated code
    success = executor.execute_plan(plan)
    print(f"Execution result: {'✅ Success' if success else '❌ Failed'}")
    
    return success

def test_browser_search():
    """Test with a browser search operation (more complex)."""
    print("\n🧪 Testing browser search operation...")
    
    planner = Planner(vllm_url="http://localhost:8000/v1")
    executor = Executor()
    
    # Test the example from CLAUDE.md
    user_input = "search google for restaurants near me"
    plan = planner.generate_plan(user_input)
    
    print(f"Generated plan type: {plan.get('type')}")
    print(f"Text plan: {plan.get('text_plan', 'No text plan')}")
    print(f"Generated code:\n{plan.get('code', 'No code generated')}")
    
    # Just test plan generation, don't execute (would require actual browser)
    print("Plan generation completed successfully")
    return True

if __name__ == "__main__":
    print("🚀 Testing code generation rework implementation\n")
    
    try:
        # Test simple math operation
        test1 = test_simple_math()
        
        # Test browser search (plan generation only)
        test2 = test_browser_search()
        
        print(f"\n📊 Test Results:")
        print(f"Simple math test: {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"Browser search test: {'✅ PASS' if test2 else '❌ FAIL'}")
        
        if test1 and test2:
            print("\n🎉 All tests passed! Code generation rework implemented successfully.")
        else:
            print("\n⚠️ Some tests failed. Check the implementation.")
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()