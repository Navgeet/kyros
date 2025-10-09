import subprocess
import pyautogui
import time
from dataclasses import dataclass
from typing import Optional


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
    # Get screen dimensions using xdotool
    result = subprocess.run(
        ["xdotool", "getdisplaygeometry"],
        capture_output=True,
        text=True
    )
    width, height = map(int, result.stdout.strip().split())

    # Convert relative to absolute coordinates
    abs_x = int(x * width)
    abs_y = int(y * height)

    # Build xdotool command
    cmd = ["xdotool", "mousemove", str(abs_x), str(abs_y)]

    # Add click with button and repeat count
    if clicks > 1:
        cmd.extend(["click", "--repeat", str(clicks), str(button)])
    else:
        cmd.extend(["click", str(button)])

    subprocess.run(cmd)

    return {
        "stdout": "",
        "stderr": "",
        "exitCode": 0
    }


def move(x: float, y: float) -> dict:
    """Move mouse to relative coordinates (0-1 range)

    Args:
        x: Relative x coordinate (0-1 range)
        y: Relative y coordinate (0-1 range)
    """
    # Get screen dimensions using xdotool
    result = subprocess.run(
        ["xdotool", "getdisplaygeometry"],
        capture_output=True,
        text=True
    )
    width, height = map(int, result.stdout.strip().split())

    # Convert relative to absolute coordinates
    abs_x = int(x * width)
    abs_y = int(y * height)

    subprocess.run(["xdotool", "mousemove", str(abs_x), str(abs_y)])

    return {
        "stdout": "",
        "stderr": "",
        "exitCode": 0
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
    """Type text using xdotool"""
    subprocess.run(["xdotool", "type", "--", text])

    return {
        "stdout": "",
        "stderr": "",
        "exitCode": 0
    }


def hotkey(keys: str) -> dict:
    """Execute hotkey combination. Example: 'super+r' or 'ctrl+alt+t'"""
    # Parse the keys
    key_parts = keys.split('+')

    # Build xdotool command
    cmd = ["xdotool"]

    # Add keydown for all modifier keys
    for key in key_parts[:-1]:
        cmd.extend(["keydown", key])

    # Add the final key press
    cmd.extend(["key", key_parts[-1]])

    # Add keyup for all modifier keys in reverse order
    for key in reversed(key_parts[:-1]):
        cmd.extend(["keyup", key])

    subprocess.run(cmd)

    return {
        "stdout": "",
        "stderr": "",
        "exitCode": 0
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
