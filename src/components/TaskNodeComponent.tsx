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
        return '#10B981'; // green
      case 'running':
        return '#F59E0B'; // amber
      case 'failed':
        return '#EF4444'; // red
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
        {getStatusDot(task.status)}
        <div style={{ fontSize: '14px', fontWeight: 'bold' }}>
          {task.name}
        </div>
      </div>
      
      <div style={{ fontSize: '12px', color: '#6B7280' }}>
        Status: {task.status}
      </div>
      
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