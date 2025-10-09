import json
import os
import base64
from datetime import datetime
from typing import List, Dict, Any


class SessionLogger:
    """Logs agent sessions to JSON files for learning and analysis"""

    def __init__(self, sessions_dir: str = "sessions"):
        """Initialize session logger

        Args:
            sessions_dir: Directory to store session JSON files
        """
        self.sessions_dir = sessions_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(sessions_dir, f"session_{self.session_id}.json")
        self.screenshots_dir = os.path.join(sessions_dir, f"session_{self.session_id}_screenshots")

        # Create directories if they don't exist
        os.makedirs(sessions_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

        self.session_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "task": None,
            "model": None,
            "iterations": 0,
            "exit_code": None,
            "context": []
        }
        self.screenshot_counter = 0

    def set_task(self, task: str):
        """Set the initial task for the session"""
        self.session_data["task"] = task

    def set_model(self, model: str):
        """Set the model used for the session"""
        self.session_data["model"] = model

    def _save_screenshot(self, base64_data: str) -> str:
        """Save screenshot to file and return relative path

        Args:
            base64_data: Base64-encoded image data (with or without data URI prefix)

        Returns:
            Relative path to saved screenshot file
        """
        # Extract base64 data from data URI if present
        if base64_data.startswith("data:"):
            base64_str = base64_data.split(",", 1)[1]
        else:
            base64_str = base64_data

        # Generate filename
        self.screenshot_counter += 1
        filename = f"screenshot_{self.screenshot_counter:04d}.jpg"
        filepath = os.path.join(self.screenshots_dir, filename)

        # Decode and save
        img_data = base64.b64decode(base64_str)
        with open(filepath, 'wb') as f:
            f.write(img_data)

        # Return relative path
        return os.path.join(f"session_{self.session_id}_screenshots", filename)

    def _process_context(self, context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process context to extract and save screenshots

        Args:
            context: Raw context array with base64 screenshots

        Returns:
            Processed context with screenshot references
        """
        processed_context = []

        for item in context:
            item_copy = item.copy()

            # Handle observation items with screenshots
            if item["type"] == "observation" and isinstance(item["content"], dict):
                if "screenshot" in item["content"]:
                    screenshot_path = self._save_screenshot(item["content"]["screenshot"])
                    item_copy["content"] = item["content"].copy()
                    item_copy["content"]["screenshot"] = screenshot_path

            processed_context.append(item_copy)

        return processed_context

    def save_context(self, context: List[Dict[str, Any]], iteration: int = 0):
        """Save current context to session data and write to disk

        Args:
            context: Current context array
            iteration: Current iteration number
        """
        self.session_data["context"] = self._process_context(context)
        self.session_data["iterations"] = iteration

        # Write to file immediately for real-time logging
        with open(self.session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)

    def finalize_session(self, exit_code: int):
        """Finalize and save the session

        Args:
            exit_code: Exit code of the session
        """
        self.session_data["end_time"] = datetime.now().isoformat()
        self.session_data["exit_code"] = exit_code

        # Write to file
        with open(self.session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)

        print(f"\n📁 Session saved to: {self.session_file}")
        print(f"📸 Screenshots saved to: {self.screenshots_dir}")

    def save_checkpoint(self, iteration: int):
        """Save incremental checkpoint during session

        Args:
            iteration: Current iteration number
        """
        checkpoint_file = os.path.join(
            self.sessions_dir,
            f"session_{self.session_id}_checkpoint_{iteration}.json"
        )

        with open(checkpoint_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)
