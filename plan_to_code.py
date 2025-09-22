#!/usr/bin/env python3
"""
Script to convert text plans to executable Python code using InternLM API with screenshot support.
Uses computer vision to locate precise click coordinates and generate accurate automation code.
"""

import sys
import argparse
import os
import requests
import json
import pyautogui
import base64
from typing import Optional

def plan_to_code_internlm(text_plan: str, user_request: str = "", 
                         api_url: str = "http://localhost:23333", 
                         api_key: str = None, include_screenshot: bool = True,
                         stream: bool = True, screenshot_file: str = None) -> str:
    """
    Convert a text plan to executable Python code using InternLM API with screenshot.
    
    Args:
        text_plan: The text plan to convert to code
        user_request: The original user request (for context)
        api_url: InternLM API URL
        api_key: API key for authentication
        include_screenshot: Whether to include current screenshot
        stream: Whether to use streaming
        screenshot_file: Path to existing screenshot file (if None, takes new screenshot)
        
    Returns:
        Generated Python code as a string
    """
    try:
        # Prepare the code generation prompt
        code_prompt = f"""
You are a code generation expert. Convert the given high level plan into executable Python code using the tools module.
You must define a main function that takes no arguments and returns a JSON object with execution results.

example output:

```python
import tools
import json

def step_function_name():
    pass

def another_step():
    foo = tools.query_screen("foo bar")
    return foo


# Execute the steps
def main():
    messages = []
    context = []

    step_function_name()
    foo = another_step()
    if "expected text" not in foo:
        messages.append("Error: Expected text not found in screen query result")
        return {{"messages": messages, "context": context, "done": False}}  # will trigger replanning

    context.append(foo)
    messages.append("Successfully completed the task")
    return {{"messages": messages, "context": context, "done": True}}
```

Available tools:
- tools.focus_window(name): Focus window by name (e.g., "chrome", "firefox") 
- tools.hotkey(keys): Send keyboard shortcuts (e.g., "ctrl+t", "ctrl+w", "enter", "escape")
- tools.type(text): Type the specified text
- tools.click(x, y): Click at coordinates (use floats 0-1 for relative positioning)
- tools.move_to(x, y): Move mouse to coordinates (use floats 0-1 for relative positioning)
- tools.query_screen(query): Ask questions about screen content
- tools.run_shell_command(args): Execute shell commands
- tools.add(a, b): Add two numbers

Code Generation Rules:
1. Import tools and json at the top
2. Follow the high level plan, don't add/modify steps.
3. Use appropriate delays if needed (time.sleep)
4. Return {{"messages": [...], "context": [...], "done": False}} from main function to trigger replanning. This can be used as a fallback in error scenarios.
5. Return {{"messages": [...], "context": [...], "done": True}} from main function to indicate task completion.
6. Include helpful status messages in the messages array to inform the user about progress.

High level plan
{text_plan}

"""
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Prepare message content
        message_content = [{"type": "text", "text": code_prompt}]
        
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
        
        print(f"🐍 Converting plan to Python code using InternLM...")
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
        print(f"❌ Error converting plan to code with InternLM: {e}")
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
        
        # Extract code from response
        code = _extract_code_from_response(full_response)
        return code
        
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
            
            # Extract code from response
            code = _extract_code_from_response(answer)
            
            print("🐍 Generated Python code:")
            print("-" * 60)
            print(code)
            print("-" * 60)
            return code
        else:
            error_msg = f"API error: {response.status_code} - {response.text}"
            print(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Request error: {e}"
        print(error_msg)
        return error_msg

def _extract_code_from_response(response: str) -> str:
    """Extract Python code from the API response."""
    # Try to extract code from markdown blocks
    if '```python' in response:
        code = response.split('```python')[1].split('```')[0].strip()
    elif '```' in response:
        code = response.split('```')[1].split('```')[0].strip()
    else:
        # If no code blocks found, return the whole response
        code = response.strip()
    
    # Ensure it starts with import if it's valid Python code
    if code and not code.startswith('#') and not code.startswith('import'):
        if 'tools.' in code:
            code = 'import kyros.tools as tools\n\n' + code
    
    return code

def read_plan_from_file(file_path: str) -> str:
    """Read plan from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"❌ Error reading plan file: {e}")
        return ""

def validate_generated_code(code: str) -> bool:
    """Basic validation of the generated Python code."""
    try:
        # Try to compile the code to check for syntax errors
        compile(code, '<generated>', 'exec')
        
        # Check for required imports
        if 'import kyros.tools' not in code and 'import tools' not in code:
            print("⚠️  Warning: Generated code may be missing kyros.tools import")
            return False
        
        return True
    except SyntaxError as e:
        print(f"❌ Generated code has syntax errors: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Code validation warning: {e}")
        return True  # Allow execution despite warnings

def main():
    parser = argparse.ArgumentParser(description="Convert text plan to executable Python code using InternLM API")
    
    # Input methods (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--plan", help="Text plan to convert directly")
    input_group.add_argument("--plan-file", help="File containing the text plan")
    
    # Optional parameters
    parser.add_argument("--user-request", default="", 
                       help="Original user request for context")
    parser.add_argument("--api-url", default="http://localhost:23333", 
                       help="InternLM API URL (default: http://localhost:23333)")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", "-o", help="Output file to save the generated code")
    parser.add_argument("--no-streaming", action="store_true", 
                       help="Disable streaming output")
    parser.add_argument("--no-screenshot", action="store_true",
                       help="Don't include screenshot in the request")
    parser.add_argument("--screenshot-file", help="Use existing screenshot file instead of taking new one")
    parser.add_argument("--validate", action="store_true",
                       help="Validate generated code syntax")
    parser.add_argument("--execute", action="store_true",
                       help="Execute the generated code immediately (use with caution!)")
    
    args = parser.parse_args()
    
    try:
        # Get the text plan
        if args.plan:
            text_plan = args.plan
        else:
            text_plan = read_plan_from_file(args.plan_file)
            if not text_plan:
                print(f"❌ Could not read plan from file: {args.plan_file}")
                sys.exit(1)
        
        print(f"🐍 Converting text plan to Python code...")
        print(f"📋 Plan preview: {text_plan[:100]}...")
        if args.user_request:
            print(f"👤 User request: {args.user_request}")
        
        # Get API key from environment if not provided
        api_key = args.api_key or os.getenv("INTERNLM_API_KEY")
        
        # Generate Python code
        python_code = plan_to_code_internlm(
            text_plan=text_plan,
            user_request=args.user_request,
            api_url=args.api_url,
            api_key=api_key,
            include_screenshot=not args.no_screenshot,
            stream=not args.no_streaming,
            screenshot_file=args.screenshot_file
        )
        
        # Validate code if requested
        if args.validate:
            print("\n🔍 Validating generated code...")
            if validate_generated_code(python_code):
                print("✅ Code validation passed")
            else:
                print("⚠️  Code validation failed")
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write(python_code)
            print(f"\n💾 Generated code saved to: {args.output}")
        
        # Execute code if requested
        if args.execute:
            print("\n⚠️  EXECUTING GENERATED CODE - This will perform actual system actions!")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() in ['yes', 'y']:
                print("🚀 Executing generated code...")
                try:
                    # Create execution namespace
                    import kyros.tools as tools
                    exec_namespace = {
                        'tools': tools,
                        'kyros': __import__('kyros'),
                        '__builtins__': {
                            'print': print,
                            'len': len,
                            'str': str,
                            'int': int,
                            'float': float,
                            'bool': bool,
                            'list': list,
                            'dict': dict,
                            'range': range,
                            'enumerate': enumerate,
                            'zip': zip,
                        }
                    }
                    exec(python_code, exec_namespace)
                    print("✅ Code executed successfully")
                except Exception as e:
                    print(f"❌ Execution error: {e}")
            else:
                print("🛑 Execution cancelled")
            
    except Exception as e:
        print(f"❌ Error converting plan to code: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # If run without arguments, provide interactive mode
    if len(sys.argv) == 1:
        print("🎯 Interactive Plan to Code Converter (InternLM API with screenshot)")
        print("Commands:")
        print("  'quit'/'exit'/'q' - exit")
        print("  'toggle' - toggle streaming")
        print("  'screenshot' - toggle screenshot inclusion")
        print("  'file <path>' - set screenshot file (or 'file' to clear)")
        print("  'url <url>' - set API URL")
        print("  'key <key>' - set API key")
        print("  'request <text>' - set user request context")
        print("  'validate' - toggle code validation")
        print("Enter text plan to convert to code:")
        
        use_streaming = True
        include_screenshot = True
        api_url = "http://localhost:23333"
        api_key = os.getenv("INTERNLM_API_KEY")
        screenshot_file = None
        user_request = ""
        validate_code = True
        
        while True:
            try:
                status = f"[{'stream' if use_streaming else 'no-stream'}]"
                status += f"[{'📸' if include_screenshot else '🚫📸'}]"
                status += f"[{'✅' if validate_code else '🚫'}val]"
                if screenshot_file:
                    status += f"[📁{os.path.basename(screenshot_file)}]"
                if user_request:
                    status += f"[👤{user_request[:15]}...]"
                
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
                elif plan_input.lower() in ['validate', 'val']:
                    validate_code = not validate_code
                    print(f"{'✅ Code validation enabled' if validate_code else '🚫 Code validation disabled'}")
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
                    
                python_code = plan_to_code_internlm(
                    text_plan=plan_input,
                    user_request=user_request,
                    api_url=api_url,
                    api_key=api_key,
                    include_screenshot=include_screenshot,
                    stream=use_streaming,
                    screenshot_file=screenshot_file
                )
                
                # Validate if enabled
                if validate_code and python_code:
                    print("\n🔍 Validating code...")
                    validate_generated_code(python_code)
                
                print()  # Extra newline after completion
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    else:
        main()
