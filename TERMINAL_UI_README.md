# Terminal UI - Claude Code-like Interface

This implementation adds a Claude Code-like terminal interface to the Kyros agent system, as described in CLAUDE.md.

## Features

### 1. ASCII Art Banner
When running tasks from the CLI, the system displays an ASCII art banner:

```
╦╔═╦ ╦╦═╗╔═╗╔═╗
╠╩╗╚╦╝╠╦╝║ ║╚═╗
╩ ╩ ╩ ╩╚═╚═╝╚═╝

Kyros Agent System
Multi-agent orchestrator with vision capabilities
```

### 2. In-Place Refreshing Output
Agent outputs refresh in-place, keeping the terminal clean and organized. The UI uses ANSI escape codes to:
- Clear previous lines
- Update content without scrolling
- Show real-time streaming of LLM responses

### 3. Hierarchical Agent Display
The interface shows the agent hierarchy clearly:

```
Boss: I'll help you search for information. Let me delegate this to the GUI agent.

|__GUI: # Click on search box
       ```python
       tools.click(0.5, 0.5)
       tools.type("search query")
       ```
```

The format shows:
- **Boss agent** in green with no indentation
- **Sub-agents** indented with `|__` prefix and colored by type:
  - GUI: Blue
  - Shell: Yellow
  - Browser: Magenta
  - Research: Cyan
  - XPath: White

### 4. Code Block Formatting
Code blocks in agent outputs are automatically formatted with:
- Proper indentation (3 spaces)
- Dimmed color for code fence markers
- Clear separation from regular text

### 5. Action Feedback
Actions are displayed with visual feedback:
- `→ Action description` for executing actions
- `✓ Action completed` in green for success
- `✗ Action failed: error` in red for failures

### 6. Task Status
Clear task boundaries with:
- Task submission banner
- Task completion banner with results
- Color-coded status indicators

## Usage

### Running with Terminal UI (Default for CLI)

```bash
python main.py --task "Your task here"
```

The terminal UI is automatically enabled when using the `--task` flag.

### Disabling Terminal UI

```bash
python main.py --task "Your task here" --no-ui
```

### Testing the UI

Run the test script to see a simulated workflow:

```bash
python test_terminal_ui.py
```

### Running without CLI (Web Interface)

```bash
python main.py
```

This starts the WebSocket server without terminal UI formatting, suitable for the web frontend.

## Architecture

### Components

1. **terminal_ui.py**
   - `TerminalUI` class handles all terminal formatting
   - Event handler processes WebSocket events
   - Methods for formatting different agent outputs
   - In-place update mechanism using ANSI codes

2. **main.py** (Modified)
   - Added `use_terminal_ui` flag
   - Integrated terminal UI event listener
   - Shows banner for CLI tasks
   - Delegates user prompts to terminal UI

3. **websocket_server.py** (Modified)
   - Added event listener mechanism
   - Broadcasts events to terminal UI
   - Supports both WebSocket clients and local listeners

### Event Flow

```
Agent Action
    ↓
WebSocket Broadcast
    ↓
Event Listeners (Terminal UI)
    ↓
Terminal Display Update
```

## Event Types Handled

The terminal UI handles these WebSocket event types:

- `task_submitted` - Task starts
- `boss_response` - Boss agent responds
- `delegation` - Boss delegates to sub-agent
- `llm_call_start` - LLM call begins
- `llm_content_chunk` - Streaming LLM response
- `llm_call_end` - LLM call completes
- `action_execute` - Action being executed
- `action_result` - Action result
- `task_completed` - Task finishes

## Dependencies

Added `colorama>=0.4.6` to `pyproject.toml` for cross-platform terminal colors.

## Customization

### Changing Colors

Edit the `agent_colors` dict in `terminal_ui.py`:

```python
agent_colors = {
    'gui': Fore.BLUE,
    'shell': Fore.YELLOW,
    'browser': Fore.MAGENTA,
    # Add or modify colors here
}
```

### Changing ASCII Art

Edit the `ASCII_ART` constant in `terminal_ui.py`:

```python
ASCII_ART = """
Your custom ASCII art here
"""
```

### Adjusting Text Wrapping

Modify the `width` parameters in `format_boss_message()` and `format_subagent_message()`:

```python
wrapped = textwrap.fill(content, width=76, ...)  # Change 76 to your preferred width
```

## Compatibility

- Works on Linux, macOS, and Windows (via colorama)
- Requires terminal with ANSI escape code support
- Best viewed in terminals with at least 80 columns

## Future Enhancements

Potential improvements:
- Add progress bars for long-running operations
- Show token usage statistics
- Display screenshots inline (for supported terminals)
- Add keyboard shortcuts for interaction
- Save session transcripts with formatting
