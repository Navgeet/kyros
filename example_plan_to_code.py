#!/usr/bin/env python3
"""
Example usage of the plan-to-code conversion script.
Demonstrates converting text plans to executable Python code.
"""

from plan_to_code import plan_to_code_internlm

def demo_plan_to_code_conversion():
    """Demonstrate plan to code conversion with various examples."""
    
    examples = [
        {
            "user_request": "calculate 15 + 27",
            "text_plan": """
1. Use the add function to calculate 15 + 27
2. Print the result
""",
        },
        {
            "user_request": "open browser and search google",
            "text_plan": """
1. Focus on the Chrome browser window
2. Open a new tab using Ctrl+T
3. Type "google.com" in the address bar
4. Press Enter to navigate
5. Click on the search box
6. Type "restaurants near me"
7. Press Enter to search
""",
        },
        {
            "user_request": "click on the login button",
            "text_plan": """
1. Look at the screen to find the login button
2. Click on the login button coordinates
3. Wait for the page to load
""",
        },
        {
            "user_request": "take a screenshot",
            "text_plan": """
1. Use the screenshot tool to capture current screen
2. Save it with a timestamp name
""",
        },
    ]
    
    print("🐍 Plan to Code Conversion Examples")
    print("=" * 70)
    
    for i, example in enumerate(examples, 1):
        print(f"\n📋 Example {i}: {example['user_request']}")
        print("-" * 50)
        print("Text Plan:")
        print(example['text_plan'])
        print("\nConverting to Python code...")
        print("-" * 50)
        
        try:
            python_code = plan_to_code_internlm(
                text_plan=example['text_plan'],
                user_request=example['user_request'],
                include_screenshot=False  # Skip screenshot for demo
            )
            print("Generated Python Code:")
            print(python_code)
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 70)

def demo_with_screenshot():
    """Demonstrate code generation with screenshot for click coordinates."""
    
    print("\n🖼️  Screenshot-Based Code Generation Demo")
    print("-" * 50)
    
    click_plan = """
1. Look at the current screen
2. Find the search input field
3. Click on the search input field
4. Type "hello world"
5. Press Enter
"""
    
    print("Text Plan:")
    print(click_plan)
    print("\nThis demo would normally:")
    print("1. Take a screenshot of current screen")  
    print("2. Use computer vision to locate UI elements")
    print("3. Generate precise click coordinates")
    print("4. Create executable Python code with tools.click(x, y)")
    print("\nExample output would be:")
    print("""
```python
import kyros.tools as tools

def find_and_click_search():
    # Click on search field at detected coordinates
    tools.click(0.4089, 0.6493)

def type_search_query():
    # Type the search query
    tools.type("hello world")
    
def submit_search():
    # Press Enter to submit
    tools.hotkey("enter")

# Execute the steps
find_and_click_search()
type_search_query()  
submit_search()
```
""")

def demo_file_workflow():
    """Demonstrate complete workflow with file input/output."""
    
    print("\n🗂️  Complete File Workflow Demo")
    print("-" * 40)
    
    # Create sample files
    sample_plan = """
1. Open the calculator application
2. Click on the number 5
3. Click on the plus (+) button
4. Click on the number 3
5. Click on the equals (=) button
6. Read the result from the display
"""
    
    with open("calculator_plan.txt", "w") as f:
        f.write(sample_plan)
    
    print("📝 Created sample plan file: calculator_plan.txt")
    print("Plan content:")
    print(sample_plan)
    
    try:
        # Read plan from file
        with open("calculator_plan.txt", "r") as f:
            plan_content = f.read().strip()
        
        print("Converting plan to Python code...")
        
        python_code = plan_to_code_internlm(
            text_plan=plan_content,
            user_request="calculate 5 + 3 using calculator app",
            include_screenshot=False
        )
        
        # Save generated code
        with open("calculator_automation.py", "w") as f:
            f.write(python_code)
        
        print(f"\n💾 Generated code saved to: calculator_automation.py")
        print("Generated code preview:")
        print("-" * 30)
        print(python_code[:300] + "..." if len(python_code) > 300 else python_code)
        
    except Exception as e:
        print(f"❌ Error in workflow: {e}")

if __name__ == "__main__":
    print("🎯 Plan to Code Conversion Demo")
    print("This demo shows how to convert text plans to executable Python code")
    print()
    
    # Run basic examples
    demo_plan_to_code_conversion()
    
    # Show screenshot capabilities
    demo_with_screenshot()
    
    # Show file workflow
    demo_file_workflow()
    
    print("\n✨ Demo completed!")
    print("\nTry the interactive mode:")
    print("  ./plan_to_code.py")
    print("\nOr use command line:")
    print('  ./plan_to_code.py --plan "1. Click button\\n2. Type text" --validate')
    print("\nComplete workflow:")
    print("  ./generate_text_plan.py \"search google\" > plan.txt")
    print("  ./refine_plan.py --plan-file plan.txt > refined_plan.txt") 
    print("  ./plan_to_code.py --plan-file refined_plan.txt --output automation.py")