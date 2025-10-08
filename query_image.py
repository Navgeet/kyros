#!/usr/bin/env python3
"""
Script to query images using InternLM model for click coordinate detection.
"""
import argparse
import requests
import json
import base64
import sys
from pathlib import Path

def encode_image_to_base64(image_path):
    """Convert image to base64 string, converting to JPEG with quality 75."""
    from PIL import Image
    import io

    # Open and convert image to JPEG
    with Image.open(image_path) as img:
        # Convert to RGB if needed (for PNG with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        # Save as JPEG with quality 75
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=75, optimize=True)
        img_buffer.seek(0)

        return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

def query_internlm_model(image_path, query, model_name="internvl3.5-241b-a28b"):
    """
    Query the InternLM model with an image and text prompt.

    Args:
        image_path: Path to the image file
        query: Text query about the image
        model_name: Model name to use

    Returns:
        Response from the model
    """
    # Convert image to base64
    image_base64 = encode_image_to_base64(image_path)

    # Prepare the request payload
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
    }

    # Make the API request
    # Note: You'll need to replace this URL with the actual InternLM API endpoint
    api_url = "https://chat.intern-ai.org.cn/api/v1/chat/completions"  # Replace with actual endpoint

    headers = {
        "Content-Type": "application/json",
        # Add authorization header if needed
        "Authorization": "Bearer sk-sjqf8593PefkxEluNWXi6PEoo5AsSjOB7Sf47IipA75rupgi"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying model: {e}", file=sys.stderr)
        return None

def extract_coordinates(response_text):
    """
    Extract relative coordinates from model response.
    Looks for patterns like (0.5, 0.3) or x=0.5, y=0.3

    Returns:
        tuple: (x, y) coordinates or None if not found
    """
    import re

    # Pattern to match coordinates in various formats
    patterns = [
        r'\((\d*\.?\d+),\s*(\d*\.?\d+)\)',  # (0.5, 0.3)
        r'x=(\d*\.?\d+).*?y=(\d*\.?\d+)',   # x=0.5, y=0.3
        r'(\d*\.?\d+),\s*(\d*\.?\d+)',      # 0.5, 0.3
    ]

    for pattern in patterns:
        match = re.search(pattern, response_text)
        if match:
            x, y = float(match.group(1)), float(match.group(2))
            # Ensure coordinates are in valid range
            if 0 <= x <= 1 and 0 <= y <= 1:
                return (x, y)

    return None

def main():
    parser = argparse.ArgumentParser(description='Query image using InternLM model')
    parser.add_argument('image_path', help='Path to the image file')
    parser.add_argument('query', help='Query about the image')
    parser.add_argument('--model', default='internvl3.5-241b-a28b', help='Model name to use')
    parser.add_argument('--coords-only', action='store_true', help='Return only coordinates')

    args = parser.parse_args()

    # Check if image exists
    if not Path(args.image_path).exists():
        print(f"Error: Image file {args.image_path} not found", file=sys.stderr)
        sys.exit(1)

    query = f"Instruct: If asked to find/locate something only return relative coordinates (0-1), no explanation text. Otherwise answer the query\nQuery: {args.query}"

    # Query the model
    response = query_internlm_model(args.image_path, args.query, args.model)

    if response is None:
        print("Error: Failed to get response from model", file=sys.stderr)
        sys.exit(1)

    # Extract response text
    try:
        response_text = response['choices'][0]['message']['content']
    except (KeyError, IndexError):
        print("Error: Invalid response format from model", file=sys.stderr)
        sys.exit(1)

    if args.coords_only:
        # Try to extract coordinates
        coords = extract_coordinates(response_text)
        if coords:
            print(f"{coords[0]},{coords[1]}")
        else:
            print("Error: Could not extract coordinates from response", file=sys.stderr)
            sys.exit(1)
    else:
        # Print full response
        print(response_text)

if __name__ == "__main__":
    main()