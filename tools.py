import pyautogui
import subprocess
import time
import os
from typing import Dict, Any
from PIL import Image
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
    def run_shell_command(args: str) -> bool:
        """Runs a shell command with the given arguments."""
        try:
            result = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                print(f"Output: {result.stdout}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("Command timed out after 30 seconds")
            return False
        except Exception as e:
            print(f"Error running shell command: {e}")
            return False