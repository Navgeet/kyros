#!/usr/bin/env python3
"""
Test script for GUI Agent

This script allows you to test the GUI agent in isolation without the full multi-agent system.
You can provide a task via command line or interactively.

Usage:
    python test_gui_agent.py --task "Click on Firefox and open google.com"
    python test_gui_agent.py  # Interactive mode
"""

import argparse
import asyncio
import sys
from agents.gui_agent import GUIAgent
import config
import json
import time


def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)


def print_event(event_type: str, data: dict):
    """Pretty print WebSocket events"""
    # Don't print separator for streaming chunks
    if event_type not in ["llm_content_chunk", "llm_reasoning_chunk"]:
        print_separator("-")
        print(f"EVENT: {event_type}")

    if event_type == "screenshot":
        print(f"  Active Windows:")
        windows = data.get("active_windows", "N/A")
        for line in windows.split('\n')[:5]:  # Show first 5 windows
            print(f"    {line}")
        print(f"  Screenshot: [captured]")

    elif event_type == "action_execute":
        print(f"  Iteration: {data.get('iteration')}")
        print(f"  Action:")
        action_lines = data.get('action', '').split('\n')
        for line in action_lines:
            print(f"    {line}")

    elif event_type == "action_result":
        result = data.get('result', {})
        print(f"  Exit Code: {result.get('exitCode', 'N/A')}")
        if result.get('stdout'):
            print(f"  Stdout: {result.get('stdout')}")
        if result.get('stderr'):
            print(f"  Stderr: {result.get('stderr')}")

    elif event_type == "action_verification":
        verification = data.get('verification', '')
        print(f"  Verification: {verification[:200]}...")  # First 200 chars

    elif event_type == "llm_call_start":
        print(f"  Model: {data.get('model')}")
        print(f"  Temperature: {data.get('temperature')}")
        print(f"  Max Tokens: {data.get('max_tokens')}")
        messages = data.get('messages', [])
        print(f"  Messages: {len(messages)} message(s)")

        # Print message content (eliding images)
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')

            print(f"\n  Message {i} ({role}):")

            if isinstance(content, str):
                # Simple text content
                print(f"    {content}")
            elif isinstance(content, list):
                # Multi-part content (text + images)
                for part in content:
                    if isinstance(part, dict):
                        part_type = part.get('type', 'unknown')
                        if part_type == 'text':
                            text = part.get('text', '')
                            print(f"    [text]: {text}")
                        elif part_type == 'image_url':
                            print(f"    [image]: [IMAGE_DATA_ELIDED]")
                        else:
                            print(f"    [{part_type}]: {part}")
        print()  # Add blank line after messages

    elif event_type == "llm_content_chunk":
        # Print content chunks inline
        content = data.get('content', '')
        print(content, end='', flush=True)

    elif event_type == "llm_reasoning_chunk":
        # Print reasoning chunks in gray (if terminal supports it)
        content = data.get('content', '')
        print(f"\033[90m{content}\033[0m", end='', flush=True)

    elif event_type == "llm_call_end":
        print()  # New line after streaming
        print(f"  Response length: {len(data.get('response', ''))} chars")
        if data.get('reasoning'):
            print(f"  Reasoning length: {len(data.get('reasoning', ''))} chars")


def websocket_callback(event: dict):
    """Callback to handle WebSocket events from the agent"""
    event_type = event.get("type")
    data = event.get("data", {})

    # Skip content chunks if verbose mode is off
    if event_type in ["llm_content_chunk", "llm_reasoning_chunk"]:
        print_event(event_type, data)
    else:
        print_event(event_type, data)


def main():
    parser = argparse.ArgumentParser(description="Test GUI Agent")
    parser.add_argument("--task", type=str, help="Task for the GUI agent to perform")
    parser.add_argument("--max-iterations", type=int, default=20, help="Maximum iterations (default: 20)")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")

    args = parser.parse_args()

    # Get task from args or prompt user
    task = args.task
    if not task:
        print("Enter a task for the GUI agent (e.g., 'Open Firefox and navigate to google.com'):")
        task = input("> ").strip()
        if not task:
            print("No task provided. Exiting.")
            return

    print_separator()
    print(f"TASK: {task}")
    print_separator()

    # Load configuration
    try:
        config_dict = config.load_config(args.config)
        print(f"Configuration loaded from {args.config}")
    except Exception as e:
        print(f"Warning: Failed to load config: {e}")
        print("Using environment variables for API configuration")
        config_dict = None


    time.sleep(2)

    # Create GUI agent
    print("Creating GUI agent...")
    agent = GUIAgent(
        websocket_callback=websocket_callback,
        config_dict=config_dict
    )

    print(f"Agent created: {agent.agent_id}")
    print(f"Model: {agent.model}")
    print(f"Base URL: {agent.base_url}")
    print_separator()

    # Process the task
    print("Starting task execution...")
    print_separator()

    try:
        result = agent.process_message({
            "content": task,
            "max_iterations": args.max_iterations
        })

        print_separator()
        print("TASK COMPLETED")
        print_separator()
        print(f"Success: {result.get('success')}")
        print(f"Iterations: {result.get('iterations')}")
        print(f"Total actions: {len(result.get('history', []))}")

        # Print action history summary
        print("\nAction History:")
        for i, item in enumerate(result.get('history', []), 1):
            action = item.get('action', '')
            # Get first line of action (usually the comment)
            first_line = action.split('\n')[0] if action else ''
            print(f"  {i}. {first_line[:80]}")

        print_separator()

    except KeyboardInterrupt:
        print("\n\nTask interrupted by user")
        print_separator()
    except Exception as e:
        print_separator()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print_separator()
        sys.exit(1)


if __name__ == "__main__":
    main()
