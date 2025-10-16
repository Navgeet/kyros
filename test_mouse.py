#!/usr/bin/env python3
"""
Test mouse simulation in Docker environment
This script moves the mouse in a circular pattern
"""

import time
import math
import pyautogui

# Disable PyAutoGUI's failsafe (which requires mouse to corner to abort)
pyautogui.FAILSAFE = False

def draw_circle(center_x, center_y, radius, duration=10):
    """Draw a circle with the mouse cursor"""
    print(f"Drawing circle at ({center_x}, {center_y}) with radius {radius}")

    steps = 100
    for i in range(steps):
        angle = (2 * math.pi * i) / steps
        x = int(center_x + radius * math.cos(angle))
        y = int(center_y + radius * math.sin(angle))

        pyautogui.moveTo(x, y, duration=duration/steps)
        time.sleep(duration/steps)

def test_mouse():
    """Test various mouse movements"""
    print("Testing mouse simulation...")
    print(f"Screen size: {pyautogui.size()}")

    # Get screen dimensions
    width, height = pyautogui.size()
    center_x = width // 2
    center_y = height // 2

    # Test 1: Move to center
    print("\n1. Moving to center...")
    pyautogui.moveTo(center_x, center_y, duration=1)
    time.sleep(1)

    # Test 2: Draw a circle
    print("\n2. Drawing a circle...")
    draw_circle(center_x, center_y, 100, duration=5)

    # Test 3: Move to corners
    print("\n3. Moving to corners...")
    corners = [
        (100, 100),           # Top-left
        (width-100, 100),     # Top-right
        (width-100, height-100),  # Bottom-right
        (100, height-100),    # Bottom-left
    ]

    for i, (x, y) in enumerate(corners, 1):
        print(f"   Corner {i}: ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.5)
        time.sleep(0.5)

    # Test 4: Return to center and click
    print("\n4. Returning to center and clicking...")
    pyautogui.moveTo(center_x, center_y, duration=1)
    pyautogui.click()

    print("\nMouse simulation test complete!")

if __name__ == "__main__":
    test_mouse()
