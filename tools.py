import subprocess
import pyautogui
import time
from dataclasses import dataclass
from typing import Optional
import os

# Try to import Xlib for mouse operations
try:
    import Xlib.display
    import Xlib.X
    import Xlib.ext.xtest
    XLIB_AVAILABLE = True
except ImportError:
    XLIB_AVAILABLE = False


@dataclass
class ExitException(Exception):
    """Exception to signal agent should exit"""
    message: str
    exit_code: int


def click(x: float, y: float, button: int = 1, clicks: int = 1) -> dict:
    """Click at relative coordinates (0-1 range)

    Args:
        x: Relative x coordinate (0-1 range)
        y: Relative y coordinate (0-1 range)
        button: Mouse button (1=left, 2=middle, 3=right)
        clicks: Number of clicks (1=single, 2=double, etc.)
    """
    if not XLIB_AVAILABLE:
        return {
            "stdout": "",
            "stderr": "Xlib not available",
            "exitCode": -1
        }

    try:
        display = Xlib.display.Display(os.environ.get('DISPLAY', ':0'))
        screen = display.screen()
        width = screen.width_in_pixels
        height = screen.height_in_pixels

        # Convert relative to absolute coordinates
        abs_x = int(x * width)
        abs_y = int(y * height)

        # Move mouse
        root = screen.root
        root.warp_pointer(abs_x, abs_y)
        display.sync()

        # Perform clicks
        for _ in range(clicks):
            Xlib.ext.xtest.fake_input(display, Xlib.X.ButtonPress, button)
            display.sync()
            Xlib.ext.xtest.fake_input(display, Xlib.X.ButtonRelease, button)
            display.sync()
            if clicks > 1:
                time.sleep(0.05)  # Small delay between multiple clicks

        display.close()

        return {
            "stdout": "",
            "stderr": "",
            "exitCode": 0
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": -1
        }


def move(x: float, y: float) -> dict:
    """Move mouse to relative coordinates (0-1 range)

    Args:
        x: Relative x coordinate (0-1 range)
        y: Relative y coordinate (0-1 range)
    """
    if not XLIB_AVAILABLE:
        return {
            "stdout": "",
            "stderr": "Xlib not available",
            "exitCode": -1
        }

    try:
        display = Xlib.display.Display(os.environ.get('DISPLAY', ':0'))
        screen = display.screen()
        width = screen.width_in_pixels
        height = screen.height_in_pixels

        # Convert relative to absolute coordinates
        abs_x = int(x * width)
        abs_y = int(y * height)

        # Move mouse
        root = screen.root
        root.warp_pointer(abs_x, abs_y)
        display.sync()
        display.close()

        return {
            "stdout": "",
            "stderr": "",
            "exitCode": 0
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": -1
        }


def scroll(amount: int) -> dict:
    """Scroll at current mouse position

    Args:
        amount: Scroll amount (positive=down, negative=up)
    """
    # pyautogui.scroll() takes positive for up, negative for down
    # We want positive for down, so negate the amount
    pyautogui.scroll(-amount)

    return {
        "stdout": "",
        "stderr": "",
        "exitCode": 0
    }


def type(text: str) -> dict:
    """Type text using pyautogui"""
    try:
        pyautogui.write(text, interval=0.01)
        return {
            "stdout": "",
            "stderr": "",
            "exitCode": 0
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": -1
        }


def hotkey(keys: str) -> dict:
    """Execute hotkey combination. Example: 'super+r' or 'ctrl+alt+t'"""
    try:
        # Parse the keys and map to pyautogui key names
        key_parts = keys.split('+')

        # Map common key names to pyautogui format
        key_map = {
            'super': 'winleft',
            'ctrl': 'ctrl',
            'alt': 'alt',
            'shift': 'shift'
        }

        # Convert keys to pyautogui format
        mapped_keys = []
        for key in key_parts:
            mapped_keys.append(key_map.get(key.lower(), key.lower()))

        # Execute the hotkey
        pyautogui.hotkey(*mapped_keys)

        return {
            "stdout": "",
            "stderr": "",
            "exitCode": 0
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": -1
        }


def run_shell_command(cmd: str) -> dict:
    """Execute shell command"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exitCode": result.returncode
    }


def wait(n: float) -> dict:
    """Wait for n seconds

    Args:
        n: Number of seconds to wait
    """
    time.sleep(n)

    return {
        "stdout": f"Waited for {n} seconds",
        "stderr": "",
        "exitCode": 0
    }


def exit(message: str, exit_code: int = 0) -> None:
    """Exit the agent loop"""
    raise ExitException(message=message, exit_code=exit_code)
