import base64
import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("kyros.agent")


def agent_action(func):
    """Decorator to mark functions as agent actions."""
    func.is_agent_action = True
    return func


switch_window_code = """import subprocess;
import pyautogui;
pyautogui.press('escape');
time.sleep(0.5);
subprocess.run(['wmctrl', '-ia', 'WINDOW_ID'])
subprocess.run(['wmctrl', '-ir', 'WINDOW_ID', '-b', 'add,maximized_vert,maximized_horz'])
print('Switch to WINDOW_ID')"""

launch_app_commands = {
    # Web Browser
    "chrome": "google-chrome --remote-debugging-port=1337",
    # File Manager
    "files": "nautilus",
    # Terminal
    "terminal": 'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus" && gnome-terminal',
    # Utilities
    "gedit": "gedit",
    # Office
    "libreoffice writer": "libreoffice --writer",
    "libreoffice calc": "libreoffice --calc",
    "libreoffice impress": "libreoffice --impress",
    # System
    "settings": 'export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus" && gnome-control-center',
    # Multimedia
    "vlc": "vlc",
    "gimp": "gimp",
    # IDE
    "vs code": "code",
    # Email
    "thunderbird": "thunderbird",
}


class GroundingAgent:
    """Agent that provides basic desktop interaction primitives."""

    relative_coordinate = True

    tool_list = {
        "libreoffice_calc": "CalcTools",
        "libreoffice_impress": "ImpressTools",
        "libreoffice_writer": "WriterTools",
        "code": "CodeTools",
        "vlc": "VLCTools",
        "google_chrome": "BrowserTools",
    }

    @classmethod
    def tool_commands(cls, code: str, tool_name: str):
        """Generate tool-specific commands."""
        command = f"from {tool_name} import *; "
        command += code

        tool_class = cls.tool_list[tool_name]
        command += f"; {tool_class}.print_result()"

        return [
            command,
        ]

    @classmethod
    @agent_action
    def click(
        cls,
        coordinates: List,
        num_clicks: int = 1,
        button_type: str = "left",
    ):
        """
        Click on the element.

        Args:
            coordinates (List): [x, y], Coordinates of the element to click on
                - If relative_coordinate=True: [0.0-1.0, 0.0-1.0] (relative to screen size)
                - If relative_coordinate=False: [pixel_x, pixel_y] (absolute pixels)
            num_clicks (int): number of times to click the element
            button_type (str): which mouse button to press can be "left", "middle", or "right"
        """
        command = ""
        x, y = coordinates

        if cls.relative_coordinate:
            # Convert relative coordinates (0-1) to absolute pixel coordinates
            command += f"""
import pyautogui
screen_width, screen_height = pyautogui.size()
abs_x = int({x} * screen_width)
abs_y = int({y} * screen_height)
pyautogui.click(abs_x, abs_y, clicks={num_clicks}, button={repr(button_type)})
print(f"Click Success at relative ({x}, {y}) -> absolute ({{abs_x}}, {{abs_y}})")"""
        else:
            # Use absolute coordinates directly
            command += f"""pyautogui.click({x}, {y}, clicks={num_clicks}, button={repr(button_type)}); print("Click Success")"""

        return command

    @classmethod
    @agent_action
    def type(
        cls,
        coordinates: Optional[List] = None,
        text: str = "",
        overwrite: bool = False,
        enter: bool = False,
    ):
        """
        Type text into the element.

        Args:
            coordinates (List): [x, y] Coordinates of the element to type into. If not provided, typing will start at the current cursor location.
            text (str): the text to type
            overwrite (bool): Assign it to True if the text should overwrite the existing text, otherwise assign it to False. Using this argument clears all text in an element.
            enter (bool): Assign it to True if the enter key should be pressed after typing the text, otherwise assign it to False.
        """

        command = ""

        if coordinates is not None:
            # Start typing at the center of the element
            x, y = coordinates
            if cls.relative_coordinate:
                command += f"""
import pyautogui
screen_width, screen_height = pyautogui.size()
abs_x = int({x} * screen_width)
abs_y = int({y} * screen_height)
pyautogui.click(abs_x, abs_y); """
            else:
                command += f"pyautogui.click({x}, {y}); "

        if overwrite:
            command += f"pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); "

        command += f"pyautogui.write({repr(text)}); "

        if enter:
            command += "pyautogui.press('enter'); "

        command += "print('Type Success')"

        return command

    @classmethod
    @agent_action
    def drag_and_drop(cls, drag_from_coordinates: List, drop_on_coordinates: List):
        """
        Drag element1 and drop it on element2.

        Args:
            drag_from_coordinates (List): [x, y] Coordinates of element to drag
                - If relative_coordinate=True: [0.0-1.0, 0.0-1.0] (relative to screen size)
                - If relative_coordinate=False: [pixel_x, pixel_y] (absolute pixels)
            drop_on_coordinates (List): [x, y]  Coordinates of element to drop on
                - If relative_coordinate=True: [0.0-1.0, 0.0-1.0] (relative to screen size)
                - If relative_coordinate=False: [pixel_x, pixel_y] (absolute pixels)
        """
        x1, y1 = drag_from_coordinates
        x2, y2 = drop_on_coordinates

        if cls.relative_coordinate:
            command = f"""
import pyautogui
screen_width, screen_height = pyautogui.size()
abs_x1 = int({x1} * screen_width)
abs_y1 = int({y1} * screen_height)
abs_x2 = int({x2} * screen_width)
abs_y2 = int({y2} * screen_height)
pyautogui.moveTo(abs_x1, abs_y1); """
        else:
            command = f"pyautogui.moveTo({x1}, {y1}); "
        if cls.relative_coordinate:
            command += f"pyautogui.dragTo(abs_x2, abs_y2, duration=1.); pyautogui.mouseUp(); "
        else:
            command += f"pyautogui.dragTo({x2}, {y2}, duration=1.); pyautogui.mouseUp(); "
        command += "print('Drag and Drop Success')"

        return command

    @classmethod
    @agent_action
    def scroll(cls, coordinates: List, direction: str):
        """
        Scroll the element in the specified direction.

        Args:
            coordinates (List): [x, y] Coordinates of the element to scroll in
                - If relative_coordinate=True: [0.0-1.0, 0.0-1.0] (relative to screen size)
                - If relative_coordinate=False: [pixel_x, pixel_y] (absolute pixels)
            direction (str): the direction to scroll can be "up" or "down".
        """
        x, y = coordinates
        amount = 100 if direction == "up" else -100

        if cls.relative_coordinate:
            return f"""
import pyautogui
screen_width, screen_height = pyautogui.size()
abs_x = int({x} * screen_width)
abs_y = int({y} * screen_height)
pyautogui.moveTo(abs_x, abs_y)
pyautogui.scroll({amount})
print(f'Scroll Success at relative ({x}, {y}) -> absolute ({{abs_x}}, {{abs_y}})')"""
        else:
            return f"import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.scroll({amount}); print('Scroll Success')"

    @classmethod
    @agent_action
    def open_app(cls, app_name: str):
        """
        Open a specified application.

        App List:
        - chrome
        - files
        - terminal
        - gedit
        - libreoffice writer
        - libreoffice calc
        - libreoffice impress
        - vs code
        - vlc
        - gimp
        - settings
        - thunderbird

        Args:
            app_name (str): Name of the application to open
        """

        app_name = app_name.lower().strip()

        if app_name not in launch_app_commands:
            command = f"print(f'{app_name} is not supported or recognized')"
        else:
            command = {
                "action_type": "OPEN_APP",
                "parameters": {"launch_app_command": launch_app_commands[app_name], "app_name": app_name},
            }

        return command

    @classmethod
    @agent_action
    def switch_window(cls, window_id: str):
        """
        Switch to the window with the given window id.

        Args:
            window_id (str): the window id to switch to from the provided list of open windows
        """
        return switch_window_code.replace("WINDOW_ID", window_id)

    @classmethod
    @agent_action
    def hotkey(cls, keys: List):
        """
        Press a hotkey combination.

        Args:
            keys (List): the keys to press in combination in a list format
                        Common combinations:
                        - ['ctrl', 'c'] for copy
                        - ['ctrl', 'v'] for paste
                        - ['alt', 'f2'] for run dialog (GNOME)
                        - ['super', 'r'] for run dialog (awesome/other WMs)
                        - ['ctrl', 'alt', 't'] for terminal
                        - ['prtsc'] for screenshot
        """
        return f"""
import subprocess
import time

keys = {keys}
print(f'Attempting hotkey combination: {{"+".join(keys)}}')

# Use xdotool keydown/keyup syntax for reliable hotkey execution
try:
    # Map key names to xdotool format
    xdotool_keys = []
    for key in keys:
        if key.lower() in ['super', 'win', 'windows']:
            xdotool_keys.append('super')
        elif key.lower() in ['ctrl', 'control']:
            xdotool_keys.append('ctrl')
        else:
            xdotool_keys.append(key.lower())

    # Build xdotool command using keydown/keyup syntax
    cmd = ['xdotool']

    # Press down all modifier keys first
    for key in xdotool_keys[:-1]:
        cmd.extend(['keydown', key])

    # Press and release the final key
    if len(xdotool_keys) > 0:
        cmd.extend(['key', xdotool_keys[-1]])

    # Release all modifier keys in reverse order
    for key in reversed(xdotool_keys[:-1]):
        cmd.extend(['keyup', key])

    print(f'Executing xdotool command: {{" ".join(cmd)}}')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

    if result.returncode == 0:
        print(f'xdotool hotkey executed successfully: {{"+".join(xdotool_keys)}}')
        time.sleep(0.5)  # Give system time to respond
    else:
        print(f'xdotool failed: {{result.stderr}}')
        raise Exception(f'xdotool returned code {{result.returncode}}')

except FileNotFoundError:
    print('xdotool not available, falling back to pyautogui...')
    # Fallback to pyautogui
    try:
        import pyautogui
        pyautogui_keys = []
        for key in keys:
            if key.lower() in ['super', 'win', 'windows']:
                pyautogui_keys.append('win')
            else:
                pyautogui_keys.append(key)

        pyautogui.hotkey(*pyautogui_keys)
        time.sleep(0.5)
        print(f'PyAutoGUI fallback executed: {{"+".join(pyautogui_keys)}}')
    except Exception as fallback_error:
        print(f'Both xdotool and pyautogui failed: {{fallback_error}}')

except Exception as e:
    print(f'Hotkey execution failed: {{e}}')

print('Hotkey attempt completed')
""".strip()

    @classmethod
    @agent_action
    def quote(cls, content: str):
        """
        Quoting information from the current page for memory. Only you can see the quoted content.

        Args:
            content (str): text summarized or copied from the page for later operation.
        """
        return f'''print("""{content}""")'''

    @classmethod
    @agent_action
    def wait(cls):
        """
        Wait for a while.

        """
        return "WAIT"

    @classmethod
    @agent_action
    def exit(cls, success: bool, message: str = ""):
        """
        End the current task.

        Args:
            success (bool): True if successfully finish a task, otherwise set it False
            message (str): Optional message to log when exiting
        """
        if message:
            exit_code = f"print('{message}'); "
        else:
            exit_code = ""

        if success:
            return exit_code + "DONE"
        else:
            return exit_code + "FAIL"