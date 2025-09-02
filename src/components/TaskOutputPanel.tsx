import { TaskNode } from '../types';

interface TaskOutputPanelProps {
  task: TaskNode | null;
  onClose: () => void;
}

export default function TaskOutputPanel({ task, onClose }: TaskOutputPanelProps) {
  if (!task) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: '300px',
        backgroundColor: '#1F2937',
        color: '#F9FAFB',
        border: '1px solid #374151',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #374151',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#111827',
        }}
      >
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>
          {task.name} - Output
        </h3>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#9CA3AF',
            cursor: 'pointer',
            fontSize: '18px',
            padding: '4px',
          }}
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, display: 'flex' }}>
        <div style={{ flex: 1, padding: '16px', overflow: 'auto', minHeight: 0 }}>
          {/* Show thinking content for LLM tasks (task, plan, user_task) */}
          {task.type !== 'tool_call' && task.thinking_content ? (
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#8B5CF6' }}>LLM Output</h4>
              <pre
                style={{
                  margin: 0,
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  lineHeight: '1.4',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  overflow: 'auto',
                  maxHeight: '200px',
                  color: '#E5E7EB',
                }}
              >
                {task.thinking_content || 'No LLM output available'}
              </pre>
            </div>
          ) : task.type !== 'tool_call' ? (
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#8B5CF6' }}>LLM Output</h4>
              <pre
                style={{
                  margin: 0,
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  lineHeight: '1.4',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  overflow: 'auto',
                  maxHeight: '200px',
                  color: '#9CA3AF',
                }}
              >
                No LLM output available yet...
              </pre>
            </div>
          ) : null}

          {/* Show stdout/stderr for tool calls */}
          {task.type === 'tool_call' && (
            <>
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#10B981' }}>STDOUT</h4>
                <pre
                  style={{
                    margin: 0,
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    lineHeight: '1.4',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    overflow: 'auto',
                    maxHeight: '120px',
                    color: '#E5E7EB',
                  }}
                >
                  {task.stdout?.length
                    ? task.stdout.join('\n')
                    : 'No stdout output available'}
                </pre>
              </div>

              <div>
                <h4 style={{ margin: '0 0 8px 0', color: '#EF4444' }}>STDERR</h4>
                <pre
                  style={{
                    margin: 0,
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    lineHeight: '1.4',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    overflow: 'auto',
                    maxHeight: '120px',
                    color: '#FCA5A5',
                  }}
                >
                  {task.stderr?.length
                    ? task.stderr.join('\n')
                    : 'No stderr output available'}
                </pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}