#!/usr/bin/env python3
"""
Planner script that uses Claude Sonnet 4.5 to generate low-level instructions
from screenshots for GUI automation.

This script takes a screenshot and high-level task, then uses Claude to generate
a single, specific low-level instruction that can be executed by a grounding agent.
"""

import base64
import sys
import argparse
from typing import Dict, Any, Optional
from anthropic import Anthropic
from openai import OpenAI
from config import load_config


def encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """
    Encode image file to base64 string and determine media type from extension

    Returns:
        Tuple of (base64_data, media_type)
    """
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        encoded = base64.b64encode(image_data).decode('utf-8')

        # Determine image format from extension
        ext = image_path.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg']:
            media_type = 'image/jpeg'
        elif ext == 'png':
            media_type = 'image/png'
        elif ext == 'gif':
            media_type = 'image/gif'
        elif ext == 'webp':
            media_type = 'image/webp'
        else:
            # Default to png
            media_type = 'image/png'

        return encoded, media_type


def generate_instruction(
    screenshot_path: str,
    task: str,
    active_windows: Optional[str] = None,
    previous_actions: Optional[list] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    api_provider: str = "anthropic",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a low-level instruction using a vision-language model

    Args:
        screenshot_path: Path to screenshot image
        task: High-level task description
        active_windows: String listing active windows (from wmctrl -l)
        previous_actions: List of previous actions taken
        config_dict: Configuration dictionary
        api_provider: API provider to use ('anthropic' or 'openai')
        model: Model name (optional, uses default from provider)

    Returns:
        Dictionary with 'instruction' and 'reasoning' keys
    """
    # Load config if not provided
    if config_dict is None:
        config_dict = load_config()

    # Encode screenshot
    print(f"Encoding screenshot from: {screenshot_path}")
    screenshot_data, media_type = encode_image_to_base64(screenshot_path)
    print(f"Encoded image size: {len(screenshot_data)} chars, type: {media_type}")

    # Build context
    context_parts = [f"# Task\n\n{task}"]

    if previous_actions:
        context_parts.append("\n# Previous Actions")
        for i, action in enumerate(previous_actions, 1):
            context_parts.append(f"\n{i}. {action}")

    if active_windows:
        context_parts.append(f"\n# Active Windows\n\n```\n{active_windows}\n```")

    context_parts.append("\n# Current Screenshot\n\nRefer to the provided screenshot image.")

    context_text = "\n".join(context_parts)

    # System prompt for instruction generation
    system_prompt = """You are a GUI automation planner. Your job is to analyze screenshots and generate ONE specific, low-level instruction for the next action to accomplish the given task.

# Available Actions
- switch to a window
- click/double-click/right-click etc
- type/hotkey/press key etc
- wait/exit

# Guidelines

- Generate ONLY ONE specific instruction at a time
- Be precise about WHAT to interact with and WHERE it is located
- Describe the visual element clearly (e.g., "Firefox icon in the taskbar", "search box at the top of the page")
- Use natural language descriptions of locations, not coordinates
- Consider the mouse (red dot) position, if you need to scroll, first move the mouse to the scrollable element
- If the task is complete, return instruction: "EXIT: [reason]"
- Don't generate the same instruction again and again

# Output Format

Your response should be in this format:

## Reasoning
[Brief explanation of why this is the next logical step]

## Instruction
[Single, clear, actionable instruction]

# Examples

## Reasoning
The task requires opening Firefox. I can see the Firefox icon in the taskbar at the bottom of the screen.

## Instruction
Click on the Firefox icon in the taskbar at the bottom of the screen

"""

    api_provider = 'novita'
    model = 'qwen/qwen3-vl-235b-a22b-thinking'

    # Call appropriate API based on provider
    if api_provider == "anthropic":
        # Get Anthropic config
        anthropic_config = config_dict.get('anthropic', {})
        api_key = anthropic_config.get('api_key')

        if not api_key:
            raise ValueError("Anthropic API key not found in config")

        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)

        # Use default model if not specified
        if model is None:
            model = "claude-sonnet-4-5"

        # Create message with image
        message = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.5,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": context_text
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": screenshot_data
                            }
                        }
                    ]
                }
            ]
        )

        # Parse response
        response_text = message.content[0].text

    else:
        # Get OpenAI config
        config = config_dict.get(api_provider, {})
        api_key = config.get('api_key')
        base_url = config.get('base_url')

        if not api_key:
            raise ValueError(f"{api_provider} API key not found in config")

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key, base_url=base_url)

        # Use default model if not specified
        if model is None:
            model = "gpt-4o"

        print(f"Using API provider: {api_provider}")
        print(f"Using model: {model}")
        print(f"Base URL: {base_url}")
        print(f"Context length: {len(context_text)} chars")
        print(f"Image size: {len(screenshot_data)} chars")

        # Create message with image (OpenAI format)
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=1000,
                temperature=0.5,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": context_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{screenshot_data}"
                                }
                            }
                        ]
                    }
                ]
            )

            # Parse response
            response_text = response.choices[0].message.content
        except Exception as e:
            print(f"API Error: {e}")
            print(f"Request details - model: {model}, max_tokens: 1000, temp: 0.5")
            raise


    # Extract reasoning and instruction
    reasoning = ""
    instruction = ""

    lines = response_text.strip().split('\n')
    current_section = None

    for line in lines:
        if line.strip().startswith('## Reasoning'):
            current_section = 'reasoning'
        elif line.strip().startswith('## Instruction'):
            current_section = 'instruction'
        elif current_section == 'reasoning' and line.strip():
            reasoning += line.strip() + " "
        elif current_section == 'instruction' and line.strip():
            instruction += line.strip() + " "

    return {
        'instruction': instruction.strip(),
        'reasoning': reasoning.strip(),
        'raw_response': response_text
    }


def main():
    """Command-line interface for the planner"""
    parser = argparse.ArgumentParser(
        description='Generate low-level GUI instructions from screenshots using vision-language models'
    )
    parser.add_argument('screenshot', help='Path to screenshot image')
    parser.add_argument('task', help='High-level task description')
    parser.add_argument('--windows', help='Active windows list (from wmctrl -l)')
    parser.add_argument('--previous', nargs='+', help='List of previous actions')
    parser.add_argument('--api-provider', default='anthropic', choices=['anthropic', 'openai', 'novita', 'internlm'],
                        help='API provider to use (default: anthropic)')
    parser.add_argument('--model', help='Model name (default: claude-sonnet-4-5 for anthropic, gpt-4o for openai)')

    args = parser.parse_args()

    try:
        result = generate_instruction(
            screenshot_path=args.screenshot,
            task=args.task,
            active_windows=args.windows,
            previous_actions=args.previous,
            api_provider=args.api_provider,
            model=args.model
        )

        print("=" * 80)
        print("REASONING:")
        print(result['reasoning'])
        print("\n" + "=" * 80)
        print("INSTRUCTION:")
        print(result['instruction'])
        print("=" * 80)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
