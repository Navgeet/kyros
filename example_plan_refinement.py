#!/usr/bin/env python3
"""
Example usage of the plan refinement script with various scenarios.
"""

from refine_plan import refine_plan_internlm

def demo_plan_refinement():
    """Demonstrate plan refinement with various examples."""
    
    examples = [
        {
            "user_request": "search google for restaurants near me",
            "original_plan": """
1. Open browser
2. Go to Google
3. Search for restaurants
4. Look at results
""",
        },
        {
            "user_request": "click on the search box and type hello",
            "original_plan": """
1. Find the search box
2. Click on it
3. Type hello
""",
        },
        {
            "user_request": "calculate 15 + 27 using the calculator app",
            "original_plan": """
1. Open calculator
2. Click numbers
3. Get result
""",
        },
    ]
    
    print("🔄 Plan Refinement Examples")
    print("=" * 60)
    
    for i, example in enumerate(examples, 1):
        print(f"\n📋 Example {i}: {example['user_request']}")
        print("-" * 40)
        print("Original Plan:")
        print(example['original_plan'])
        print("\nRefining...")
        print("-" * 40)
        
        try:
            refined_plan = refine_plan_internlm(
                original_plan=example['original_plan'],
                user_request=example['user_request'],
                include_screenshot=False  # Skip screenshot for demo
            )
            print("Refined Plan:")
            print(refined_plan)
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 60)

def demo_with_file_input():
    """Demonstrate refinement with file input."""
    
    # Create a sample plan file
    sample_plan = """
1. Open web browser
2. Navigate to search engine
3. Enter search query
4. Review search results
5. Click on relevant result
"""
    
    with open("sample_plan.txt", "w") as f:
        f.write(sample_plan)
    
    print("\n🗂️  File Input Demo")
    print("-" * 30)
    print(f"Sample plan written to: sample_plan.txt")
    print("Original plan:")
    print(sample_plan)
    
    try:
        with open("sample_plan.txt", "r") as f:
            original_plan = f.read().strip()
        
        refined_plan = refine_plan_internlm(
            original_plan=original_plan,
            user_request="search for python tutorials online",
            include_screenshot=False
        )
        
        print("\nRefined plan:")
        print(refined_plan)
        
        # Save refined plan
        with open("refined_plan.txt", "w") as f:
            f.write(refined_plan)
        print(f"\n💾 Refined plan saved to: refined_plan.txt")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 Plan Refinement Demo")
    print("This demo shows how to refine plans programmatically")
    print()
    
    # Run basic examples
    demo_plan_refinement()
    
    # Run file input demo  
    demo_with_file_input()
    
    print("\n✨ Demo completed!")
    print("\nTry the interactive mode:")
    print("  ./refine_plan.py")
    print("\nOr use command line:")
    print('  ./refine_plan.py --plan "1. Open app\\n2. Click button" --user-request "open calculator"')