#!/usr/bin/env python3
"""
Desktop observation functions for Kyros.
Captures screenshots, accessibility tree, and application info on Linux.
"""

import subprocess
import os
import time
import json
from typing import Dict, List, Optional, Tuple
from io import BytesIO
import logging

try:
    import pyautogui
    import psutil
    from PIL import Image
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Please install: pip install pyautogui psutil pillow")


logger = logging.getLogger("kyros.observation")


def capture_screenshot() -> bytes:
    """
    Capture current desktop screenshot.

    Returns:
        bytes: PNG screenshot data
    """
    try:
        screenshot = pyautogui.screenshot()
        buf = BytesIO()
        screenshot.save(buf, format='PNG')
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return b""


def get_accessibility_tree() -> str:
    """
    Get accessibility tree using AT-SPI on Linux.

    Returns:
        str: XML accessibility tree
    """
    try:
        # First try direct Python AT-SPI bindings (most reliable)
        try:
            import gi
            gi.require_version("Atspi", "2.0")
            from gi.repository import Atspi

            tree_lines = []

            def dump_tree(obj, level=0):
                try:
                    if not obj:
                        return

                    name = obj.get_name() or ""
                    role = obj.get_role_name() or ""
                    state_set = obj.get_state_set()
                    states = []
                    if state_set:
                        for i in range(state_set.size()):
                            state = state_set.get_state(i)
                            if state:
                                states.append(state.value_name)

                    # Get bounding box
                    bounds = ""
                    try:
                        component = obj.get_component_iface()
                        if component:
                            rect = component.get_extents(Atspi.CoordType.SCREEN)
                            if rect and rect.width > 0 and rect.height > 0:
                                bounds = f" screencoord=\"({rect.x}, {rect.y})\" size=\"({rect.width}, {rect.height})\""
                    except:
                        pass

                    # Only include visible, named elements or those with bounds
                    if name or bounds or role in ['frame', 'window', 'dialog']:
                        indent = "  " * level
                        state_attrs = f" states=\"{','.join(states)}\"" if states else ""
                        name_attr = f" name=\"{name}\"" if name else ""
                        tree_lines.append(f"{indent}<{role}{name_attr}{bounds}{state_attrs}>")

                        # Recursively process children (limit depth to avoid infinite loops)
                        if level < 10:
                            try:
                                child_count = obj.get_child_count()
                                for i in range(min(child_count, 50)):  # Limit children to avoid too much data
                                    child = obj.get_child_at_index(i)
                                    if child:
                                        dump_tree(child, level + 1)
                            except:
                                pass

                        tree_lines.append(f"{indent}</{role}>")

                except Exception as e:
                    logger.debug(f"Error processing AT-SPI object: {e}")

            # Get desktop and process applications
            desktop = Atspi.get_desktop(0)
            if desktop and desktop.get_child_count() > 0:
                tree_lines.append("<?xml version=\"1.0\"?>")
                tree_lines.append("<accessibility-tree>")

                for i in range(min(desktop.get_child_count(), 20)):  # Limit apps processed
                    app = desktop.get_child_at_index(i)
                    if app:
                        dump_tree(app, 1)

                tree_lines.append("</accessibility-tree>")

                if len(tree_lines) > 3:  # More than just the XML header
                    return "\n".join(tree_lines)

        except Exception as e:
            logger.debug(f"Direct AT-SPI Python bindings failed: {e}")

        # Fallback: Use atspi-tree command if available
        try:
            result = subprocess.run(['atspi-tree'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: Use external Python script for AT-SPI
        try:
            result = subprocess.run(['python3', '-c', '''
import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

def dump_tree(obj, level=0):
    try:
        if not obj:
            return
        name = obj.get_name() or ""
        role = obj.get_role_name() or ""
        if name or role in ["frame", "window", "dialog"]:
            indent = "  " * level
            print(f"{indent}<{role} name=\\"{name}\\">")
            if level < 8:
                for i in range(min(obj.get_child_count(), 30)):
                    child = obj.get_child_at_index(i)
                    if child:
                        dump_tree(child, level + 1)
            print(f"{indent}</{role}>")
    except:
        pass

desktop = Atspi.get_desktop(0)
if desktop:
    print("<?xml version=\\"1.0\\"?>")
    print("<accessibility-tree>")
    for i in range(min(desktop.get_child_count(), 10)):
        app = desktop.get_child_at_index(i)
        if app:
            dump_tree(app, 1)
    print("</accessibility-tree>")
'''], capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout

        except Exception as e:
            logger.debug(f"External AT-SPI script failed: {e}")

        # Final fallback: basic window info
        try:
            result = subprocess.run(['xwininfo', '-root', '-tree'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return f"<!-- Basic window tree (AT-SPI not available) -->\n{result.stdout}"
        except:
            pass

        logger.info("No accessibility tree available - using basic window detection only")
        return ""

    except Exception as e:
        logger.error(f"Failed to get accessibility tree: {e}")
        return ""


def get_running_apps() -> Dict[str, Dict]:
    """
    Get information about currently running applications.

    Returns:
        Dict: Window ID -> app info mapping
    """
    apps = {}
    try:
        # Get window list using wmctrl
        result = subprocess.run(['wmctrl', '-l'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        window_id = parts[0]
                        desktop = parts[1]
                        host = parts[2]
                        title = parts[3]

                        # Get process info for this window
                        try:
                            pid_result = subprocess.run(
                                ['xprop', '-id', window_id, '_NET_WM_PID'],
                                capture_output=True, text=True, timeout=2
                            )
                            if pid_result.returncode == 0 and '=' in pid_result.stdout:
                                pid_str = pid_result.stdout.split('=')[-1].strip()
                                pid = int(pid_str)

                                # Get process name
                                try:
                                    proc = psutil.Process(pid)
                                    app_name = proc.name()
                                except:
                                    app_name = "unknown"
                            else:
                                app_name = "unknown"
                        except:
                            app_name = "unknown"

                        apps[window_id] = {
                            'app_name': app_name,
                            'title': title,
                            'desktop': desktop,
                            'host': host
                        }

    except Exception as e:
        logger.error(f"Failed to get running apps: {e}")

    return apps


def get_active_window() -> Tuple[str, str]:
    """
    Get currently active window ID and application name.

    Returns:
        Tuple[str, str]: (window_id, app_name)
    """
    try:
        # Get active window ID
        result = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and 'window id #' in result.stdout:
            window_id = result.stdout.split('window id #')[-1].strip()
            window_id = window_id.split()[0]  # Get just the hex ID

            # Get window class/name
            try:
                class_result = subprocess.run(
                    ['xprop', '-id', window_id, 'WM_CLASS'],
                    capture_output=True, text=True, timeout=2
                )
                if class_result.returncode == 0 and '=' in class_result.stdout:
                    class_info = class_result.stdout.split('=')[-1].strip()
                    # Extract application name from WM_CLASS
                    if '"' in class_info:
                        app_name = class_info.split('"')[-2]  # Usually the last quoted string
                    else:
                        app_name = "unknown"
                else:
                    app_name = "unknown"
            except:
                app_name = "unknown"

            return window_id, app_name

    except Exception as e:
        logger.error(f"Failed to get active window: {e}")

    return "", ""


def get_current_app() -> str:
    """
    Get name of currently focused application.

    Returns:
        str: Application name
    """
    _, app_name = get_active_window()
    return app_name


def get_app_specific_info(app_name: str = "") -> str:
    """
    Get application-specific information.

    Args:
        app_name: Name of the application

    Returns:
        str: Application context information
    """
    if not app_name:
        app_name = get_current_app()

    info_lines = []

    # Add basic app info
    info_lines.append(f"Application: {app_name}")

    # Get window title
    window_id, _ = get_active_window()
    if window_id:
        try:
            result = subprocess.run(['xprop', '-id', window_id, '_NET_WM_NAME'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and '=' in result.stdout:
                title = result.stdout.split('=')[-1].strip().strip('"')
                info_lines.append(f"Window Title: {title}")
        except:
            pass

    # Add app-specific context based on application type
    try:
        if 'chrome' in app_name.lower() or 'firefox' in app_name.lower():
            # Browser-specific info could go here
            info_lines.append("Application Type: Web Browser")
        elif 'code' in app_name.lower() or 'vim' in app_name.lower():
            info_lines.append("Application Type: Text Editor/IDE")
        elif 'libreoffice' in app_name.lower():
            info_lines.append("Application Type: Office Suite")
        elif 'terminal' in app_name.lower() or 'gnome-terminal' in app_name.lower():
            info_lines.append("Application Type: Terminal")
    except:
        pass

    return '\n'.join(info_lines)


def get_desktop_observation() -> Dict:
    """
    Get complete desktop observation for the agent.

    Returns:
        Dict: Complete observation containing all desktop state information
    """
    logger.info("Capturing desktop observation...")

    # Capture all components
    screenshot = capture_screenshot()
    accessibility_tree = get_accessibility_tree()
    apps = get_running_apps()
    window_id, app_name = get_active_window()
    app_info = get_app_specific_info(app_name)

    observation = {
        "screenshot": screenshot,
        "accessibility_tree": accessibility_tree,
        "apps": apps,
        "cur_window_id": window_id,
        "cur_app": app_name,
        "app_info": app_info,
        "exe_result": ""  # Will be filled by action execution
    }

    logger.info(f"Observation captured - Screenshot: {len(screenshot)} bytes, "
               f"A11y tree: {len(accessibility_tree)} chars, "
               f"Apps: {len(apps)}, Current: {app_name}")

    return observation


def check_dependencies() -> List[str]:
    """
    Check if required system dependencies are available.

    Returns:
        List[str]: List of missing dependencies
    """
    missing = []

    # Check Python packages
    try:
        import pyautogui
    except ImportError:
        missing.append("pyautogui (pip install pyautogui)")

    try:
        import psutil
    except ImportError:
        missing.append("psutil (pip install psutil)")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow (pip install Pillow)")

    # Check system commands
    commands = ['wmctrl', 'xprop', 'xwininfo']
    for cmd in commands:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, timeout=2)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            try:
                subprocess.run([cmd, '--help'], capture_output=True, timeout=2)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing.append(f"{cmd} (sudo apt-get install {cmd})")

    # Check for AT-SPI tools - try multiple approaches
    atspi_available = False

    # Try atspi-tree command
    try:
        result = subprocess.run(['atspi-tree'], capture_output=True, timeout=2)
        if result.returncode == 0 or "Usage:" in result.stderr.decode() or "usage:" in result.stderr.decode():
            atspi_available = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try alternative: check if AT-SPI Python bindings are available
    if not atspi_available:
        try:
            result = subprocess.run([
                'python3', '-c',
                'import gi; gi.require_version("Atspi", "2.0"); from gi.repository import Atspi; print("OK")'
            ], capture_output=True, timeout=5)
            if result.returncode == 0 and "OK" in result.stdout.decode():
                atspi_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Try checking if dbus accessibility services are running
    if not atspi_available:
        try:
            result = subprocess.run(['systemctl', '--user', 'is-active', 'at-spi-dbus-bus'],
                                  capture_output=True, timeout=2)
            if result.returncode == 0 and "active" in result.stdout.decode():
                atspi_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    if not atspi_available:
        missing.append("at-spi2-core or accessibility services (try: sudo apt-get install at-spi2-core python3-gi gir1.2-atspi-2.0)")

    return missing


if __name__ == "__main__":
    # Test the observation system
    logging.basicConfig(level=logging.INFO)

    print("🔍 Checking dependencies...")
    missing = check_dependencies()
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies before running.")
    else:
        print("✅ All dependencies available")

    print("\n📸 Testing desktop observation...")
    obs = get_desktop_observation()

    print(f"Screenshot: {len(obs['screenshot'])} bytes")
    print(f"Accessibility tree: {len(obs['accessibility_tree'])} characters")
    print(f"Current app: {obs['cur_app']}")
    print(f"Running apps: {len(obs['apps'])}")
    print(f"App info: {obs['app_info']}")