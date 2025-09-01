import { useState, useEffect } from 'react';
import TaskGraph from './TaskGraph';
import TaskOutputPanel from './TaskOutputPanel';
import { TaskNode } from '../types';

interface TaskViewerProps {
  onClose: () => void;
}

export default function TaskViewer({ onClose }: TaskViewerProps) {
  const [tasks, setTasks] = useState<TaskNode[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>();

  // Mock data for demonstration
  useEffect(() => {
    const mockTasks: TaskNode[] = [
      {
        id: '1',
        name: 'Initialize Project',
        status: 'completed',
        dependencies: [],
        stdout: ['Project initialized successfully', 'Dependencies installed'],
        stderr: [],
      },
      {
        id: '2',
        name: 'Parse Requirements',
        status: 'completed',
        dependencies: ['1'],
        stdout: ['Requirements parsed', 'Found 5 tasks to execute'],
        stderr: [],
      },
      {
        id: '3',
        name: 'Generate Code',
        status: 'running',
        dependencies: ['2'],
        stdout: ['Starting code generation...', 'Processing templates...'],
        stderr: ['Warning: Template not found, using default'],
      },
      {
        id: '4',
        name: 'Run Tests',
        status: 'pending',
        dependencies: ['3'],
        stdout: [],
        stderr: [],
      },
      {
        id: '5',
        name: 'Deploy',
        status: 'pending',
        dependencies: ['4'],
        stdout: [],
        stderr: [],
      },
    ];

    setTasks(mockTasks);
  }, []);

  const handleTaskSelect = (taskId: string) => {
    setSelectedTaskId(taskId);
  };

  const handleCloseOutput = () => {
    setSelectedTaskId(undefined);
  };

  const selectedTask = tasks.find(task => task.id === selectedTaskId) || null;

  return (
    <div style={{ position: 'relative', height: '100vh', backgroundColor: '#F9FAFB' }}>
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
          Task Execution Graph
        </h2>
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
      </div>

      <div style={{ height: 'calc(100vh - 80px)' }}>
        <TaskGraph
          tasks={tasks}
          onTaskSelect={handleTaskSelect}
          selectedTaskId={selectedTaskId}
        />
      </div>

      <TaskOutputPanel
        task={selectedTask}
        onClose={handleCloseOutput}
      />
    </div>
  );
}