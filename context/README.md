# HTTP Agent with InternLM

A standalone HTTP agent that receives messages and images as input, processes them using InternLM, and maintains a persistent context document.

## Features

- **HTTP API**: RESTful endpoints for processing messages and images
- **InternLM Integration**: Uses InternLM for natural language and vision processing
- **Context Management**: Maintains persistent context across interactions
- **Image Processing**: Handles base64-encoded images with automatic resizing
- **Health Monitoring**: Built-in health check endpoint

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have InternLM running (default: `http://localhost:8080/v1/chat/completions`)

## Usage

### Starting the Agent

```bash
# Basic usage
python http_agent.py

# Custom configuration
python http_agent.py --host 0.0.0.0 --port 8000 --internlm-url http://your-internlm-server:8080/v1/chat/completions
```

### Command Line Options

- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 5000)
- `--internlm-url`: InternLM API URL (default: http://localhost:8080/v1/chat/completions)
- `--api-key`: API key for InternLM (optional)
- `--context-file`: Context file path (default: context.txt)
- `--debug`: Enable debug mode

## API Endpoints

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

### Process Message and Images
```http
POST /process
Content-Type: application/json

{
  "message": "Your message here",
  "images": ["base64_encoded_image1", "base64_encoded_image2"]
}
```

Response:
```json
{
  "status": "success",
  "result": {
    "response": "AI response to your message",
    "images_processed": 2,
    "context_updated": true
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

### Get Context
```http
GET /context
```

Response:
```json
{
  "context": "Current context content...",
  "timestamp": "2024-01-01T12:00:00"
}
```

### Update Context
```http
POST /context
Content-Type: application/json

{
  "content": "New content to add",
  "append": true
}
```

Response:
```json
{
  "status": "success",
  "message": "Context updated",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Testing

Run the example client to test the agent:

```bash
python example_client.py

# Test with custom URL
python example_client.py --url http://localhost:8000
```

## Image Format

Images should be provided as base64-encoded strings. The agent supports:
- Common formats: PNG, JPEG, GIF, BMP
- Automatic conversion to RGB
- Automatic resizing for large images (max 1024px)
- Data URL format support (e.g., `data:image/png;base64,iVBORw0KGgo...`)

## Context Management

The agent maintains a persistent context file that:
- Records all interactions with timestamps
- Includes user messages, processed images count, and AI responses
- Can be manually updated via the API
- Supports both append and replace modes

## Example Usage in Python

```python
import requests
import base64

# Prepare data
data = {
    "message": "What do you see in this image?",
    "images": [base64.b64encode(open("image.png", "rb").read()).decode()]
}

# Send request
response = requests.post("http://localhost:5000/process", json=data)
result = response.json()

print(result["result"]["response"])
```

## Configuration

### InternLM Setup

The agent expects InternLM to be running with OpenAI-compatible API endpoints. Common configurations:

1. **Local InternLM**: `http://localhost:8080/v1/chat/completions`
2. **Remote InternLM**: Update the `--internlm-url` parameter
3. **API Key**: Use `--api-key` if your InternLM instance requires authentication

### Context File

The context file (`context.txt` by default) stores:
- Initialization timestamp
- All user interactions
- AI responses
- Processing metadata

## Error Handling

The agent includes comprehensive error handling for:
- Invalid image formats
- InternLM API failures
- Missing required parameters
- File system issues

All errors are logged and returned as JSON responses with appropriate HTTP status codes.