import { Handle, Position, NodeProps } from 'reactflow';
import { TaskNode } from '../types';

interface TaskNodeData {
  task: TaskNode;
  isSelected: boolean;
  onSelect: () => void;
}

export default function TaskNodeComponent({ data }: NodeProps<TaskNodeData>) {
  const { task, isSelected, onSelect } = data;

  const getStatusColor = (status: TaskNode['status']) => {
    switch (status) {
      case 'completed':
      case 'success':
        return '#10B981'; // green
      case 'running':
        return '#F59E0B'; // amber
      case 'failed':
      case 'error':
        return '#EF4444'; // red
      case 'replan':
        return '#8B5CF6'; // purple
      case 'pending':
      default:
        return '#6B7280'; // gray
    }
  };

  const getStatusDot = (status: TaskNode['status']) => {
    const color = getStatusColor(status);
    return (
      <div
        style={{
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: color,
          marginRight: '8px',
          animation: status === 'running' ? 'pulse 2s infinite' : 'none',
        }}
      />
    );
  };

  const getTitle = () => {
    // Check if this is a replan task (type: "plan" or status: "replan")
    if (task.type === 'plan' || task.status === 'replan') {
      return '🔄'; // Return just an icon for replan
    }
    // For tool_call type tasks, show the tool name
    if (task.type === 'tool_call' && task.tool_name) {
      return task.tool_name;
    }
    // Otherwise show the task name
    return task.name;
  };

  const getSubtitle = () => {
    // No subtitle for replan tasks
    if (task.type === 'plan' || task.status === 'replan') {
      return '';
    }
    // Only show params for tool_call type tasks
    if (task.type === 'tool_call' && task.params) {
      // Format params as a readable string
      const paramEntries = Object.entries(task.params);
      if (paramEntries.length === 0) return '';
      
      // Limit display to avoid overly long text
      const shortParams = paramEntries.slice(0, 2).map(([key, value]) => {
        const strValue = typeof value === 'string' ? value : JSON.stringify(value);
        const shortValue = strValue.length > 20 ? strValue.substring(0, 20) + '...' : strValue;
        return `${key}: ${shortValue}`;
      }).join(', ');
      
      return paramEntries.length > 2 ? `${shortParams}...` : shortParams;
    }
    return '';
  };

  return (
    <div
      onClick={onSelect}
      style={{
        padding: '12px',
        border: `2px solid ${isSelected ? '#3B82F6' : '#E5E7EB'}`,
        borderRadius: '8px',
        backgroundColor: '#FFFFFF',
        minWidth: '200px',
        cursor: 'pointer',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#555' }}
      />
      
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
        {!(task.type === 'plan' || task.status === 'replan') && getStatusDot(task.status)}
        <div style={{ 
          fontSize: (task.type === 'plan' || task.status === 'replan') ? '24px' : '14px', 
          fontWeight: 'bold',
          textAlign: (task.type === 'plan' || task.status === 'replan') ? 'center' : 'left',
          width: (task.type === 'plan' || task.status === 'replan') ? '100%' : 'auto'
        }}>
          {getTitle()}
        </div>
      </div>
      
      {getSubtitle() && (
        <div style={{ fontSize: '12px', color: '#6B7280' }}>
          {getSubtitle()}
        </div>
      )}
      
      {task.dependencies.length > 0 && (
        <div style={{ fontSize: '11px', color: '#9CA3AF', marginTop: '4px' }}>
          Dependencies: {task.dependencies.length}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#555' }}
      />

      <style>
        {`
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
          }
        `}
      </style>
    </div>
  );
}