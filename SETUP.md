# Kyros Setup Guide

This guide will help you set up the Kyros AutoGLM agent with all required dependencies.

## Quick Start with uv

If you're using `uv` (recommended for fast dependency management):

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install -y wmctrl x11-utils xprop xwininfo at-spi2-core python3-gi gir1.2-atspi-2.0

# 2. Install Python dependencies with uv
uv sync

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your InternLM API settings

# 4. Run the working example
uv run working_example.py
```

## Manual Setup

### System Dependencies (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    wmctrl \
    x11-utils \
    xprop \
    xwininfo \
    at-spi2-core \
    python3-gi \
    gir1.2-atspi-2.0 \
    scrot
```

### Python Dependencies

#### With uv (recommended)
```bash
uv sync
```

#### With pip
```bash
pip install -e .
# or
pip install pillow pyautogui psutil requests
```

### Environment Configuration

Create a `.env` file:

```bash
# InternLM API Configuration
INTERNLM_API_URL=http://localhost:23333
INTERNLM_API_KEY=your_api_key_here

# Optional: Display settings for headless operation
# DISPLAY=:99
```

## Usage

### Running the Examples

#### Working Example (with real implementations)
```bash
# With uv
uv run working_example.py

# With pip
python working_example.py

# With custom task
uv run working_example.py "Open a text editor and type hello world"
```

#### Original Mock Example
```bash
# With uv
uv run example_usage.py

# With pip
python example_usage.py
```

### Testing Individual Components

#### Test Desktop Observation
```bash
uv run desktop_observation.py
```

#### Test Action Execution
```bash
uv run action_execution.py
```

#### Test LLM Integration
```bash
uv run python -c "from llm_integration import create_internlm_function; print('LLM integration ready')"
```

## Components Implemented

✅ **LLM Integration** (`llm_integration.py`)
- InternLM API integration based on your `generate_text_plan.py`
- Supports image input and streaming
- Configurable API URL and authentication

✅ **Desktop Observation** (`desktop_observation.py`)
- Screenshot capture using pyautogui
- Accessibility tree via AT-SPI
- Running applications detection
- Active window tracking
- Application-specific context

✅ **Action Execution** (`action_execution.py`)
- Safe Python code execution
- PyAutoGUI action processing
- Coordinate bounds checking
- Special command handling (WAIT, DONE, FAIL)
- Error handling and recovery

✅ **Updated Agent** (existing `autoglm/` files)
- Integrated with new components
- Accessibility tree processing
- Image and context handling

## InternLM Server Setup

Make sure your InternLM server is running and accessible:

```bash
# Example: Start InternLM server (adjust as needed)
# This depends on your InternLM setup
python -m internlm.serve --port 23333 --model internvl3.5-241b-a28b
```

## Troubleshooting

### Permission Issues
```bash
# If you get permission errors, ensure you're in a graphical session
echo $DISPLAY  # Should show something like :0

# For remote sessions, you might need:
export DISPLAY=:0
```

### Accessibility Tree Issues
```bash
# If accessibility tree is empty:
systemctl --user restart at-spi-dbus-bus

# Check if AT-SPI is working:
atspi-tree
```

### Headless Operation
```bash
# For headless operation, use Xvfb:
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Then run your commands
uv run working_example.py
```

### Missing Dependencies
```bash
# Check what's missing:
uv run desktop_observation.py
uv run action_execution.py

# Install missing system packages:
sudo apt-get install <missing-package>
```

## Development

### Code Structure
```
kyros/
├── autoglm/                    # Original agent code
│   ├── agent.py               # Main KyrosAgent class
│   └── prompt/                # Prompt handling
├── llm_integration.py         # InternLM API integration
├── desktop_observation.py     # Desktop state capture
├── action_execution.py        # Action execution system
├── working_example.py         # Complete working example
├── example_usage.py           # Original mock example
└── pyproject.toml            # Project configuration
```

### Adding New Features

1. **New LLM Provider**: Extend `llm_integration.py`
2. **New Actions**: Add to `action_execution.py`
3. **New Observations**: Extend `desktop_observation.py`
4. **New Applications**: Add tools to `autoglm/prompt/`

## Security Notes

- Actions are executed in a restricted environment
- Coordinate bounds checking prevents off-screen actions
- Safe execution context limits available functions
- Always review generated actions before execution in production

## Performance Tips

- Use `with_image=False` if you don't need visual input
- Reduce `a11y_tree_max_items` for faster processing
- Use streaming for real-time LLM responses
- Consider image resizing for faster processing