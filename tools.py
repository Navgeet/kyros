import pyautogui
import subprocess
import time
import os
import requests
import json
import base64
from typing import Dict, Any, Union
from PIL import Image, ImageDraw
import hashlib

class Tools:
    @staticmethod
    def focus_window(name: str) -> bool:
        """Find a running window by its name, switch to the desktop containing the window, raise and focus it."""
        try:
            # Use wmctrl to find and focus the window
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            windows = result.stdout.strip().split('\n')
            
            for window in windows:
                if name.lower() in window.lower():
                    # Extract window ID (first column)
                    window_id = window.split()[0]
                    
                    # Focus the window
                    subprocess.run(['wmctrl', '-i', '-a', window_id])
                    time.sleep(0.5)  # Give time for window to focus
                    return True
            
            print(f"Window '{name}' not found")
            return False
            
        except Exception as e:
            print(f"Error focusing window: {e}")
            return False
    
    @staticmethod
    def launch(path: str) -> bool:
        """Launches an application at the specified path."""
        try:
            subprocess.Popen([path])
            time.sleep(2)  # Give time for application to start
            return True
        except Exception as e:
            print(f"Error launching application: {e}")
            return False
    
    @staticmethod
    def hotkey(keys: str) -> bool:
        """Sends a keyboard hotkey combination."""
        try:
            # Parse key combination
            key_parts = keys.lower().split('+')
            
            if len(key_parts) == 1:
                pyautogui.press(key_parts[0])
            else:
                # Handle modifier keys
                modifiers = key_parts[:-1]
                main_key = key_parts[-1]
                
                # Map common modifier names
                modifier_map = {
                    'ctrl': 'ctrl',
                    'alt': 'alt', 
                    'shift': 'shift',
                    'cmd': 'cmd',
                    'win': 'win'
                }
                
                mapped_modifiers = [modifier_map.get(mod, mod) for mod in modifiers]
                pyautogui.hotkey(*mapped_modifiers, main_key)
            
            time.sleep(0.1)  # Small delay between key presses
            return True
            
        except Exception as e:
            print(f"Error sending hotkey: {e}")
            return False
    
    @staticmethod
    def move_to(x: Union[int, float], y: Union[int, float]) -> bool:
        """Moves the mouse cursor to the specified coordinates.
        
        Args:
            x: X coordinate. If int, absolute pixel coordinate. If float (0-1), relative to screen width.
            y: Y coordinate. If int, absolute pixel coordinate. If float (0-1), relative to screen height.
        """
        try:
            # Get screen dimensions
            screen_width, screen_height = pyautogui.size()
            
            # Convert relative coordinates to absolute if needed
            if isinstance(x, float):
                if not (0 <= x <= 1):
                    raise ValueError(f"Relative x coordinate must be between 0 and 1, got {x}")
                x = int(x * screen_width)
            
            if isinstance(y, float):
                if not (0 <= y <= 1):
                    raise ValueError(f"Relative y coordinate must be between 0 and 1, got {y}")
                y = int(y * screen_height)
            
            pyautogui.moveTo(x, y)
            time.sleep(0.1)  # Small delay after moving
            return True
        except Exception as e:
            print(f"Error moving mouse to ({x}, {y}): {e}")
            return False
    
    @staticmethod
    def click(x: Union[int, float], y: Union[int, float]) -> bool:
        """Clicks at the specified coordinates.
        
        Args:
            x: X coordinate. If int, absolute pixel coordinate. If float (0-1), relative to screen width.
            y: Y coordinate. If int, absolute pixel coordinate. If float (0-1), relative to screen height.
        """
        try:
            # Get screen dimensions
            screen_width, screen_height = pyautogui.size()
            
            # Convert relative coordinates to absolute if needed
            if isinstance(x, float):
                if not (0 <= x <= 1):
                    raise ValueError(f"Relative x coordinate must be between 0 and 1, got {x}")
                x = int(x * screen_width)
            
            if isinstance(y, float):
                if not (0 <= y <= 1):
                    raise ValueError(f"Relative y coordinate must be between 0 and 1, got {y}")
                y = int(y * screen_height)
            
            pyautogui.click(x, y)
            time.sleep(0.1)  # Small delay after clicking
            return True
        except Exception as e:
            print(f"Error clicking at ({x}, {y}): {e}")
            return False
    
    @staticmethod
    def type(text: str) -> bool:
        """Types the specified text. Won't do anything if there is nowhere to type into."""
        try:
            pyautogui.write(text)
            time.sleep(0.1)  # Small delay after typing
            return True
        except Exception as e:
            print(f"Error typing text: {e}")
            return False
    
    @staticmethod
    def screenshot(name: str) -> bool:
        """Takes a screenshot and saves it with the given name."""
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs("screenshots", exist_ok=True)
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            filepath = f"screenshots/{name}.png"
            screenshot.save(filepath)
            
            print(f"Screenshot saved as {filepath}")
            return True
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False
    
    @staticmethod
    def compare_screenshots(before: str, after: str) -> bool:
        """Compares two screenshots to detect if there was a visual change."""
        try:
            before_path = f"screenshots/{before}.png"
            after_path = f"screenshots/{after}.png"
            
            # Check if both files exist
            if not os.path.exists(before_path) or not os.path.exists(after_path):
                print(f"Screenshots not found: {before_path}, {after_path}")
                return False
            
            # Load images
            img_before = Image.open(before_path)
            img_after = Image.open(after_path)
            
            # Convert to bytes and hash for quick comparison
            before_hash = hashlib.md5(img_before.tobytes()).hexdigest()
            after_hash = hashlib.md5(img_after.tobytes()).hexdigest()
            
            # Check if images are different
            if before_hash != after_hash:
                print("✓ Screen change detected - task verification successful")
                return True
            else:
                print("✗ No screen change detected - task may have failed")
                return False
                
        except Exception as e:
            print(f"Error comparing screenshots: {e}")
            return False
    
    @staticmethod
    def _set_task_output(task, stdout=None, stderr=None):
        """Helper method to set task output for both Task objects and JSON dicts."""
        if task:
            if isinstance(task, dict):
                # JSON task
                if stdout is not None:
                    task['stdout'] = stdout
                if stderr is not None:
                    task['stderr'] = stderr
            else:
                # Task object
                if stdout is not None:
                    task.stdout = stdout
                if stderr is not None:
                    task.stderr = stderr

    @staticmethod
    def run_shell_command(args: str, task=None) -> bool:
        """Runs a shell command with the given arguments."""
        try:
            result = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
            
            # Capture output in task if provided
            Tools._set_task_output(task, stdout=result.stdout, stderr=result.stderr)
            
            if result.stdout:
                print(f"Output: {result.stdout}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out after 30 seconds"
            Tools._set_task_output(task, stderr=error_msg)
            print(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error running shell command: {e}"
            Tools._set_task_output(task, stderr=error_msg)
            print(error_msg)
            return False
    
    @staticmethod
    def query_screen_internlm(query: str, task=None, api_url: str = "http://localhost:23333", api_key: str = None) -> str:
        """Ask questions about the screen using InternLM vision model via OpenAI-compatible API."""
        try:
            # Take a screenshot
            screenshot = pyautogui.screenshot()
            
            # Compress screenshot and convert to base64
            import io
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format='JPEG', quality=75, optimize=True)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Prepare the request to InternLM API (OpenAI-compatible)
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Format query with bbox instruction if needed
            formatted_query = f"{query}"
            
            payload = {
                "model": "internvl3.5-241b-a28b",  # This will be auto-detected by the server
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": formatted_query},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]
                    }
                ],
                "stream": False
            }
            
            response = requests.post(f"{api_url}/v1/chat/completions", json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                print(f"InternLM vision model response: {answer}")
                
                # Attach output to task if provided
                Tools._set_task_output(task, stdout=answer)
                
                return answer
            else:
                error_msg = f"InternLM API error: {response.status_code} - {response.text}"
                print(error_msg)
                error_response = json.dumps({"error": error_msg})
                
                # Attach error to task if provided
                Tools._set_task_output(task, stderr=error_msg)
                
                return error_response
                
        except Exception as e:
            error_msg = f"Error in query_screen_internlm: {e}"
            print(error_msg)
            error_response = json.dumps({"error": error_msg})
            
            # Attach error to task if provided
            Tools._set_task_output(task, stderr=error_msg)
            
            return error_response

    @staticmethod 
    def query_vision_model(query: str, image_path: str = None, task=None, 
                          api_type: str = "ollama", api_url: str = None, 
                          api_key: str = None, model: str = None) -> str:
        """Generic method to query vision models with different API providers."""
        try:
            # Use screenshot if no image path provided
            if image_path:
                with Image.open(image_path) as img:
                    screenshot = img.copy()
            else:
                screenshot = pyautogui.screenshot()
            
            # Add grid lines to help the model
            width, height = screenshot.size
            draw = ImageDraw.Draw(screenshot)
            
            # Draw 10 vertical grid lines (0.1x apart)
            for i in range(1, 10):
                x = int(width * i * 0.1)
                draw.line([(x, 0), (x, height)], fill='red', width=2)
            
            # Draw 10 horizontal grid lines (0.1x apart) 
            for i in range(1, 10):
                y = int(height * i * 0.1)
                draw.line([(0, y), (width, y)], fill='red', width=2)
            
            # Compress screenshot and convert to base64
            import io
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format='JPEG', quality=75, optimize=True)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Format query with bbox instruction if needed
            formatted_query = f"Instruct: If asked to find/locate/search for something, then just return a point for clicking example output: <action>click(x=0.3797, y=0.7417)</action>. Use the grid lines for estimating the point. The grid divides the screen into a 10x10 grid where each cell represents 10% of the width and height\nQuery: {query}"
            
            if api_type.lower() == "internlm":
                # InternLM API (OpenAI-compatible)
                if not api_url:
                    api_url = os.getenv("INTERNLM_URL", "http://localhost:23333")
                if not model:
                    model = "internlm-chat"
                    
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user", 
                            "content": [
                                {"type": "text", "text": formatted_query},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                            ]
                        }
                    ],
                    "enable_thinking": False,
                    "stream": False
                }
                
                response = requests.post(f"{api_url}/v1/chat/completions", json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                else:
                    error_msg = f"InternLM API error: {response.status_code} - {response.text}"
                    print(error_msg)
                    Tools._set_task_output(task, stderr=error_msg)
                    return json.dumps({"error": error_msg})
                    
            else:
                # Default to Ollama API
                if not api_url:
                    api_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
                if not model:
                    model = "qwen2.5vl:7b"
                
                payload = {
                    "model": model,
                    "prompt": formatted_query,
                    "images": [img_base64],
                    "stream": False
                }
                
                response = requests.post(f"{api_url}/api/generate", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('response', '').strip()
                else:
                    error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                    print(error_msg)
                    Tools._set_task_output(task, stderr=error_msg)
                    return json.dumps({"error": error_msg})
            
            print(f"Vision model response: {answer}")
            Tools._set_task_output(task, stdout=answer)
            return answer
                
        except Exception as e:
            error_msg = f"Error in query_vision_model: {e}"
            print(error_msg)
            error_response = json.dumps({"error": error_msg})
            Tools._set_task_output(task, stderr=error_msg)
            return error_response

    @staticmethod
    def query_screen(query: str, task=None) -> str:
        """Ask questions about the screen using a vision model (defaults to Ollama)."""
        return Tools.query_vision_model(query, task=task, api_type="internlm", api_key="sk-QpCDT6MB54Yz31D6Cuw47puneTT9Yo5M4H61Pm7Nk1fY1CFM", api_url='https://chat.intern-ai.org.cn/api', model="internvl3.5-241b-a28b")

    @staticmethod
    def add(a: Union[int, float], b: Union[int, float], task=None) -> Union[int, float]:
        """
        Add two numbers together.
        
        Args:
            a: First number (integer or float)
            b: Second number (integer or float)
            task: Optional task object to store output
            
        Returns:
            Sum of a and b
            
        Raises:
            TypeError: If inputs are not numeric
        """
        try:
            # Validate inputs are numeric
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                raise TypeError(f"Both arguments must be numbers. Got: a={type(a)}, b={type(b)}")
            
            result = a + b
            print(f"add({a}, {b}) = {result}")
            
            # Store result in task if provided
            Tools._set_task_output(task, stdout=str(result))
            
            return result
            
        except Exception as e:
            error_msg = f"Error in add({a}, {b}): {e}"
            print(error_msg)
            Tools._set_task_output(task, stderr=error_msg)
            raise
