#!/usr/bin/env python3
"""
Test script to verify AT-SPI accessibility functionality.
"""

import subprocess
import sys

def test_atspi_command():
    """Test if atspi-tree command is available."""
    try:
        result = subprocess.run(['atspi-tree'], capture_output=True, timeout=3)
        print(f"atspi-tree command: return code {result.returncode}")
        if result.stdout:
            print(f"stdout (first 200 chars): {result.stdout.decode()[:200]}")
        if result.stderr:
            print(f"stderr: {result.stderr.decode()[:200]}")
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ atspi-tree command not found")
        return False
    except subprocess.TimeoutExpired:
        print("⏰ atspi-tree command timed out")
        return False

def test_python_atspi():
    """Test if Python AT-SPI bindings are available."""
    try:
        result = subprocess.run([
            'python3', '-c',
            '''
import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi
print("Python AT-SPI bindings: OK")
desktop = Atspi.get_desktop(0)
if desktop:
    print(f"Desktop applications: {desktop.get_child_count()}")
else:
    print("Could not get desktop")
'''
        ], capture_output=True, timeout=5)

        print(f"Python AT-SPI test: return code {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout.decode()}")
        if result.stderr:
            print(f"stderr: {result.stderr.decode()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Python AT-SPI test failed: {e}")
        return False

def test_dbus_service():
    """Test if AT-SPI D-Bus service is running."""
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', 'at-spi-dbus-bus'],
                              capture_output=True, timeout=2)
        status = result.stdout.decode().strip()
        print(f"AT-SPI D-Bus service status: {status}")
        return status == "active"
    except Exception as e:
        print(f"Could not check D-Bus service: {e}")
        return False

def test_alternative_commands():
    """Test alternative accessibility commands."""
    commands = [
        ['accerciser', '--version'],
        ['python3', '-c', 'import pyatspi; print("pyatspi available")'],
        ['gsettings', 'get', 'org.gnome.desktop.interface', 'toolkit-accessibility']
    ]

    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            print(f"{' '.join(cmd[:2])}: {result.returncode == 0}")
            if result.stdout:
                print(f"  output: {result.stdout.decode().strip()[:100]}")
        except Exception as e:
            print(f"{' '.join(cmd[:2])}: Not available ({e})")

def main():
    print("🔍 Testing AT-SPI Accessibility Support")
    print("=" * 40)

    print("\n1. Testing atspi-tree command:")
    test_atspi_command()

    print("\n2. Testing Python AT-SPI bindings:")
    test_python_atspi()

    print("\n3. Testing D-Bus service:")
    test_dbus_service()

    print("\n4. Testing alternative commands:")
    test_alternative_commands()

    print("\n💡 Troubleshooting tips:")
    print("- If accessibility is not working, try: systemctl --user restart at-spi-dbus-bus")
    print("- Enable accessibility in GNOME: gsettings set org.gnome.desktop.interface toolkit-accessibility true")
    print("- Check if running in a proper desktop session (not SSH without X forwarding)")

if __name__ == "__main__":
    main()