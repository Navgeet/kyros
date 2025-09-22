#!/usr/bin/env python3
"""
Script to generate text plans from user prompts using InternLM API with screenshot support.
Supports streaming output for real-time plan generation.
"""

import sys
import argparse
import os
import requests
import json
import pyautogui
import base64
from typing import Optional, Callable
from planner import Planner

def generate_text_plan_internlm(prompt: str, api_url: str = "http://localhost:23333", 
                               api_key: str = None, include_screenshot: bool = True,
                               stream: bool = False, screenshot_file: str = None) -> str:
    """
    Generate a text plan using InternLM API with optional screenshot.
    
    Args:
        prompt: The user input/prompt to generate a plan for
        api_url: InternLM API URL
        api_key: API key for authentication
        include_screenshot: Whether to include current screenshot
        stream: Whether to use streaming
        screenshot_file: Path to existing screenshot file (if None, takes new screenshot)
        
    Returns:
        Generated text plan as a string
    """
    try:
        # Prepare the planning prompt
        planning_prompt = f"""
You are a high-level task planner. Your job is to create a text-based plan to accomplish the user's request.

Given the user input and available tools, create a step-by-step text plan that describes what needs to be done.
This plan will later be converted to executable Python code, so focus on the logical steps needed.

Available tools overview:
- focus_window(name): Focus a window by name
- hotkey(keys): Send keyboard shortcuts like "ctrl+t", "enter"
- type(text): Type text
- click(x, y): Click at coordinates
- scroll(i): Scroll up/down
- move_to(x, y): Move mouse to coordinates
- query_screen(query): Ask questions about what's on screen
- run_shell_command(args): Run shell commands
- add(a, b): add two numbers

Other available actions:
- add some text to context
- send message to user
- replan

Create a concise, step-by-step text plan. Do not write code - just describe the steps.

Rules:
- Specify the tool names and the exact argument values.
- Add error handling where appropriate. Fallback to replanning if required.

User request: {prompt}
"""
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Prepare message content
        message_content = [{"type": "text", "text": planning_prompt}]
        
        # Add screenshot if requested
        if include_screenshot:
            if screenshot_file:
                print(f"📁 Loading screenshot from: {screenshot_file}")
                try:
                    with open(screenshot_file, 'rb') as f:
                        img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    # Determine file format for MIME type
                    file_ext = screenshot_file.lower().split('.')[-1]
                    if file_ext in ['jpg', 'jpeg']:
                        mime_type = 'jpeg'
                    elif file_ext == 'png':
                        mime_type = 'png'
                    elif file_ext == 'webp':
                        mime_type = 'webp'
                    else:
                        mime_type = 'jpeg'  # default
                        
                except Exception as e:
                    print(f"❌ Error loading screenshot file: {e}")
                    return f"Error: Cannot load screenshot file - {e}"
            else:
                print("📸 Taking screenshot...")
                screenshot = pyautogui.screenshot()
                
                # Compress screenshot and convert to base64
                import io
                img_buffer = io.BytesIO()
                screenshot.save(img_buffer, format='JPEG', quality=75, optimize=True)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                mime_type = 'jpeg'
            
            message_content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/{mime_type};base64,{img_base64}"}
            })
        
        # Prepare payload
        payload = {
            "model": "internvl3.5-241b-a28b",
            "messages": [{"role": "user", "content": message_content}],
            "stream": stream
        }
        
        print(f"🤖 Generating text plan using InternLM...")
        print(f"📡 API URL: {api_url}")
        if include_screenshot:
            if screenshot_file:
                print(f"🖼️  Screenshot: from file ({screenshot_file})")
            else:
                print(f"🖼️  Screenshot: captured live")
        else:
            print(f"🖼️  Screenshot: not included")
        print(f"🌊 Streaming: {'enabled' if stream else 'disabled'}")
        print()
        
        if stream:
            return _handle_streaming_response(api_url, payload, headers)
        else:
            return _handle_non_streaming_response(api_url, payload, headers)
            
    except Exception as e:
        print(f"❌ Error generating text plan with InternLM: {e}")
        return f"Error: {e}"

def _handle_streaming_response(api_url: str, payload: dict, headers: dict) -> str:
    """Handle streaming response from InternLM API."""
    try:
        response = requests.post(f"{api_url}/v1/chat/completions", 
                               json=payload, headers=headers, stream=True)
        
        if response.status_code != 200:
            error_msg = f"API error: {response.status_code} - {response.text}"
            print(error_msg)
            return error_msg
        
        print("💭 Thinking: ", end="", flush=True)
        full_response = ""
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            print(content, end="", flush=True)
                            full_response += content
                    except json.JSONDecodeError:
                        continue
        
        print()  # Final newline
        return full_response.strip()
        
    except Exception as e:
        error_msg = f"Streaming error: {e}"
        print(error_msg)
        return error_msg

def _handle_non_streaming_response(api_url: str, payload: dict, headers: dict) -> str:
    """Handle non-streaming response from InternLM API."""
    try:
        response = requests.post(f"{api_url}/v1/chat/completions", 
                               json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            print("📝 Generated text plan:")
            print("-" * 50)
            print(answer)
            print("-" * 50)
            return answer
        else:
            error_msg = f"API error: {response.status_code} - {response.text}"
            print(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Request error: {e}"
        print(error_msg)
        return error_msg

def generate_text_plan(prompt: str, vllm_url: str = "http://localhost:8000/v1", 
                      streaming_callback: Optional[Callable] = None) -> str:
    """
    Generate a text plan from a user prompt with optional streaming (legacy method).
    
    Args:
        prompt: The user input/prompt to generate a plan for
        vllm_url: URL of the vLLM server
        streaming_callback: Optional callback for streaming output (chunk_type, content)
        
    Returns:
        Generated text plan as a string
    """
    planner = Planner(vllm_url=vllm_url)
    
    # Set up streaming callback if provided
    if streaming_callback:
        planner.set_streaming_callback(streaming_callback)
    
    return planner._generate_text_plan(prompt)

def generate_text_plan_streaming(prompt: str, vllm_url: str = "http://localhost:8000/v1",
                                use_colors: bool = True) -> str:
    """
    Generate a text plan with built-in streaming output to console.
    
    Args:
        prompt: The user input/prompt to generate a plan for
        vllm_url: URL of the vLLM server
        use_colors: Whether to use colored output
        
    Returns:
        Generated text plan as a string
    """
    
    def streaming_callback(chunk_type: str, content: str):
        """Handle streaming output with visual formatting."""
        if chunk_type == "thinking":
            if use_colors:
                print(f"\033[90m{content}\033[0m", end="", flush=True)
            else:
                print(content, end="", flush=True)
        elif chunk_type == "plan":
            print(content, end="", flush=True)
    
    return generate_text_plan(prompt, vllm_url, streaming_callback)

def main():
    parser = argparse.ArgumentParser(description="Generate text plan from user prompt using InternLM API")
    parser.add_argument("prompt", help="The user prompt to generate a plan for")
    parser.add_argument("--api-url", default="http://localhost:23333", 
                       help="InternLM API URL (default: http://localhost:23333)")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", "-o", help="Output file to save the plan (optional)")
    parser.add_argument("--no-streaming", action="store_true", 
                       help="Disable streaming output")
    parser.add_argument("--no-screenshot", action="store_true",
                       help="Don't include screenshot in the request")
    parser.add_argument("--screenshot-file", help="Use existing screenshot file instead of taking new one")
    parser.add_argument("--legacy", action="store_true",
                       help="Use legacy vLLM method instead of InternLM")
    parser.add_argument("--vllm-url", default="http://localhost:8000/v1", 
                       help="vLLM server URL for legacy mode")
    
    args = parser.parse_args()
    
    try:
        print(f"🤖 Generating text plan for: {args.prompt}")
        
        # Get API key from environment if not provided
        api_key = args.api_key or os.getenv("INTERNLM_API_KEY")
        
        if args.legacy:
            # Use legacy vLLM method
            print(f"📡 Using legacy vLLM server: {args.vllm_url}")
            print()
            
            if args.no_streaming:
                text_plan = generate_text_plan(args.prompt, args.vllm_url)
                print("📝 Generated Text Plan:")
                print("-" * 50)
                print(text_plan)
                print("-" * 50)
            else:
                text_plan = generate_text_plan_streaming(args.prompt, args.vllm_url)
        else:
            # Use InternLM API
            text_plan = generate_text_plan_internlm(
                prompt=args.prompt,
                api_url=args.api_url,
                api_key=api_key,
                include_screenshot=not args.no_screenshot,
                stream=not args.no_streaming,
                screenshot_file=args.screenshot_file
            )
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write(text_plan)
            print(f"\n💾 Plan saved to: {args.output}")
            
    except Exception as e:
        print(f"❌ Error generating text plan: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # If run without arguments, provide interactive mode
    if len(sys.argv) == 1:
        print("🎯 Interactive Text Plan Generator (InternLM API with screenshot)")
        print("Commands:")
        print("  'quit'/'exit'/'q' - exit")
        print("  'toggle' - toggle streaming")
        print("  'screenshot' - toggle screenshot inclusion")
        print("  'file <path>' - set screenshot file (or 'file' to clear)")
        print("  'url <url>' - set API URL")
        print("  'key <key>' - set API key")
        print("Enter your prompt:")
        
        use_streaming = True
        include_screenshot = True
        api_url = "http://localhost:23333"
        api_key = os.getenv("INTERNLM_API_KEY")
        screenshot_file = None
        
        while True:
            try:
                status = f"[{'stream' if use_streaming else 'no-stream'}]"
                status += f"[{'📸' if include_screenshot else '🚫📸'}]"
                if screenshot_file:
                    status += f"[📁{os.path.basename(screenshot_file)}]"
                prompt = input(f"\n{status} > ").strip()
                
                if prompt.lower() in ['quit', 'exit', 'q']:
                    break
                elif prompt.lower() in ['toggle', 'stream', 'no-stream']:
                    use_streaming = not use_streaming
                    print(f"{'✅ Streaming enabled' if use_streaming else '❌ Streaming disabled'}")
                    continue
                elif prompt.lower() in ['screenshot', 'pic', 'image']:
                    include_screenshot = not include_screenshot
                    print(f"{'📸 Screenshot enabled' if include_screenshot else '🚫 Screenshot disabled'}")
                    continue
                elif prompt.lower().startswith('url '):
                    api_url = prompt[4:].strip()
                    print(f"📡 API URL set to: {api_url}")
                    continue
                elif prompt.lower().startswith('key '):
                    api_key = prompt[4:].strip()
                    print(f"🔑 API key set")
                    continue
                elif prompt.lower().startswith('file'):
                    if len(prompt.split()) > 1:
                        screenshot_file = prompt[5:].strip()
                        if os.path.exists(screenshot_file):
                            print(f"📁 Screenshot file set to: {screenshot_file}")
                        else:
                            print(f"⚠️  Warning: Screenshot file not found: {screenshot_file}")
                    else:
                        screenshot_file = None
                        print("📁 Screenshot file cleared - will capture live")
                    continue
                elif not prompt:
                    continue
                    
                text_plan = generate_text_plan_internlm(
                    prompt=prompt,
                    api_url=api_url,
                    api_key=api_key,
                    include_screenshot=include_screenshot,
                    stream=use_streaming,
                    screenshot_file=screenshot_file
                )
                
                print()  # Extra newline after completion
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    else:
        main()
