# Kyros V3 Frontend

React frontend for the LangGraph Supervised Planning Agent V3.

## Features

- **Real-time Communication**: WebSocket-based chat interface
- **Interactive Workflows**: Human-in-the-loop plan and code approval
- **Session Management**: Persistent sessions with reconnection support
- **Responsive Design**: Works on desktop and mobile devices
- **TypeScript**: Fully typed for better development experience

## Architecture

- **Components**: Modular React components for different UI parts
- **Hooks**: Custom hooks for WebSocket management
- **Services**: WebSocket service for backend communication
- **Types**: TypeScript definitions for all data structures

## Development

### Prerequisites

- Node.js 16+ and npm
- Running V3 backend server on port 8000

### Setup

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The frontend will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

### Type Check

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

## Usage

1. Start the V3 backend server
2. Open the frontend in your browser
3. Start a conversation with the agent
4. Follow the interactive workflow for plan creation and code generation

## Backend Integration

The frontend communicates with the V3 backend via:

- **WebSocket**: `/ws` endpoint for real-time messaging
- **HTTP API**: REST endpoints for session management and health checks

## Session Management

Sessions are persisted using localStorage and can be resumed after disconnections. The UI shows the current connection status and workflow phase.