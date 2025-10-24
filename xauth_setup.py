"""
X11 authentication setup utility for containers.

This module ensures proper X11 authentication is configured,
eliminating Xlib.xauth warnings.
"""

import os
import subprocess
import sys


def setup_xauthority():
    """
    Setup X11 authentication by creating/updating .Xauthority file.

    This is called automatically on module import or can be called manually.
    """
    try:
        # Get environment variables
        display = os.environ.get('DISPLAY', ':1')
        xauth_file = os.environ.get('XAUTHORITY', os.path.expanduser('~/.Xauthority'))

        # Create empty .Xauthority if it doesn't exist
        if not os.path.exists(xauth_file):
            open(xauth_file, 'a').close()

        # Set proper permissions
        os.chmod(xauth_file, 0o600)

        # Try to generate magic cookie
        try:
            result = subprocess.run(['mcookie'], capture_output=True, text=True, timeout=2)
            mcookie = result.stdout.strip() if result.returncode == 0 else '00000000000000000000000000000000'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            mcookie = '00000000000000000000000000000000'

        # Add authentication entries using xauth
        try:
            subprocess.run(
                ['xauth', 'add', display, '.', mcookie],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            hostname = subprocess.run(['hostname'], capture_output=True, text=True, timeout=2).stdout.strip()
            subprocess.run(
                ['xauth', 'add', f'{hostname}/unix{display}', '.', mcookie],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return True

    except Exception as e:
        # Silently fail - X11 is optional
        return False


# Automatically setup on import
setup_xauthority()
