#!/bin/bash
# Helper script to run the Kyros agent inside the Docker container

# Check if .env file exists, if not copy from example
if [ ! -f /home/dockeruser/kyros/.env ]; then
    echo "No .env file found. Please create one with your API keys."
    echo "You can copy from .env.example:"
    echo "  cp /home/dockeruser/kyros/.env.example /home/dockeruser/kyros/.env"
    exit 1
fi

# Set DISPLAY for X11
export DISPLAY=:1

# Navigate to kyros directory
cd /home/dockeruser/kyros

# Run the agent with the provided task
if [ -z "$1" ]; then
    echo "Usage: run_agent.sh \"Your task description\""
    echo "Example: run_agent.sh \"Open Firefox and navigate to github.com\""
    exit 1
fi

# Run the agent
uv run main.py "$@"
