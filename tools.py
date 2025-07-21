import pyautogui
import subprocess
import time
from typing import Dict, Any

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