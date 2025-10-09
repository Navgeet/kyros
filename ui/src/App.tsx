import React, { useState, useEffect, useRef } from 'react';
import './App.css';

interface LLMCall {
  id: string;
  agentId: string;
  agentType: string;
  timestamp: number;
  messages?: any[];
  model?: string;
  reasoning?: string;
  response?: string;
  screenshot?: string;
  status: 'running' | 'completed';
}

interface TaskSubmission {
  task: string;
}

function App() {
  const [task, setTask] = useState('');
  const [llmCalls, setLlmCalls] = useState<LLMCall[]>([]);
  const [selectedCall, setSelectedCall] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const llmCallsRef = useRef<Map<string, LLMCall>>(new Map());

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket(`ws://${window.location.hostname}:8765/ws`);

    websocket.onopen = () => {
      console.log('Connected to WebSocket');
      setConnected(true);
    };

    websocket.onclose = () => {
      console.log('Disconnected from WebSocket');
      setConnected(false);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  const handleWebSocketMessage = (message: any) => {
    const { type, agent_id, agent_type, data } = message;

    switch (type) {
      case 'llm_call_start':
        const newCall: LLMCall = {
          id: `${agent_id}-${Date.now()}`,
          agentId: agent_id,
          agentType: agent_type,
          timestamp: Date.now(),
          messages: data.messages,
          model: data.model,
          reasoning: '',
          response: '',
          status: 'running'
        };
        llmCallsRef.current.set(newCall.id, newCall);
        setLlmCalls(Array.from(llmCallsRef.current.values()));
        break;

      case 'llm_reasoning_chunk':
        const latestCallForReasoning = Array.from(llmCallsRef.current.values())
          .filter(c => c.agentId === agent_id && c.status === 'running')
          .sort((a, b) => b.timestamp - a.timestamp)[0];

        if (latestCallForReasoning) {
          latestCallForReasoning.reasoning = (latestCallForReasoning.reasoning || '') + data.content;
          llmCallsRef.current.set(latestCallForReasoning.id, latestCallForReasoning);
          setLlmCalls(Array.from(llmCallsRef.current.values()));
        }
        break;

      case 'llm_content_chunk':
        const latestCallForContent = Array.from(llmCallsRef.current.values())
          .filter(c => c.agentId === agent_id && c.status === 'running')
          .sort((a, b) => b.timestamp - a.timestamp)[0];

        if (latestCallForContent) {
          latestCallForContent.response = (latestCallForContent.response || '') + data.content;
          llmCallsRef.current.set(latestCallForContent.id, latestCallForContent);
          setLlmCalls(Array.from(llmCallsRef.current.values()));
        }
        break;

      case 'llm_call_end':
        const latestCallForEnd = Array.from(llmCallsRef.current.values())
          .filter(c => c.agentId === agent_id && c.status === 'running')
          .sort((a, b) => b.timestamp - a.timestamp)[0];

        if (latestCallForEnd) {
          latestCallForEnd.status = 'completed';
          // Update with final response and reasoning if provided (for non-streaming mode)
          if (data.response && !latestCallForEnd.response) {
            latestCallForEnd.response = data.response;
          }
          if (data.reasoning && !latestCallForEnd.reasoning) {
            latestCallForEnd.reasoning = data.reasoning;
          }
          llmCallsRef.current.set(latestCallForEnd.id, latestCallForEnd);
          setLlmCalls(Array.from(llmCallsRef.current.values()));
        }
        break;

      case 'screenshot':
        const latestCallForScreenshot = Array.from(llmCallsRef.current.values())
          .filter(c => c.agentId === agent_id)
          .sort((a, b) => b.timestamp - a.timestamp)[0];

        if (latestCallForScreenshot) {
          latestCallForScreenshot.screenshot = data.screenshot;
          llmCallsRef.current.set(latestCallForScreenshot.id, latestCallForScreenshot);
          setLlmCalls(Array.from(llmCallsRef.current.values()));
        }
        break;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!task.trim() || isSubmitting) return;

    setIsSubmitting(true);

    try {
      const response = await fetch(`http://${window.location.hostname}:8765/api/task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ task }),
      });

      if (response.ok) {
        console.log('Task submitted successfully');
        setTask('');
      } else {
        const errorText = await response.text();
        alert(`Failed to submit task: ${response.status} ${response.statusText}\n${errorText}`);
      }
    } catch (error) {
      alert(`Error submitting task: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedCallData = selectedCall
    ? llmCallsRef.current.get(selectedCall)
    : null;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Computer Use Agent</h1>
        <div className={`status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Connected' : '○ Disconnected'}
        </div>
      </header>

      <div className="main-container">
        <div className="task-section">
          <form onSubmit={handleSubmit}>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Enter your task here..."
              rows={4}
              disabled={!connected}
            />
            <button type="submit" disabled={!connected || !task.trim() || isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit Task'}
            </button>
          </form>
        </div>

        <div className="content-section">
          <div className="llm-calls-list">
            <h2>LLM Calls</h2>
            <div className="calls-container">
              {llmCalls.map((call) => (
                <div
                  key={call.id}
                  className={`call-item ${selectedCall === call.id ? 'selected' : ''} ${call.status}`}
                  onClick={() => setSelectedCall(call.id)}
                >
                  <div className="call-header">
                    <span className="agent-type">{call.agentType}</span>
                    <span className="timestamp">
                      {new Date(call.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="call-model">{call.model}</div>
                  <div className="call-status">{call.status}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="llm-call-details">
            {selectedCallData ? (
              <>
                <div className="details-header">
                  <h2>{selectedCallData.agentType}</h2>
                  <span className="model-badge">{selectedCallData.model}</span>
                </div>

                {selectedCallData.screenshot && (
                  <div className="screenshot-section">
                    <h3>Screenshot</h3>
                    <img
                      src={selectedCallData.screenshot}
                      alt="Agent screenshot"
                      className="screenshot"
                    />
                  </div>
                )}

                {selectedCallData.reasoning && (
                  <div className="reasoning-section">
                    <h3>Reasoning</h3>
                    <pre className="reasoning-content">
                      {selectedCallData.reasoning}
                    </pre>
                  </div>
                )}

                {selectedCallData.response && (
                  <div className="response-section">
                    <h3>Response</h3>
                    <pre className="response-content">
                      {selectedCallData.response}
                    </pre>
                  </div>
                )}

                {selectedCallData.messages && (
                  <div className="messages-section">
                    <h3>Messages</h3>
                    <pre className="messages-content">
                      {JSON.stringify(selectedCallData.messages, null, 2)}
                    </pre>
                  </div>
                )}
              </>
            ) : (
              <div className="no-selection">
                <p>Select an LLM call to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
