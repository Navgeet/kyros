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
    try:
        # pyautogui.scroll() takes positive for up, negative for down
        # We want positive for down, so negate the amount
        pyautogui.scroll(-amount)

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


def focus_window(window_id: str) -> dict:
    """Focus a window by its ID using wmctrl and move mouse to center

    Args:
        window_id: Window ID in hexadecimal format (e.g., '0x02400003')
    """
    try:
        # Use wmctrl to activate the window by ID
        # -i -a activates the window by ID
        result = subprocess.run(
            ["wmctrl", "-i", "-a", window_id],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            # Get window geometry to move mouse to center
            # -l -G provides geometry: WID DESKTOP X Y W H
            time.sleep(0.1)  # Small delay to ensure window is focused
            geom_result = subprocess.run(
                ["wmctrl", "-l", "-G"],
                capture_output=True,
                text=True,
                timeout=2
            )

            # Parse geometry for our window
            if geom_result.returncode == 0:
                for line in geom_result.stdout.splitlines():
                    parts = line.split(None, 6)  # Split into max 7 parts
                    if len(parts) >= 6 and parts[0] == window_id:
                        # Extract window position and size
                        x = int(parts[2])
                        y = int(parts[3])
                        width = int(parts[4])
                        height = int(parts[5])

                        # Calculate center of window (absolute coordinates)
                        center_x = x + width // 2
                        center_y = y + height // 2

                        # Get screen dimensions to convert to relative coordinates
                        if XLIB_AVAILABLE:
                            display = Xlib.display.Display(os.environ.get('DISPLAY', ':0'))
                            screen = display.screen()
                            screen_width = screen.width_in_pixels
                            screen_height = screen.height_in_pixels
                            display.close()

                            # Convert to relative coordinates and move mouse
                            rel_x = center_x / screen_width
                            rel_y = center_y / screen_height
                            move(rel_x, rel_y)

                        break

            return {
                "stdout": f"Focused window: {window_id}",
                "stderr": "",
                "exitCode": 0
            }
        else:
            # Try listing windows to provide helpful error
            list_result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return {
                "stdout": "",
                "stderr": f"Could not find window with ID '{window_id}'. Available windows:\n{list_result.stdout}",
                "exitCode": -1
            }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": "wmctrl not installed. Install with: sudo apt-get install wmctrl",
            "exitCode": -1
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": -1
        }


def exit(message: str, exit_code: int = 0) -> None:
    """Exit the agent loop"""
    raise ExitException(message=message, exit_code=exit_code)
