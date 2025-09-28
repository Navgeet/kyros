#!/bin/bash
"""
Setup script for Kyros AutoGLM agent.
Installs system dependencies and Python packages.
"""

set -e  # Exit on any error

echo "🚀 Setting up Kyros AutoGLM Agent"
echo "=================================="

# Check if running on Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    echo "❌ This setup script is for Ubuntu/Debian systems only"
    echo "Please install dependencies manually for your system"
    exit 1
fi

echo "📦 Installing system dependencies..."

# Update package list
sudo apt-get update

# Install required system packages
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    wmctrl \
    x11-utils \
    xprop \
    xwininfo \
    at-spi2-core \
    python3-gi \
    gir1.2-atspi-2.0 \
    scrot \
    xvfb

echo "🐍 Installing Python dependencies..."

# Install Python packages
pip3 install -r requirements.txt

echo "🔧 Setting up environment..."

# Create .env file template if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# InternLM API Configuration
INTERNLM_API_URL=http://localhost:23333
INTERNLM_API_KEY=your_api_key_here

# Optional: Display settings for headless operation
# DISPLAY=:99
EOF
    echo "📝 Created .env template file"
    echo "Please edit .env with your InternLM API settings"
fi

echo "🔍 Testing installation..."

# Test Python imports
python3 -c "
import pyautogui
import psutil
import PIL
import requests
print('✅ All Python packages imported successfully')
"

# Test system commands
echo "Testing system commands..."
for cmd in wmctrl xprop xwininfo; do
    if command -v $cmd &> /dev/null; then
        echo "✅ $cmd: available"
    else
        echo "❌ $cmd: missing"
    fi
done

echo ""
echo "🎉 Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your InternLM API configuration"
echo "2. Start your InternLM server at the configured URL"
echo "3. Run the example: python3 working_example.py"
echo ""
echo "For manual testing:"
echo "- Test observation: python3 desktop_observation.py"
echo "- Test action execution: python3 action_execution.py"
echo "- Test LLM integration: python3 -c 'from llm_integration import create_internlm_function; print(\"LLM integration ready\")'"
echo ""
echo "Troubleshooting:"
echo "- If you get permission errors, make sure you're in a graphical session"
echo "- If accessibility tree is empty, try: systemctl --user restart at-spi-dbus-bus"
echo "- For headless operation, use Xvfb: Xvfb :99 -screen 0 1920x1080x24 &"