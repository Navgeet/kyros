#!/usr/bin/env python3
"""
LLM integration for Kyros using InternLM API.
Based on the generate_text_plan.py example.
"""

import os
import requests
import json
import base64
from typing import List, Dict, Any, Optional
from PIL import Image
from io import BytesIO


def internlm_llm_function(messages: List[Dict[str, Any]],
                         api_url: str = "http://localhost:23333",
                         api_key: Optional[str] = None,
                         model: str = "internvl3.5-241b-a28b",
                         stream: bool = False) -> str:
    """
    LLM function using InternLM API for Kyros agent.

    Args:
        messages: List of message dictionaries in OpenAI format
        api_url: InternLM API URL
        api_key: API key for authentication
        model: Model name to use
        stream: Whether to use streaming (for now always False for simplicity)

    Returns:
        str: Generated response from the LLM
    """
    try:
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv("INTERNLM_API_KEY")

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Prepare payload
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 2000,
            "temperature": 0.1
        }

        print(f"🤖 Calling InternLM API at {api_url}")

        # Make the request
        response = requests.post(f"{api_url}/v1/chat/completions",
                               json=payload, headers=headers, timeout=60)

        if response.status_code == 200:
            result = response.json()
            answer = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            return answer
        else:
            error_msg = f"API error: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        error_msg = f"LLM call error: {e}"
        print(f"❌ {error_msg}")
        return f"Error: {error_msg}"


def create_internlm_function(api_url: str = "http://localhost:23333",
                           api_key: Optional[str] = None,
                           model: str = "internvl3.5-241b-a28b") -> callable:
    """
    Create a configured InternLM function for use with KyrosAgent.

    Args:
        api_url: InternLM API URL
        api_key: API key for authentication
        model: Model name to use

    Returns:
        callable: Configured LLM function
    """
    def llm_func(messages):
        return internlm_llm_function(messages, api_url, api_key, model)

    return llm_func