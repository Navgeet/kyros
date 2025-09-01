import { useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { TaskNode } from '../types';
import TaskNodeComponent from './TaskNodeComponent';

const nodeTypes = {
  taskNode: TaskNodeComponent,
};

interface TaskGraphProps {
  tasks: TaskNode[];
  onTaskSelect: (taskId: string) => void;
  selectedTaskId?: string;
}

export default function TaskGraph({ tasks, onTaskSelect, selectedTaskId }: TaskGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Convert tasks to nodes and edges
  useEffect(() => {
    // Create a map for better positioning based on hierarchy
    const taskMap = new Map(tasks.map(task => [task.id, task]));
    const positioned = new Set<string>();
    
    // Find root tasks (tasks with no parent, i.e., not in any subtasks array)
    const parentTasks = new Set<string>();
    tasks.forEach(task => {
      if (task.subtasks) {
        task.subtasks.forEach(subtaskId => parentTasks.add(subtaskId));
      }
    });
    const rootTasks = tasks.filter(task => !parentTasks.has(task.id));
    
    const newNodes: Node[] = [];
    let rootX = 100;
    const rootY = 100;
    
    // Position root tasks first
    rootTasks.forEach((task, rootIndex) => {
      const position = task.position || { x: rootX + rootIndex * 400, y: rootY };
      newNodes.push({
        id: task.id,
        type: 'taskNode',
        position,
        data: {
          task,
          isSelected: selectedTaskId === task.id,
          onSelect: () => onTaskSelect(task.id),
        },
      });
      positioned.add(task.id);
      
      // Position subtasks in a hierarchical layout
      if (task.subtasks) {
        const subtaskStartX = position.x - ((task.subtasks.length - 1) * 150) / 2;
        task.subtasks.forEach((subtaskId, subtaskIndex) => {
          const subtask = taskMap.get(subtaskId);
          if (subtask && !positioned.has(subtaskId)) {
            newNodes.push({
              id: subtask.id,
              type: 'taskNode',
              position: subtask.position || {
                x: subtaskStartX + subtaskIndex * 300,
                y: position.y + 200
              },
              data: {
                task: subtask,
                isSelected: selectedTaskId === subtask.id,
                onSelect: () => onTaskSelect(subtask.id),
              },
            });
            positioned.add(subtaskId);
          }
        });
      }
    });
    
    // Position any remaining tasks that weren't positioned yet
    tasks.forEach((task, index) => {
      if (!positioned.has(task.id)) {
        newNodes.push({
          id: task.id,
          type: 'taskNode',
          position: task.position || { x: 100 + (index % 3) * 300, y: 400 + Math.floor(index / 3) * 150 },
          data: {
            task,
            isSelected: selectedTaskId === task.id,
            onSelect: () => onTaskSelect(task.id),
          },
        });
      }
    });

    const newEdges: Edge[] = [];
    tasks.forEach((task) => {
      // Add dependency edges (execution order)
      task.dependencies.forEach((depId) => {
        newEdges.push({
          id: `dep-${depId}-${task.id}`,
          source: depId,
          target: task.id,
          type: 'smoothstep',
          animated: task.status === 'running',
          style: { stroke: '#6366f1', strokeWidth: 2 },
          label: 'depends on',
        });
      });
      
      // Add subtask edges (parent-child hierarchy)
      if (task.subtasks) {
        task.subtasks.forEach((subtaskId) => {
          newEdges.push({
            id: `sub-${task.id}-${subtaskId}`,
            source: task.id,
            target: subtaskId,
            type: 'straight',
            style: { 
              stroke: '#10b981', 
              strokeWidth: 2,
              strokeDasharray: '5,5'
            },
            label: 'contains',
          });
        });
      }
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [tasks, selectedTaskId, onTaskSelect, setNodes, setEdges]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>
      
      {/* Legend */}
      <div style={{
        position: 'absolute',
        top: 10,
        right: 10,
        background: 'white',
        padding: '12px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        fontSize: '12px',
        zIndex: 1000
      }}>
        <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>Relationships</div>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
          <div style={{
            width: '20px',
            height: '2px',
            backgroundColor: '#6366f1',
            marginRight: '8px'
          }}></div>
          <span>Dependencies</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{
            width: '20px',
            height: '2px',
            backgroundColor: '#10b981',
            backgroundImage: 'linear-gradient(90deg, #10b981 50%, transparent 50%)',
            backgroundSize: '10px 2px',
            marginRight: '8px'
          }}></div>
          <span>Subtasks</span>
        </div>
      </div>
    </div>
  );
}