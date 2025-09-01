export interface Message {
  id: string;
  type: 'user' | 'system' | 'error' | 'status' | 'execution';
  content: string;
  timestamp: string;
  metadata?: {
    status?: string;
    current_task?: string;
    plan?: Array<{
      name: string;
      level?: number;
      dependencies?: string[];
    }>;
    result?: {
      error?: string;
    };
    task_nodes?: TaskNode[];
  };
}

export interface TaskRequest {
  task: string;
  max_retries?: number;
  session_id?: string;
}

export interface TaskResponse {
  task_id: string;
  session_id: string;
  status: string;
}

export interface MessagesRequest {
  session_id: string;
  since_message_id?: string;
}

export interface MessagesResponse {
  messages: Message[];
  session_id: string;
}

export type StatusType = 'ready' | 'working' | 'error';

export interface TaskNode {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];
  level?: number;
  position?: { x: number; y: number };
  stdout?: string[];
  stderr?: string[];
}