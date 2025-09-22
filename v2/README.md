# Conversational Planning Agent V2

A new agent that carries out conversations with users using a web frontend, supporting iterative plan development and improvement through user feedback.

## Features

### Two-Phase Planning Workflow

1. **High-Level Text Planning**
   - Generate descriptive text plans from user requests
   - Allow user approval/rejection of plans
   - Support plan improvement based on user feedback
   - Enable complete replanning when needed

2. **Low-Level Code Generation**
   - Convert approved text plans to executable Python code
   - Allow user approval/rejection of generated code
   - Support code improvement based on user feedback
   - Enable code regeneration when needed

### Interactive Web Interface

- Real-time conversation via WebSockets
- Step-by-step approval workflow
- Feedback collection and incorporation
- Plan and code review interfaces
- Session management

## Setup

### Prerequisites

```bash
# Install required packages
pip install fastapi uvicorn websockets

# Set environment variables
export INTERNLM_API_KEY='your-api-key-here'
export INTERNLM_API_URL='http://localhost:23333'  # Optional, defaults to localhost:23333
```

### Optional Configuration

```bash
export AGENT_HOST='localhost'    # Default: localhost
export AGENT_PORT='8001'         # Default: 8001
```

## Usage

### Starting the Agent

```bash
# From the v2 directory
python start_agent_v2.py

# Or run the agent directly
python agent_v2.py
```

The agent will be available at: http://localhost:8001

### Workflow

1. **Initial Request**: Describe what you want to accomplish
2. **Text Plan Review**: Review the generated high-level plan
   - ✅ Approve to proceed to code generation
   - ❌ Provide feedback for improvements
   - 🔄 Request a completely new plan
3. **Code Review**: Review the generated Python code
   - ✅ Approve to complete the task
   - ❌ Provide feedback for improvements
   - 🔄 Generate new code from the same plan
4. **Completion**: Download or execute the final code

### Example Conversation Flow

```
User: "Help me create a simple calculator"

Agent: [Generates text plan]
"1. Create a function to handle basic math operations
 2. Add input validation
 3. Create a simple CLI interface"

User: [Approves plan]

Agent: [Generates Python code]
```python
def calculator():
    # Implementation here
    pass
```

User: [Provides feedback] "Add support for floating point numbers"

Agent: [Improves code based on feedback]
```

## Architecture

### Core Components

- **ConversationalPlanningAgent**: Main web server and conversation manager
- **WebSocketManager**: Handles real-time communication
- **Session Management**: Tracks conversation state and progress
- **Integration Modules**: Uses existing planning scripts

### Planning Integration

The agent integrates with existing planning modules:
- `generate_text_plan.py`: High-level text plan generation
- `refine_plan.py`: Plan improvement and refinement
- `plan_to_code.py`: Code generation from text plans
- `improve_plan_feedback.py`: Feedback-based improvements

### Session States

- `greeting`: Initial user request
- `text_plan_generation`: Generating high-level plan
- `text_plan_approval`: Waiting for plan approval
- `text_plan_feedback`: Collecting plan feedback
- `code_generation`: Generating Python code
- `code_approval`: Waiting for code approval
- `code_feedback`: Collecting code feedback
- `completed`: Task completed successfully

## API Endpoints

### WebSocket Messages

#### Client → Server

```json
// User message
{"type": "user_message", "content": "Your request"}

// Plan/code approval
{"type": "approval", "approved": true/false}

// Provide feedback
{"type": "feedback", "content": "Your feedback"}

// Request replanning
{"type": "replan", "plan_type": "text|code"}
```

#### Server → Client

```json
// Text plan review
{"type": "text_plan_review", "plan": "...", "message": "..."}

// Code review
{"type": "code_review", "code": "...", "message": "..."}

// Request feedback
{"type": "feedback_request", "plan_type": "text|code", "message": "..."}

// Task completion
{"type": "completion", "final_plan": "...", "final_code": "..."}
```

## Comparison with V1

### V1 Agent
- Single-step plan generation and execution
- Screenshot-based automation
- Manual approval for execution only

### V2 Agent
- Two-phase planning workflow
- Conversational interface with feedback loops
- Iterative improvement at both plan and code levels
- Session-based state management
- Complete replanning capabilities

## Future Enhancements

- Code execution and testing
- Plan versioning and history
- Multi-user session support
- Plan templates and libraries
- Integration with external tools and APIs
- Export functionality for plans and code