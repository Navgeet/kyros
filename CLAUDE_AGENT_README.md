# Claude Code Agent

An intelligent agent that uses Claude Code in the background to generate and execute Python code for computer use tasks.

## Overview

The Claude Code Agent provides an automated system for computer task automation:

1. **Screenshot Capture**: Takes screenshots of the current screen state
2. **Plan Generation**: Uses Claude Code to analyze screenshots and generate Python code plans
3. **Code Execution**: Executes the generated Python code using the kyros.tools module
4. **Review System**: Uses Claude Code to review execution results and provide feedback
5. **Web Interface**: Provides a user-friendly web interface for interaction

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Request  │    │  Claude Code     │    │  Code Execution │
│                 │────│  Plan Generation │────│  Environment    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Web Frontend   │    │  Screenshot      │    │  Execution      │
│  (Optional)     │    │  Management      │    │  Review         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

### Core Functionality
- **Automated Screenshot Management**: Captures before/after screenshots
- **Claude Code Integration**: Uses Claude Code CLI for intelligent plan generation
- **Safe Code Execution**: Sandboxed execution environment with kyros.tools
- **Plan Review System**: User can approve/reject plans before execution
- **Execution Feedback**: Claude Code reviews execution results

### User Interfaces
- **Web Interface**: Full-featured web UI with real-time updates
- **CLI Interface**: Command-line interface for direct interaction
- **WebSocket Support**: Real-time communication for web interface

### Safety Features
- **Plan Approval**: User must approve plans before execution
- **Sandboxed Execution**: Limited execution environment
- **Error Handling**: Comprehensive error capture and reporting
- **Screenshot Evidence**: Visual proof of execution results

## Installation

### Prerequisites
1. **Claude Code CLI**: Install from [https://docs.anthropic.com/claude/docs/claude-code](https://docs.anthropic.com/claude/docs/claude-code)
2. **Python 3.8+**: Required for the agent
3. **System Dependencies**:
   - `pyautogui` dependencies (varies by OS)
   - `wmctrl` for window management (Linux)

### Setup
```bash
# Install Python dependencies
pip install -r requirements_claude_agent.txt

# Make scripts executable
chmod +x start_claude_agent.py
chmod +x demo_claude_agent.py

# Test installation
python demo_claude_agent.py
```

## Usage

### Quick Start
```bash
# Start web interface (recommended)
python start_claude_agent.py --mode web

# Start CLI interface
python start_claude_agent.py --mode standalone

# Run demo
python demo_claude_agent.py
```

### Web Interface
1. Start the web server: `python start_claude_agent.py --mode web`
2. Open browser to `http://localhost:8000`
3. Enter task descriptions in the chat interface
4. Review and approve generated plans
5. Monitor execution results

### CLI Interface
1. Start CLI: `python start_claude_agent.py --mode standalone`
2. Enter task descriptions when prompted
3. Plans are auto-executed (no approval step in CLI mode)
4. Results are displayed in terminal

## Example Tasks

### Basic Computer Operations
- "take a screenshot"
- "open a new browser tab"
- "focus on chrome window"
- "click on the search box"

### Web Browsing
- "search google for restaurants near me"
- "navigate to wikipedia.org"
- "scroll down the page"

### Application Control
- "open calculator app"
- "open file manager"
- "switch to next window"

### Text Input
- "type 'hello world' and press enter"
- "press ctrl+t to open new tab"
- "use hotkey alt+tab"

## API Reference

### ClaudeCodeAgent Class

```python
from claude_code_agent import ClaudeCodeAgent

# Initialize agent
agent = ClaudeCodeAgent()

# Process a request
result = agent.process_user_request("search google for cats")

# Access results
print(f"Success: {result['execution']['success']}")
print(f"Review: {result['review']}")
```

### Key Methods

- `take_screenshot(name=None)`: Capture screen
- `generate_plan_with_claude_code(request, screenshot)`: Generate plan
- `execute_generated_code(plan)`: Execute code
- `review_execution_with_claude_code(plan, result, screenshot)`: Review results
- `process_user_request(request)`: End-to-end processing

## Configuration

### Agent Configuration
```python
# Custom Claude Code path
agent = ClaudeCodeAgent(claude_code_path="/path/to/claude")
```

### Web Server Configuration
```python
# Custom host/port
server = ClaudeCodeWebServer(host="0.0.0.0", port=8080)
```

### Command Line Options
```bash
# Custom host/port for web mode
python start_claude_agent.py --mode web --host 0.0.0.0 --port 8080

# Skip dependency checks
python start_claude_agent.py --skip-checks
```

## Development

### Project Structure
```
├── claude_code_agent.py        # Main agent class
├── claude_code_web_server.py   # Web server implementation
├── start_claude_agent.py       # Startup script
├── demo_claude_agent.py        # Demo and testing
├── requirements_claude_agent.txt  # Python dependencies
└── screenshots/                # Screenshot storage
```

### Adding New Tools
1. Add tool to `tools.py` in kyros.tools module
2. Update tool documentation in prompts
3. Test with agent

### Extending the Web Interface
- Modify HTML/CSS/JavaScript in `claude_code_web_server.py`
- Add new WebSocket message types
- Implement corresponding handlers

## Troubleshooting

### Common Issues

**"Claude Code CLI not found"**
- Install Claude Code CLI
- Verify `claude --version` works
- Check PATH configuration

**"Screenshot failed"**
- Install pyautogui dependencies
- Check display permissions
- Verify X11/Wayland setup (Linux)

**"Plan generation failed"**
- Check Claude Code authentication
- Verify network connectivity
- Check screenshot file permissions

**"Code execution failed"**
- Check Python environment
- Verify kyros.tools module
- Review generated code for errors

### Debug Mode
```bash
# Run with verbose output
python start_claude_agent.py --mode standalone --skip-checks
```

### Log Files
- Agent logs execution details to console
- Web server logs to uvicorn output
- Screenshots saved to `screenshots/` directory

## Security Considerations

- **Code Review**: Always review generated code before approval
- **Sandboxed Environment**: Code execution is limited to kyros.tools
- **Screenshot Privacy**: Screenshots may contain sensitive information
- **Network Access**: Claude Code requires internet connectivity

## Performance Tips

- **Screenshot Quality**: Lower quality screenshots process faster
- **Plan Complexity**: Simpler tasks generate more reliable plans
- **Network Latency**: Local Claude Code setup reduces delays
- **Resource Usage**: Monitor memory usage for long sessions

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

See project license for terms and conditions.

## Support

- Check demo script for basic functionality testing
- Review troubleshooting section for common issues
- Create issues for bugs or feature requests

---

Built with ❤️ using Claude Code and Python