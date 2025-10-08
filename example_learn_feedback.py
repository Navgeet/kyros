#!/usr/bin/env python3
"""
Example usage of the learn from feedback script with various scenarios.
"""

from learn_from_feedback import learn_from_feedback_internlm

def demo_learning_from_feedback():
    """Demonstrate learning from user feedback with various examples."""

    examples = [
        {
            "generated_plan": """
1. Open browser
2. Go to Google
3. Search for restaurants
4. Look at results
""",
            "user_feedback": "The plan is too vague. It doesn't specify which browser to use or how to actually perform the search. Also, it should include clicking on the search box before typing.",
        },
        {
            "generated_plan": """
1. Click on the calculator app icon
2. Click number 1
3. Click number 5
4. Click plus button
5. Click number 2
6. Click number 7
7. Click equals button
""",
            "user_feedback": "This worked perfectly! The step-by-step clicking approach was exactly what I needed. The plan was clear and executable.",
        },
        {
            "generated_plan": """
1. Take screenshot
2. Use hotkey Ctrl+C
3. Open notepad
4. Paste content
""",
            "user_feedback": "This doesn't make sense. You can't copy a screenshot with Ctrl+C unless something is already selected. The plan should use the screenshot tool to save an image file instead.",
        },
        {
            "generated_plan": """
1. Focus Chrome browser window
2. Open new tab using Ctrl+T
3. Type 'github.com' in address bar
4. Press Enter to navigate
5. Wait for page to load
6. Click on search box
7. Type 'python tutorials'
8. Press Enter to search
""",
            "user_feedback": "Great detailed plan! I especially like that you included the waiting step and specified the keyboard shortcuts. This worked exactly as expected.",
        },
    ]

    print("🧠 Learning from Feedback Examples")
    print("=" * 70)

    for i, example in enumerate(examples, 1):
        print(f"\n📋 Example {i}")
        print("-" * 50)
        print("Generated Plan:")
        print(example['generated_plan'])
        print("\nUser Feedback:")
        print(example['user_feedback'])
        print("\nAnalyzing feedback...")
        print("-" * 50)

        try:
            learning_insights = learn_from_feedback_internlm(
                generated_plan=example['generated_plan'],
                user_feedback=example['user_feedback']
            )
            print("Learning Insights:")
            print(learning_insights)
        except Exception as e:
            print(f"❌ Error: {e}")

        print("\n" + "=" * 70)

def demo_with_file_workflow():
    """Demonstrate learning workflow with file input/output."""

    print("\n🗂️  File Workflow Demo")
    print("-" * 40)

    # Create sample files
    sample_plan = """
1. Open web browser
2. Navigate to search engine
3. Enter search query
4. Review search results
5. Click on relevant result
"""

    sample_feedback = """
The plan is too generic. It should specify:
- Which browser to open (Chrome, Firefox, etc.)
- Which search engine to use (Google, Bing, etc.)
- How to actually open the browser (clicking icon, using hotkey, etc.)
- More specific steps for entering the search query (click search box first)
Also missing error handling if browser doesn't open or search fails.
"""

    # Write to files
    with open("sample_plan.txt", "w") as f:
        f.write(sample_plan)

    with open("sample_feedback.txt", "w") as f:
        f.write(sample_feedback)

    print("📝 Created sample files:")
    print("  - sample_plan.txt")
    print("  - sample_feedback.txt")

    print("\nPlan content:")
    print(sample_plan)
    print("Feedback content:")
    print(sample_feedback)

    try:
        # Read from files and analyze
        with open("sample_plan.txt", "r") as f:
            plan_content = f.read().strip()

        with open("sample_feedback.txt", "r") as f:
            feedback_content = f.read().strip()

        print("🔍 Analyzing feedback from files...")

        learning_insights = learn_from_feedback_internlm(
            generated_plan=plan_content,
            user_feedback=feedback_content
        )

        # Save insights to file
        with open("learning_insights.txt", "w") as f:
            f.write(learning_insights)

        print(f"\n💾 Learning insights saved to: learning_insights.txt")
        print("Insights preview:")
        print("-" * 30)
        print(learning_insights[:400] + "..." if len(learning_insights) > 400 else learning_insights)

    except Exception as e:
        print(f"❌ Error in workflow: {e}")

def demo_positive_vs_negative_feedback():
    """Compare learning from positive vs negative feedback."""

    print("\n➕➖ Positive vs Negative Feedback Analysis")
    print("-" * 55)

    base_plan = """
1. Focus window "Terminal"
2. Type command "ls -la"
3. Press Enter
4. Read the output
"""

    feedback_scenarios = [
        {
            "type": "Positive",
            "feedback": "Perfect! This worked exactly as expected. The plan was clear, specific, and executable. I like that you specified the exact command and included reading the output."
        },
        {
            "type": "Negative",
            "feedback": "This failed because Terminal wasn't open. The plan should first check if Terminal is running, and if not, open it using a hotkey or clicking the application icon."
        }
    ]

    for scenario in feedback_scenarios:
        print(f"\n🔍 {scenario['type']} Feedback Analysis:")
        print("-" * 35)

        try:
            learning_insights = learn_from_feedback_internlm(
                generated_plan=base_plan,
                user_feedback=scenario['feedback']
            )
            print(f"Feedback: {scenario['feedback']}")
            print(f"\nLearning Insights:")
            print(learning_insights)
        except Exception as e:
            print(f"❌ Error: {e}")

        print("-" * 55)

if __name__ == "__main__":
    print("🎯 Learning from Feedback Demo")
    print("This demo shows how to analyze user feedback to improve planning")
    print()

    # Run basic examples
    demo_learning_from_feedback()

    # Show file workflow
    demo_with_file_workflow()

    # Compare positive vs negative feedback
    demo_positive_vs_negative_feedback()

    print("\n✨ Demo completed!")
    print("\nTry the interactive mode:")
    print("  ./learn_from_feedback.py")
    print("\nOr use command line:")
    print('  ./learn_from_feedback.py --plan plan.txt --feedback "Missing steps"')
    print("\nComplete workflow:")
    print("  ./generate_text_plan.py \"search google\" > plan.txt")
    print("  # ... user tests the plan and provides feedback ...")
    print("  ./learn_from_feedback.py --plan plan.txt --feedback-file feedback.txt")