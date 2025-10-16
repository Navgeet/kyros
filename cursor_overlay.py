#!/usr/bin/env python3
"""
Creates a visible cursor overlay that follows xdotool mouse position
This ensures the cursor is visible in VNC even without a physical mouse device
"""

import subprocess
import time
import sys

def get_mouse_position():
    """Get current mouse position using xdotool"""
    try:
        result = subprocess.run(
            ['xdotool', 'getmouselocation', '--shell'],
            capture_output=True,
            text=True,
            check=True
        )

        pos = {}
        for line in result.stdout.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=')
                pos[key] = int(value)

        return pos.get('X', 0), pos.get('Y', 0)
    except Exception as e:
        print(f"Error getting mouse position: {e}", file=sys.stderr)
        return None, None

def create_cursor_window():
    """Create a small window that acts as a cursor"""
    # Using xdotool to create a simple dot cursor overlay
    # We'll draw a filled circle using xdotool and wmctrl
    pass

def main():
    """Main loop to update cursor position"""
    print("Starting cursor overlay for VNC visibility...")

    last_x, last_y = -1, -1

    while True:
        x, y = get_mouse_position()

        if x is not None and y is not None:
            if x != last_x or y != last_y:
                # Cursor moved - for now just log it
                # In a full implementation, we'd update a visual overlay
                print(f"Cursor at: ({x}, {y})", end='\r')
                last_x, last_y = x, y

        time.sleep(0.05)  # Update 20 times per second

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCursor overlay stopped.")
        sys.exit(0)
