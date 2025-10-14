#!/usr/bin/env python3
"""
Test script for BrowserAgent
"""
import asyncio
from agents.browser_agent import BrowserAgent
import config


def main():
    # Load config
    config_dict = config.load_config()

    # Create browser agent
    agent = BrowserAgent(config_dict=config_dict)

    # Test task: Navigate to a website and take a screenshot
    message = {
        "content": """
        Please do the following:
        1. Launch a browser
        2. Navigate to https://testsheepnz.github.io/BasicCalculator.html
        """,
        "max_iterations": 10
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
