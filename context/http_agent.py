#!/usr/bin/env python3
"""
HTTP Agent for processing messages and images with InternLM.
Receives messages and images via HTTP, processes them with InternLM, and updates context.
"""

import json
import logging
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from io import BytesIO

from flask import Flask, request, jsonify
from PIL import Image
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InternLMClient:
    """Client for interacting with InternLM API."""

    def __init__(self, api_url: str = "http://localhost:8080/v1/chat/completions", api_key: Optional[str] = None):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def process_message(self, messages: List[Dict], max_tokens: int = 1000) -> str:
        """Send messages to InternLM and get response."""
        payload = {
            "model": "internlm2-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling InternLM API: {e}")
            return f"Error: Failed to process request - {str(e)}"
        except KeyError as e:
            logger.error(f"Unexpected response format: {e}")
            return "Error: Unexpected response format from InternLM"

class ContextManager:
    """Manages the context document."""

    def __init__(self, context_file: str = "context.txt"):
        self.context_file = Path(context_file)
        self.ensure_context_file()

    def ensure_context_file(self):
        """Create context file if it doesn't exist."""
        if not self.context_file.exists():
            self.context_file.write_text("# Agent Context\n\nInitialized on: {}\n\n".format(
                datetime.now().isoformat()
            ))

    def read_context(self) -> str:
        """Read current context."""
        return self.context_file.read_text()

    def update_context(self, new_content: str, append: bool = True):
        """Update context with new content."""
        timestamp = datetime.now().isoformat()

        if append:
            current_context = self.read_context()
            updated_context = f"{current_context}\n\n--- Update: {timestamp} ---\n{new_content}\n"
        else:
            updated_context = f"# Agent Context\n\nLast updated: {timestamp}\n\n{new_content}\n"

        self.context_file.write_text(updated_context)
        logger.info(f"Context updated at {timestamp}")

class HTTPAgent:
    """HTTP Agent for processing messages and images."""

    def __init__(self, internlm_url: str = "http://localhost:8080/v1/chat/completions",
                 api_key: Optional[str] = None, context_file: str = "context.txt"):
        self.app = Flask(__name__)
        self.internlm_client = InternLMClient(internlm_url, api_key)
        self.context_manager = ContextManager(context_file)
        self.setup_routes()

    def setup_routes(self):
        """Setup HTTP routes."""

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

        @self.app.route('/process', methods=['POST'])
        def process():
            """Process message and optional images."""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400

                message = data.get('message', '')
                images = data.get('images', [])

                if not message:
                    return jsonify({"error": "Message is required"}), 400

                # Process the request
                result = self.process_request(message, images)

                return jsonify({
                    "status": "success",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                logger.error(f"Error processing request: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/context', methods=['GET'])
        def get_context():
            """Get current context."""
            try:
                context = self.context_manager.read_context()
                return jsonify({
                    "context": context,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error getting context: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/context', methods=['POST'])
        def update_context():
            """Manually update context."""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400

                content = data.get('content', '')
                append = data.get('append', True)

                if not content:
                    return jsonify({"error": "Content is required"}), 400

                self.context_manager.update_context(content, append)

                return jsonify({
                    "status": "success",
                    "message": "Context updated",
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                logger.error(f"Error updating context: {e}")
                return jsonify({"error": str(e)}), 500

    def process_images(self, images: List[str]) -> List[Dict]:
        """Process base64 encoded images."""
        processed_images = []

        for i, img_data in enumerate(images):
            try:
                # Remove data URL prefix if present
                if img_data.startswith('data:image'):
                    img_data = img_data.split(',', 1)[1]

                # Decode base64 image
                img_bytes = base64.b64decode(img_data)
                img = Image.open(BytesIO(img_bytes))

                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if too large
                max_size = 1024
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Convert back to base64
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

                processed_images.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }
                })

                logger.info(f"Processed image {i+1}/{len(images)}")

            except Exception as e:
                logger.error(f"Error processing image {i+1}: {e}")

        return processed_images

    def process_request(self, message: str, images: List[str]) -> Dict:
        """Process a request with message and images."""
        # Get current context
        current_context = self.context_manager.read_context()

        # Prepare messages for InternLM
        messages = [
            {
                "role": "system",
                "content": f"You are an AI assistant. Here is the current context:\n\n{current_context}\n\nProcess the user's message and any images they provide. Provide a helpful response and suggest how to update the context based on this interaction."
            }
        ]

        # Process images if provided
        content = [{"type": "text", "text": message}]

        if images:
            processed_images = self.process_images(images)
            content = processed_images + content

        messages.append({
            "role": "user",
            "content": content
        })

        # Get response from InternLM
        response = self.internlm_client.process_message(messages)

        # Update context with the interaction
        interaction_summary = f"User Message: {message}\n"
        if images:
            interaction_summary += f"Images: {len(images)} image(s) provided\n"
        interaction_summary += f"AI Response: {response}"

        self.context_manager.update_context(interaction_summary)

        return {
            "response": response,
            "images_processed": len(images),
            "context_updated": True
        }

    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Run the HTTP server."""
        logger.info(f"Starting HTTP Agent on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="HTTP Agent with InternLM")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--internlm-url', default='http://localhost:8080/v1/chat/completions',
                       help='InternLM API URL')
    parser.add_argument('--api-key', help='API key for InternLM (optional)')
    parser.add_argument('--context-file', default='context.txt', help='Context file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    agent = HTTPAgent(
        internlm_url=args.internlm_url,
        api_key=args.api_key,
        context_file=args.context_file
    )

    agent.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()