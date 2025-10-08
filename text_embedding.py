#!/usr/bin/env python3
"""
Script to generate embeddings for text using Ollama.
"""

import json
import requests
import sys
from typing import List, Optional


def get_embedding(text: str, model: str = "dengcao/Qwen3-Embedding-8B:Q4_K_M") -> Optional[List[float]]:
    """Get embedding for text using Ollama API."""
    url = "http://192.168.0.213:11434/api/embeddings"

    payload = {
        "model": model,
        "prompt": text
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        return result.get("embedding")

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}", file=sys.stderr)
        return None


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python text_embedding.py <text>")
        print("Example: python text_embedding.py 'Hello world'")
        sys.exit(1)

    text = " ".join(sys.argv[1:])

    print(f"Generating embedding for: {text}")
    print(f"Using model: dengcao/Qwen3-Embedding-8B:Q4_K_M")

    embedding = get_embedding(text)

    if embedding:
        print(f"Embedding dimension: {len(embedding)}")
        print("Embedding vector:")
        print(json.dumps(embedding, indent=2))
    else:
        print("Failed to generate embedding")
        sys.exit(1)


if __name__ == "__main__":
    main()