#!/usr/bin/env python3
"""
Script to refine text plans using InternLM API with screenshot support.
Takes an existing plan and improves it based on available tools and context.
"""

import sys
import argparse
import os
import requests
import json
import pyautogui
import base64
from typing import Optional

def refine_plan_internlm(prompt: str,
                        api_url: str = "http://localhost:23333", 
                        api_key: str = None, include_screenshot: bool = True,
                        stream: bool = False, screenshot_file: str = None) -> str:
    """
    Refine a text plan using InternLM API with optional screenshot.
    
    Args:
        original_plan: The original plan to refine
        user_request: The original user request (for context)
        api_url: InternLM API URL
        api_key: API key for authentication
        include_screenshot: Whether to include current screenshot
        stream: Whether to use streaming
        screenshot_file: Path to existing screenshot file (if None, takes new screenshot)
        
    Returns:
        Refined text plan as a string
    """
    try:
        # Prepare the refinement prompt
        refinement_prompt = f"""
Analyze and improve the given plan according to user feedback. Only make the required changes, don't change anything else.

{prompt}

Available tools overview:
- focus_window(name): Focus a window by name
- hotkey(keys): Send keyboard shortcuts like "ctrl+t", "enter"
- type(text): Type text
- click(x, y): Click at coordinates
- move_to(x, y): Move mouse to coordinates
- query_screen(query): Ask questions about what's on screen
- run_shell_command(args): Run shell commands
- add(a, b): add two numbers

Other available actions:
- add some text to context
- send message to user
- replanning

"""
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Prepare message content
        message_content = [{"type": "text", "text": refinement_prompt}]
        
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
        
        print(f"🔄 Refining plan using InternLM...")
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
        print(f"❌ Error refining plan with InternLM: {e}")
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
            print("📝 Refined plan:")
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

def read_plan_from_file(file_path: str) -> str:
    """Read plan from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error reading plan file: {e}")
        return ""

def main():
    parser = argparse.ArgumentParser(description="Refine text plan using InternLM API")
    
    # Input methods (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--plan", help="Original plan text directly")
    input_group.add_argument("--plan-file", help="File containing the original plan")
    
    # Optional parameters
    parser.add_argument("--user-request", default="", 
                       help="Original user request for context")
    parser.add_argument("--api-url", default="http://localhost:23333", 
                       help="InternLM API URL (default: http://localhost:23333)")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", "-o", help="Output file to save the refined plan")
    parser.add_argument("--no-streaming", action="store_true", 
                       help="Disable streaming output")
    parser.add_argument("--no-screenshot", action="store_true",
                       help="Don't include screenshot in the request")
    parser.add_argument("--screenshot-file", help="Use existing screenshot file instead of taking new one")
    
    args = parser.parse_args()
    
    try:
        # Get the original plan
        if args.plan:
            original_plan = args.plan
        else:
            original_plan = read_plan_from_file(args.plan_file)
            if not original_plan:
                print(f"❌ Could not read plan from file: {args.plan_file}")
                sys.exit(1)
        
        print(f"🔄 Refining plan...")
        print(f"📋 Original plan preview: {original_plan[:100]}...")
        if args.user_request:
            print(f"👤 User request: {args.user_request}")
        
        # Get API key from environment if not provided
        api_key = args.api_key or os.getenv("INTERNLM_API_KEY")
        
        # Refine the plan
        refined_plan = refine_plan_internlm(
            original_plan=original_plan,
            user_request=args.user_request,
            api_url=args.api_url,
            api_key=api_key,
            include_screenshot=not args.no_screenshot,
            stream=not args.no_streaming,
            screenshot_file=args.screenshot_file
        )
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write(refined_plan)
            print(f"\n💾 Refined plan saved to: {args.output}")
            
    except Exception as e:
        print(f"❌ Error refining plan: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # If run without arguments, provide interactive mode
    if len(sys.argv) == 1:
        print("🎯 Interactive Plan Refinement (InternLM API with screenshot)")
        print("Commands:")
        print("  'quit'/'exit'/'q' - exit")
        print("  'toggle' - toggle streaming")
        print("  'screenshot' - toggle screenshot inclusion")
        print("  'file <path>' - set screenshot file (or 'file' to clear)")
        print("  'url <url>' - set API URL")
        print("  'key <key>' - set API key")
        print("  'request <text>' - set user request context")
        print("Enter original plan to refine:")
        
        use_streaming = True
        include_screenshot = True
        api_url = "http://localhost:23333"
        api_key = os.getenv("INTERNLM_API_KEY")
        screenshot_file = None
        user_request = ""
        
        while True:
            try:
                status = f"[{'stream' if use_streaming else 'no-stream'}]"
                status += f"[{'📸' if include_screenshot else '🚫📸'}]"
                if screenshot_file:
                    status += f"[📁{os.path.basename(screenshot_file)}]"
                if user_request:
                    status += f"[👤{user_request[:20]}...]"
                
                plan_input = input(f"\n{status} Plan> ").strip()
                
                if plan_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif plan_input.lower() in ['toggle', 'stream', 'no-stream']:
                    use_streaming = not use_streaming
                    print(f"{'✅ Streaming enabled' if use_streaming else '❌ Streaming disabled'}")
                    continue
                elif plan_input.lower() in ['screenshot', 'pic', 'image']:
                    include_screenshot = not include_screenshot
                    print(f"{'📸 Screenshot enabled' if include_screenshot else '🚫 Screenshot disabled'}")
                    continue
                elif plan_input.lower().startswith('file'):
                    if len(plan_input.split()) > 1:
                        screenshot_file = plan_input[5:].strip()
                        if os.path.exists(screenshot_file):
                            print(f"📁 Screenshot file set to: {screenshot_file}")
                        else:
                            print(f"⚠️  Warning: Screenshot file not found: {screenshot_file}")
                    else:
                        screenshot_file = None
                        print("📁 Screenshot file cleared - will capture live")
                    continue
                elif plan_input.lower().startswith('url '):
                    api_url = plan_input[4:].strip()
                    print(f"📡 API URL set to: {api_url}")
                    continue
                elif plan_input.lower().startswith('key '):
                    api_key = plan_input[4:].strip()
                    print(f"🔑 API key set")
                    continue
                elif plan_input.lower().startswith('request '):
                    user_request = plan_input[8:].strip()
                    print(f"👤 User request set to: {user_request}")
                    continue
                elif not plan_input:
                    continue
                    
                refined_plan = refine_plan_internlm(
                    original_plan=plan_input,
                    user_request=user_request,
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
