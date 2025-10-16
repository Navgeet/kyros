"""Utility functions for the multi-agent system"""
from typing import List, Dict, Any
from anthropic import Anthropic
import os
import json
from datetime import datetime


def compact_context(
    content: List[Dict[str, Any]],
    task: str,
    config_dict: Dict[str, Any] = None,
    websocket_callback = None,
    agent_id: str = None,
    agent_name: str = None
) -> str:
    """
    Compact context using configured LLM

    Args:
        content: List of context items to compact (e.g., previous responses or actions)
        task: The current task for context
        config_dict: Configuration dictionary for API credentials and compaction settings
        websocket_callback: Optional callback for WebSocket updates
        agent_id: Agent ID for logging
        agent_name: Agent name for logging

    Returns:
        Compacted context as a string
    """
    # Get compaction config
    compaction_config = config_dict.get('compaction', {}) if config_dict else {}
    model = compaction_config.get('model', 'claude-sonnet-4-5-20250929')
    api_provider = compaction_config.get('api_provider', 'anthropic')
    max_tokens = compaction_config.get('max_tokens', 1000)

    # Get API key based on provider
    api_key = None
    if config_dict and api_provider in config_dict:
        api_key = config_dict[api_provider].get('api_key')
    if not api_key:
        api_key = os.environ.get(f'{api_provider.upper()}_API_KEY')

    if not api_key:
        # If no API key, just return a truncated version
        result = str(content[-5:])  # Return last 5 items
        return result

    # Create Anthropic client (only Anthropic supported for now)
    client = Anthropic(api_key=api_key)

    # Build compaction prompt
    prompt = f"""Task: {task}

Context to compact:
{content}

Please provide a concise summary of the above context, preserving all critical information needed to continue the task. Focus on:
1. Key actions taken or responses provided
2. Important results or outcomes
3. Current state or progress
4. Any errors or issues encountered

Keep the summary under 500 words."""

    messages = [{
        "role": "user",
        "content": prompt
    }]

    # Log input to file
    _log_to_file({
        "event": "input",
        "purpose": "context_compaction",
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages
    }, agent_id, agent_name)

    # Send LLM call start event
    if websocket_callback:
        websocket_callback({
            "type": "llm_call_start",
            "data": {
                "purpose": "context_compaction",
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens
            }
        })

    # Call LLM for compaction with streaming
    compacted_text = ""

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        messages=messages
    ) as stream:
        for text in stream.text_stream:
            compacted_text += text
            # Send content chunks
            if websocket_callback:
                websocket_callback({
                    "type": "llm_content_chunk",
                    "data": {
                        "content": text
                    }
                })

    # Log output to file
    _log_to_file({
        "event": "output",
        "purpose": "context_compaction",
        "response": compacted_text,
        "original_word_count": count_words(str(content)),
        "compacted_word_count": count_words(compacted_text)
    }, agent_id, agent_name)

    # Send LLM call end event
    if websocket_callback:
        websocket_callback({
            "type": "llm_call_end",
            "data": {
                "purpose": "context_compaction",
                "response": compacted_text,
                "original_word_count": count_words(str(content)),
                "compacted_word_count": count_words(compacted_text)
            }
        })

    return compacted_text


def _log_to_file(log_data: Dict[str, Any], agent_id: str = None, agent_name: str = None):
    """Log data to llm_calls.log file"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id or "unknown",
            "agent_name": agent_name or "compaction",
            **log_data
        }

        with open("logs/llm_calls.log", 'a') as f:
            f.write(json.dumps(log_entry, indent=2))
            f.write("\n" + "="*80 + "\n")
    except Exception as e:
        print(f"Warning: Failed to log to file: {e}")


def count_words(text: str) -> int:
    """Count words in a string"""
    return len(text.split())


def strip_json_code_blocks(text: str) -> str:
    """Strip markdown code blocks from JSON response, allowing text before the code block"""
    text = text.strip()
    # Look for ```json or ``` code block anywhere in the text
    code_block_start = text.find("```")
    if code_block_start != -1:
        # Find the first newline after opening ```
        first_newline = text.find('\n', code_block_start)
        if first_newline != -1:
            # Find the closing ```
            closing = text.find("```", first_newline)
            if closing != -1:
                text = text[first_newline+1:closing].strip()
    return text


def save_screenshot(screenshot_data: str, prefix: str = "screenshot") -> str:
    """
    Save a base64-encoded screenshot to the screenshots directory

    Args:
        screenshot_data: Base64-encoded image data (with or without data URL prefix)
        prefix: Prefix for the screenshot filename

    Returns:
        Path to the saved screenshot file
    """
    import base64
    import os
    from datetime import datetime

    # Create screenshots directory if it doesn't exist
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)

    # Generate timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # millisecond precision
    filename = f"{prefix}_{timestamp}.png"
    filepath = os.path.join(screenshots_dir, filename)

    # Extract base64 data if it includes the data URL prefix
    if screenshot_data.startswith("data:image"):
        # Format: data:image/jpeg;base64,<data> or data:image/png;base64,<data>
        screenshot_data = screenshot_data.split(",", 1)[1]

    # Decode and save
    try:
        # Fix base64 padding if needed
        # Base64 strings should be a multiple of 4 characters
        missing_padding = len(screenshot_data) % 4
        if missing_padding:
            screenshot_data += '=' * (4 - missing_padding)

        image_bytes = base64.b64decode(screenshot_data)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filepath
    except Exception as e:
        print(f"Warning: Failed to save screenshot: {e}")
        return None
