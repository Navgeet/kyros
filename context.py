import base64
import subprocess
from io import BytesIO
from typing import List, Dict, Any
import tempfile
import os
from PIL import Image


class ContextManager:
    """Manages the context array for the agent"""

    def __init__(self):
        self.context: List[Dict[str, Any]] = []

    def add_message(self, from_: str, content: str):
        """Add a message to the context"""
        self.context.append({
            "type": "message",
            "from": from_,
            "content": content
        })

    def add_action(self, content: str, stdout: str = "", stderr: str = "", exit_code: int = 0):
        """Add an action to the context"""
        action = {
            "type": "action",
            "from": "system",
            "content": content
        }
        if stdout or stderr or exit_code != 0:
            action["stdout"] = stdout
            action["stderr"] = stderr
            action["exitCode"] = exit_code
        self.context.append(action)

    def add_observation(self, content: Any):
        """Add an observation to the context"""
        self.context.append({
            "type": "observation",
            "from": "system",
            "content": content
        })

    def get_screenshot_base64(self) -> str:
        """Capture screenshot and return as base64-encoded JPEG using scrot"""
        # Create temp file and close it immediately so scrot can write to it
        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(temp_fd)  # Close the file descriptor immediately

        # Remove the empty file that mkstemp created
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        try:
            # Capture with scrot (ensure DISPLAY is set)
            env = os.environ.copy()
            if 'DISPLAY' not in env:
                env['DISPLAY'] = ':0'

            result = subprocess.run(
                ["scrot", temp_path],
                capture_output=True,
                timeout=2,
                env=env
            )

            if result.returncode != 0:
                raise RuntimeError(f"scrot failed with code {result.returncode}: {result.stderr.decode()}")

            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError(f"scrot did not create screenshot file at {temp_path}")

            # Load and convert to JPEG
            screenshot = Image.open(temp_path)
            buffer = BytesIO()
            screenshot.save(buffer, format="JPEG", quality=75)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_active_windows(self) -> str:
        """Get list of active windows using wmctrl"""
        try:
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout if result.returncode == 0 else "wmctrl not available"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "wmctrl not available"

    def add_current_state(self):
        """Add current screenshot and active windows to context"""
        self.add_observation({
            "active_windows": self.get_active_windows(),
            "screenshot": self.get_screenshot_base64()
        })

    def get_context(self) -> List[Dict[str, Any]]:
        """Get the full context array"""
        return self.context
