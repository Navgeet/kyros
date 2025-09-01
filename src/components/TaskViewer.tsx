import { useState } from 'react';
import TaskGraph from './TaskGraph';
import TaskOutputPanel from './TaskOutputPanel';
import { TaskNode } from '../types';

interface TaskViewerProps {
  onClose?: () => void;
  tasks?: TaskNode[];
}

export default function TaskViewer({ onClose, tasks = [] }: TaskViewerProps) {
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>();

  // Use tasks from props directly

  const handleTaskSelect = (taskId: string) => {
    setSelectedTaskId(taskId);
  };

  const handleCloseOutput = () => {
    setSelectedTaskId(undefined);
  };

  const selectedTask = tasks.find(task => task.id === selectedTaskId) || null;

  return (
    <div className="task-viewer" style={{ position: 'relative', backgroundColor: '#F9FAFB' }}>
      <div
        style={{
          padding: '16px',
          borderBottom: '1px solid #E5E7EB',
          backgroundColor: '#FFFFFF',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 'bold' }}>
          Task Execution
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6B7280',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        )}
      </div>

      <div style={{ flex: 1 }}>
        {tasks.length > 0 ? (
          <TaskGraph
            tasks={tasks}
            onTaskSelect={handleTaskSelect}
            selectedTaskId={selectedTaskId}
          />
        ) : (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%',
            color: '#666',
            fontSize: '1.2rem'
          }}>
            No active tasks. Submit a task to see the execution plan.
          </div>
        )}
      </div>

      <TaskOutputPanel
        task={selectedTask}
        onClose={handleCloseOutput}
      />
    </div>
  );
}