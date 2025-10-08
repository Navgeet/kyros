#!/usr/bin/env python3
"""
Script to generate embeddings for JSON documents using Ollama.
Generates embeddings for 'example' and 'learning' fields and stores them as 'example_embed' and 'learning_embed'.
"""

import json
import requests
import sys
from typing import List, Dict, Any


def get_embedding(text: str, model: str = "dengcao/Qwen3-Embedding-8B:Q4_K_M") -> List[float]:
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
        return result.get("embedding", [])

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return []


def process_documents(input_file: str, output_file: str = None) -> None:
    """Process JSON documents and add embeddings."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {input_file} not found")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return

    if not isinstance(documents, list):
        print("Error: Expected a list of documents")
        return

    processed_docs = []

    for i, doc in enumerate(documents):
        print(f"Processing document {i+1}/{len(documents)}...")

        # Create a copy of the document
        processed_doc = doc.copy()

        # Generate embedding for 'example' field
        if 'example' in doc:
            example_embedding = get_embedding(doc['example'])
            if example_embedding:
                processed_doc['example_embed'] = example_embedding
            else:
                print(f"Warning: Failed to generate embedding for 'example' in document {i+1}")

        # Generate embedding for 'learning' field
        if 'learning' in doc:
            learning_embedding = get_embedding(doc['learning'])
            if learning_embedding:
                processed_doc['learning_embed'] = learning_embedding
            else:
                print(f"Warning: Failed to generate embedding for 'learning' in document {i+1}")

        processed_docs.append(processed_doc)

    # Determine output file
    if output_file is None:
        output_file = input_file.replace('.json', '_with_embeddings.json')

    # Save processed documents
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_docs, f, indent=2, ensure_ascii=False)

        print(f"Successfully processed {len(processed_docs)} documents")
        print(f"Output saved to: {output_file}")

    except IOError as e:
        print(f"Error writing output file: {e}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python generate_embeddings.py <input_json_file> [output_json_file]")
        print("Example: python generate_embeddings.py /tmp/lel.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Generating embeddings for documents in: {input_file}")
    print(f"Using model: dengcao/Qwen3-Embedding-8B:Q4_K_M")

    process_documents(input_file, output_file)


if __name__ == "__main__":
    main()
