# Kyros - Computer Use Agent (CUA)

A computer-use agent built on a multi-agent architecture, running in a Docker container with VNC access.

## Demo

<iframe src="https://drive.google.com/file/d/1jHft7HIMBlnqR_m5KlwnqszaopXvbhfX/preview" width="640" height="480" allow="autoplay" allowfullscreen></iframe>


## Prerequisites

- Python 3.13+
- uv package manager
- xdotool (for mouse/keyboard control)
- wmctrl (for window management)
- X11 display server
- scrot

### Install system dependencies (Ubuntu/Debian):

```bash
sudo apt-get install xdotool wmctrl
```

## Installation

1. Clone the repository
2. Install dependencies:

```bash
uv sync
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your InternLM API key
```

4. Install playwright dependencies


## Usage

Run the agent with a task description:

```bash
uv run main.py "Your task description here"
```

### Options

- `--api-key`: InternLM API key (or set INTERNLM_API_KEY env var)
- `--base-url`: InternLM API base URL (or set INTERNLM_BASE_URL env var)
- `--max-iterations`: Maximum number of iterations (default: 20)

### Example

```bash
uv run main.py "Open Firefox and navigate to github.com" --max-iterations 10
```

## Architecture

The agent follows a feedback loop:

1. **Gather Context**: Collects messages, actions, observations, screenshots, and active windows
2. **Generate Action**: Uses InternLM API to generate executable Python code calling tools
3. **Execute**: Runs the generated code
4. **Verify**: Compares before/after screenshots to verify success
5. **Repeat**: Continues until task completion or exit

### Available Tools

- `tools.click(x, y)`: Click at relative coordinates (0-1 range)
- `tools.type(text)`: Type text
- `tools.hotkey(keys)`: Press hotkey combination (e.g., 'super+r')
- `tools.bash(cmd)`: Execute bash command
- `tools.exit(message, exitCode)`: Exit the agent loop

## Docker Setup

### Build the Docker Image

```bash
docker build -t kyros-agent .
```

Note: First build may take 10-15 minutes due to desktop environment installation.

### Run with Docker Compose (recommended)

```bash
docker-compose up -d
```

### Run with Docker directly

```bash
docker run -d -p 5901:5901 --name kyros-agent kyros-agent
```

### Connecting via VNC

1. Install a VNC client (e.g., TigerVNC, RealVNC, TightVNC Viewer)
2. Connect to: `localhost:5901`
3. Password: `password`

### Access Container Shell

```bash
docker exec -it kyros-agent bash
```

### Change VNC Password

Edit the Dockerfile and modify the password in the CMD line, then rebuild.

### Workspace

The `agent-workspace` directory is mounted into the container at `/home/dockeruser/workspace` for persistent storage.

### Stopping the Agent

```bash
docker-compose down
# or
docker stop kyros-agent && docker rm kyros-agent
```

## License

MIT
