#!/bin/bash
set -e

# Set environment variables
export USER=dockeruser
export HOME=/home/dockeruser
export DISPLAY=:1

# Clean up any stale X lock files
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

# Start Xvfb (virtual framebuffer X server)
echo "Starting Xvfb..."
Xvfb :1 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for X server to start
sleep 2

# Set cursor theme
export XCURSOR_THEME=Adwaita
export XCURSOR_SIZE=24

# Start window manager
echo "Starting xfce4..."
startxfce4 &

# Wait for window manager to start
sleep 3

# Create x11vnc password file
mkdir -p ~/.vnc
x11vnc -storepasswd password ~/.vnc/passwd

# Start x11vnc with software cursor support
echo "Starting x11vnc with software cursor..."
x11vnc -display :1 \
    -rfbport 5901 \
    -shared \
    -forever \
    -cursor arrow \
    -cursorpos \
    -cursor_drag \
    -arrow 20 \
    -rfbauth ~/.vnc/passwd \
    -noxdamage \
    -noxfixes \
    -noxrecord \
    -noxinerama \
    -nocursorshape \
    -verbose &

X11VNC_PID=$!

# Keep cursor active with periodic movement
# (
#   while true; do
#     xdotool mousemove_relative --sync -- 0 0
#     sleep 5
#   done
# ) &

# Wait and log
echo "VNC server ready on port 5901"
echo "Xvfb PID: $XVFB_PID"
echo "x11vnc PID: $X11VNC_PID"

# Keep container running
wait
