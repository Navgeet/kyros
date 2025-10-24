#!/bin/bash
# Setup X11 authentication for the container

set -e

# Get DISPLAY if not set
DISPLAY=${DISPLAY:-:1}
XAUTH_FILE=${XAUTHORITY:-$HOME/.Xauthority}

echo "Setting up X11 authentication..."
echo "DISPLAY: $DISPLAY"
echo "XAUTHORITY: $XAUTH_FILE"

# Check if xauth command is available
if ! command -v xauth &> /dev/null; then
    echo "ERROR: xauth not found. Install x11-xauth package."
    exit 1
fi

# Check if DISPLAY socket exists
if [ ! -S "/tmp/.X11-unix/${DISPLAY#:}" ]; then
    echo "WARNING: X11 display socket not found at /tmp/.X11-unix/${DISPLAY#:}"
    echo "Make sure X server is running."
fi

# Create empty .Xauthority if it doesn't exist
touch "$XAUTH_FILE"

# Generate MIT magic cookie
# This creates a dummy authentication entry for local connections
MCOOKIE=$(mcookie 2>/dev/null || echo "00000000000000000000000000000000")

# Add entries to .Xauthority for local connections
xauth add "$DISPLAY" . "$MCOOKIE" 2>/dev/null || true
xauth add "$(hostname)/unix$DISPLAY" . "$MCOOKIE" 2>/dev/null || true

# Set proper permissions
chmod 600 "$XAUTH_FILE"

echo "✅ X11 authentication setup complete"
echo "   XAUTHORITY=$XAUTH_FILE"
ls -la "$XAUTH_FILE"
