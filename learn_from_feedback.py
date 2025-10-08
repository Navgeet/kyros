#!/usr/bin/env python3
"""
Script to learn from user feedback on generated plans.
Takes a generated plan and user feedback to improve future planning.
"""

import sys
import argparse
import json
import os
from typing import Optional
import requests


def learn_from_feedback_internlm(generated_plan: str, user_feedback: str,
                                api_url: str = "http://localhost:23333",
                                api_key: str = None) -> str:
    """
    Learn from user feedback on a generated plan using InternLM API.

    Args:
        generated_plan: The plan that was generated
        user_feedback: User's feedback on the plan
        api_url: InternLM API URL
        api_key: API key for authentication

    Returns:
        Learning insights and improvement suggestions as a string
    """
    try:
        # Prepare the learning prompt
        learning_prompt = f"""
You are a learning system that analyzes user feedback on generated plans to generate a knowledge base entry.

Output format:
{{"title": "foo", "summary": "around 50 words", "content": "lorem ipsum"}}

Available tools:
- tools.focus_window(name): Focus window by name (e.g., "chrome", "firefox")
- tools.hotkey(keys): Send keyboard shortcuts (e.g., "ctrl+t", "ctrl+w", "enter", "escape")
- tools.type(text): Type the specified text
- tools.click(x, y): Click at coordinates (use floats 0-1 for relative positioning)
- tools.move_to(x, y): Move mouse to coordinates (use floats 0-1 for relative positioning)
- tools.query_screen(query): Ask questions about screen content
- tools.run_shell_command(args): Execute shell commands
- tools.add(a, b): Add two numbers

Rules:
1. Be concise.
2. content field should also contain code.


GENERATED PLAN:
{generated_plan}

USER FEEDBACK:
{user_feedback}

"""

        # Prepare API request
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        data = {
            "model": "internvl3.5-241b-a28b",
            "messages": [
                {
                    "role": "user",
                    "content": learning_prompt
                }
            ],
            "stream": False,
            "temperature": 0.1  # Lower temperature for more consistent analysis
        }

        # Make API request
        response = requests.post(f"{api_url}/v1/chat/completions",
                               headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        result = response.json()

        if 'choices' not in result or not result['choices']:
            raise Exception("No response from API")

        learning_insights = result['choices'][0]['message']['content']
        return learning_insights.strip()

    except Exception as e:
        raise Exception(f"Failed to analyze feedback: {str(e)}")


def save_learning_to_file(learning_insights: str, output_file: str = None) -> str:
    """Save learning insights to a file with timestamp."""
    import datetime

    if not output_file:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"learning_insights_{timestamp}.txt"

    with open(output_file, 'w') as f:
        f.write(learning_insights)

    return output_file


def interactive_learning():
    """Interactive mode for learning from feedback."""
    print("🧠 Interactive Learning Mode")
    print("=" * 50)
    print("Enter the generated plan and user feedback to analyze and learn.")
    print("Type 'exit' at any prompt to quit.\n")

    while True:
        print("📋 Enter the generated plan:")
        plan_lines = []
        while True:
            try:
                line = input()
                if line.lower() == 'exit':
                    return
                if line == "":  # Empty line ends input
                    break
                plan_lines.append(line)
            except (EOFError, KeyboardInterrupt):
                return

        if not plan_lines:
            print("No plan entered. Try again or type 'exit'.")
            continue

        generated_plan = "\n".join(plan_lines)

        print("\n💬 Enter the user feedback:")
        feedback_lines = []
        while True:
            try:
                line = input()
                if line.lower() == 'exit':
                    return
                if line == "":  # Empty line ends input
                    break
                feedback_lines.append(line)
            except (EOFError, KeyboardInterrupt):
                return

        if not feedback_lines:
            print("No feedback entered. Try again or type 'exit'.")
            continue

        user_feedback = "\n".join(feedback_lines)

        print("\n🔍 Analyzing feedback...")
        try:
            learning_insights = learn_from_feedback_internlm(generated_plan, user_feedback)
            print("\n" + "="*60)
            print("📚 LEARNING INSIGHTS")
            print("="*60)
            print(learning_insights)
            print("="*60)

            # Ask if user wants to save
            save_prompt = input("\n💾 Save insights to file? (y/n): ").strip().lower()
            if save_prompt in ['y', 'yes']:
                output_file = save_learning_to_file(learning_insights)
                print(f"✅ Saved to: {output_file}")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("\n" + "-"*50)


def main():
    parser = argparse.ArgumentParser(description="Learn from user feedback on generated plans")
    parser.add_argument("--plan", help="File containing the generated plan")
    parser.add_argument("--feedback", help="User feedback text")
    parser.add_argument("--feedback-file", help="File containing the user feedback")
    parser.add_argument("--output", help="Output file for learning insights")
    parser.add_argument("--api-url", default="http://localhost:23333",
                       help="InternLM API URL")
    parser.add_argument("--api-key", help="API key for authentication")

    args = parser.parse_args()

    # If no arguments provided, start interactive mode
    if not any([args.plan, args.feedback, args.feedback_file]):
        interactive_learning()
        return

    # Get plan from file
    if args.plan:
        try:
            with open(args.plan, 'r') as f:
                generated_plan = f.read().strip()
        except FileNotFoundError:
            print(f"❌ Plan file not found: {args.plan}")
            sys.exit(1)
    else:
        print("❌ Must provide --plan (file path)")
        sys.exit(1)

    # Get feedback from file or argument
    if args.feedback_file:
        try:
            with open(args.feedback_file, 'r') as f:
                user_feedback = f.read().strip()
        except FileNotFoundError:
            print(f"❌ Feedback file not found: {args.feedback_file}")
            sys.exit(1)
    elif args.feedback:
        user_feedback = args.feedback
    else:
        print("❌ Must provide either --feedback or --feedback-file")
        sys.exit(1)

    try:
        print("🔍 Analyzing feedback...")
        learning_insights = learn_from_feedback_internlm(
            generated_plan, user_feedback,
            api_url=args.api_url, api_key=args.api_key
        )

        if args.output:
            output_file = save_learning_to_file(learning_insights, args.output)
            print(f"✅ Learning insights saved to: {output_file}")
        else:
            print("\n📚 LEARNING INSIGHTS")
            print("="*60)
            print(learning_insights)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
