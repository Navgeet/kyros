# Kyros

AI Agent with planning and execution capabilities that can interact with computer interfaces through automated screenshot analysis and task decomposition.

## Features

- **Task Planning**: Breaks down complex tasks into manageable subtasks with dependency tracking
- **Computer Vision**: Takes and analyzes screenshots to understand current state
- **Tool Execution**: Executes various tools including mouse clicks, keyboard input, and system commands
- **Web Interface**: React-based frontend for monitoring task execution with visual flow diagrams
- **Streaming Output**: Real-time task execution monitoring

## Architecture

- **Agent** (`agent.py`): Main orchestrator that coordinates planning and execution
- **Planner** (`planner.py`): Creates execution plans from user tasks using LLM reasoning
- **Executor** (`executor.py`): Executes individual tasks and tool calls
- **Web Server** (`web_server.py`): FastAPI server providing REST API and web interface
- **Frontend**: React application for visualizing task execution flows

## Installation

```bash
# Install Python dependencies
uv sync

# Install Node.js dependencies
npm install
```

## Usage

### Web Interface

```bash
# Start the web server
python web_server.py --ollama-url http://localhost:11434 --vllm-url http://localhost:8000 --port 8080

# In another terminal, build the frontend
npm run dev
```
Then open http://localhost:5173 in your browser.

## License

ISC
