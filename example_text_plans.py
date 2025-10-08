#!/usr/bin/env python3
"""
Example usage of the text plan generator with various prompts.
"""

from generate_text_plan import generate_text_plan

def demo_text_plan_generation():
    """Demonstrate text plan generation with various examples."""
    
    examples = [
        "search google for restaurants near me",
        "open a new browser tab and navigate to github.com", 
        "calculate 15 + 27",
        "take a screenshot and save it",
        "find the search box on the current page and click it"
    ]
    
    print("🎯 Text Plan Generation Examples")
    print("=" * 50)
    
    for i, prompt in enumerate(examples, 1):
        print(f"\n📋 Example {i}: {prompt}")
        print("-" * 30)
        
        try:
            text_plan = generate_text_plan(prompt)
            print(text_plan)
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    demo_text_plan_generation()