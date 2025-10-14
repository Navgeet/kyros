#!/bin/bash
set -e

# Set environment variables
export USER=dockeruser
export HOME=/home/dockeruser

# Clean up any stale VNC lock files
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

# Create VNC password file
echo 'password' | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# Kill any existing VNC server on display :1
vncserver -kill :1 >/dev/null 2>&1 || true

# Start VNC server
vncserver :1 -geometry 1280x800 -depth 24

# Keep container running and tail logs
tail -f ~/.vnc/*.log
