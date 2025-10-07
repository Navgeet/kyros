#!/usr/bin/env python3
"""
Example client for testing the HTTP Agent.
"""

import base64
import json
import requests
from pathlib import Path

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_agent(base_url: str = "http://localhost:5000"):
    """Test the HTTP Agent with example requests."""

    print("Testing HTTP Agent...")

    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
        return

    # Test message processing without images
    print("\n2. Testing message processing...")
    try:
        data = {
            "message": "Hello! This is a test message. Can you help me understand what you do?"
        }
        response = requests.post(f"{base_url}/process", json=data)
        result = response.json()
        print(f"Response: {result['result']['response']}")
    except Exception as e:
        print(f"Error: {e}")

    # Test getting context
    print("\n3. Testing context retrieval...")
    try:
        response = requests.get(f"{base_url}/context")
        context = response.json()
        print(f"Current context length: {len(context['context'])} characters")
        print(f"Context preview: {context['context'][:200]}...")
    except Exception as e:
        print(f"Error: {e}")

    # Test message with mock image (if you have an image file)
    print("\n4. Testing message with image...")
    try:
        # Create a simple test image if none exists
        from PIL import Image
        import io

        # Create a simple red square
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        data = {
            "message": "I'm sending you a red square image. Can you describe what you see?",
            "images": [img_b64]
        }
        response = requests.post(f"{base_url}/process", json=data)
        result = response.json()
        print(f"Response: {result['result']['response']}")
        print(f"Images processed: {result['result']['images_processed']}")
    except Exception as e:
        print(f"Error: {e}")

    # Test manual context update
    print("\n5. Testing manual context update...")
    try:
        data = {
            "content": "Manual update: The agent has been tested successfully.",
            "append": True
        }
        response = requests.post(f"{base_url}/context", json=data)
        result = response.json()
        print(f"Context update: {result['message']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test HTTP Agent")
    parser.add_argument('--url', default='http://localhost:5000', help='Agent URL')

    args = parser.parse_args()

    test_agent(args.url)