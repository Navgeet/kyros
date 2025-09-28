# Kyros - Standalone AutoGLM Agent

A standalone implementation of the AutoGLM agent for desktop automation, extracted from the OSWorld project.

## Overview

Kyros is a multimodal agent that can control desktop applications through:
- Visual observation (screenshots)
- Accessibility tree parsing
- Natural language instruction following
- Python code generation for UI interactions

## Features

- **Multimodal Input**: Processes both visual (screenshots) and structural (accessibility tree) information
- **Natural Language Control**: Takes high-level instructions and converts them to specific UI actions
- **Desktop Automation**: Supports clicking, typing, scrolling, drag-and-drop, and application launching
- **Cross-Application**: Works with various desktop applications
- **Modular Design**: Easy to integrate with different LLM backends

## Quick Start

### Installation

```bash
# Clone or copy the kyros directory
# Install dependencies
pip install pillow pyautogui
```

### Basic Usage

```python
from autoglm import KyrosAgent

# Define your LLM function
def my_llm_function(messages):
    # Your LLM call here (OpenAI, Anthropic, etc.)
    pass

# Create agent
agent = KyrosAgent(
    with_image=True,
    gen_func=my_llm_function
)

# Use the agent
instruction = "Open a text editor and type 'Hello World'"
observation = get_desktop_observation()  # Your implementation
response, actions = agent.predict(instruction, observation)
```

### Example

See `example_usage.py` for a complete example with mock functions that you can replace with actual implementations.

## Architecture

### Core Components

1. **KyrosAgent** (`autoglm/agent.py`): Main agent class that orchestrates the entire process
2. **GroundingAgent** (`autoglm/prompt/grounding_agent.py`): Provides basic desktop interaction primitives
3. **Prompt Management** (`autoglm/prompt/procedural_memory.py`): Handles prompt construction and LLM communication
4. **Accessibility Tree Handler** (`autoglm/prompt/accessibility_tree_handle.py`): Processes UI structure information

### Agent Actions

The agent supports these basic actions:

- `Agent.click(coordinates, num_clicks, button_type)`: Click at specified coordinates
- `Agent.type(coordinates, text, overwrite, enter)`: Type text
- `Agent.drag_and_drop(from_coords, to_coords)`: Drag and drop
- `Agent.scroll(coordinates, direction)`: Scroll up or down
- `Agent.open_app(app_name)`: Launch applications
- `Agent.switch_window(window_id)`: Switch between windows
- `Agent.hotkey(keys)`: Press key combinations
- `Agent.wait()`: Wait/pause execution
- `Agent.exit(success)`: End task execution

### Supported Applications

- Chrome (web browsing)
- LibreOffice (Writer, Calc, Impress)
- VS Code
- VLC Media Player
- File Manager
- Terminal
- System Settings
- And more...

## Implementation Requirements

To use Kyros in a real environment, you need to implement:

### 1. LLM Integration

```python
def your_llm_function(messages):
    # Example with OpenAI
    import openai
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=1000
    )
    return response.choices[0].message.content
```

### 2. Desktop Observation

```python
def get_desktop_observation():
    return {
        "screenshot": capture_screenshot(),  # PNG bytes
        "accessibility_tree": get_accessibility_tree(),  # XML string
        "apps": get_running_apps(),  # Dict of app info
        "cur_window_id": get_active_window(),  # Window ID
        "cur_app": get_current_app(),  # App name
        "app_info": get_app_specific_info(),  # App context
    }
```

### 3. Action Execution

```python
def execute_action(action):
    # Execute the generated Python code
    # Handle special commands (WAIT, DONE, FAIL)
    # Return execution result
    pass
```

## Platform Support

Currently designed for **Linux (Ubuntu)** with:
- AT-SPI accessibility framework
- X11 window system
- PyAutoGUI for automation

## Dependencies

- `pillow`: Image processing
- `pyautogui`: Desktop automation (you'll need to install this)
- `python >= 3.7`

## Limitations

1. **No Tool Integration**: This standalone version doesn't include application-specific tools (like browser automation)
2. **Mock Functions**: The example includes mock functions that need real implementations
3. **Linux Only**: Currently designed for Linux environments
4. **No Error Recovery**: Limited error handling and recovery mechanisms

## Extending Kyros

### Adding New Actions

Add methods to the `GroundingAgent` class with the `@agent_action` decorator:

```python
@agent_action
def my_custom_action(cls, param1: str, param2: int):
    \"\"\"
    Custom action description.

    Args:
        param1 (str): First parameter
        param2 (int): Second parameter
    \"\"\"
    return f"custom_command({param1}, {param2})"
```

### Adding Application Tools

Extend the `tool_list` in the agent and implement tool-specific commands.

## License

This code is derived from the OSWorld project. Please refer to the original project's license terms.

## Contributing

This is a standalone extraction. For improvements to the original AutoGLM agent, contribute to the OSWorld project.

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all required packages are installed
2. **Permission Issues**: Some desktop automation features may require special permissions
3. **Display Issues**: Ensure you have a proper display environment for GUI automation

### Getting Help

1. Check the example usage file
2. Review the original OSWorld documentation
3. Ensure your LLM integration is working correctly

## Acknowledgments

This standalone version is based on the AutoGLM agent from the OSWorld project. Credit goes to the original authors and contributors of OSWorld.