#!/usr/bin/env python3
"""
Test script for BrowserBossAgent (new architecture)
"""
import asyncio
from agents.browser_boss_agent import BrowserBossAgent
import config


def main():
    # Load config
    config_dict = config.load_config()

    # Create browser boss agent
    agent = BrowserBossAgent(config_dict=config_dict)

    # Test task: Navigate to a website and interact with elements
    message = {
        "content": """
        Please do the following:
        1. Launch a browser
        2. Navigate to https://testsheepnz.github.io/BasicCalculator.html
        3. Find the input field for the first number and enter "5"
        4. Find the input field for the second number and enter "3"
        5. Find and click the "Add" button
        6. Exit with success
        """,
        "max_iterations": 30
    }

    print("Starting BrowserAgent test...")
    print("=" * 80)

    result = agent.process_message(message)

    print("\n" + "=" * 80)
    print("Test completed!")
    print(f"Success: {result.get('success')}")
    print(f"Iterations: {result.get('iterations')}")

    if result.get('error'):
        print(f"Error: {result.get('error')}")

    if result.get('result'):
        print(f"Result: {result.get('result')}")

    print("\nHistory:")
    for i, item in enumerate(result.get('history', []), 1):
        print(f"\n{i}. Thought: {item.get('thought')}")
        print(f"   Action: {item.get('action')}")
        print(f"   Result: {item.get('result')}")


if __name__ == "__main__":
    main()
