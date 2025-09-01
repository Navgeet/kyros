import { useCallback, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
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
    const newNodes: Node[] = tasks.map((task, index) => ({
      id: task.id,
      type: 'taskNode',
      position: task.position || { x: 100 + (index % 3) * 300, y: 100 + Math.floor(index / 3) * 150 },
      data: {
        task,
        isSelected: selectedTaskId === task.id,
        onSelect: () => onTaskSelect(task.id),
      },
    }));

    const newEdges: Edge[] = [];
    tasks.forEach((task) => {
      task.dependencies.forEach((depId) => {
        newEdges.push({
          id: `${depId}-${task.id}`,
          source: depId,
          target: task.id,
          type: 'smoothstep',
          animated: task.status === 'running',
        });
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [tasks, selectedTaskId, onTaskSelect, setNodes, setEdges]);

  return (
    <div style={{ width: '100%', height: '600px' }}>
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
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
      </ReactFlow>
    </div>
  );
}