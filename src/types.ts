export interface Message {
  id: string;
  type: 'user' | 'system' | 'error' | 'status' | 'execution' | 'agent';
  content: string;
  timestamp: string;
  metadata?: {
    status?: string;
    current_task?: string;
    plan?: Array<{
      name: string;
      level?: number;
      dependencies?: string[];
    }> | {
      tasks: Array<{
        id?: string;
        name: string;
        type?: string;
        level?: number;
        dependencies?: string[];
        subtasks?: string[];
      }>;
    };
    result?: {
      error?: string;
    };
    agent_messages?: Array<{
      message: string;
      timestamp: number;
    }>;
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
  type?: 'task' | 'tool_call' | 'plan' | 'user_task';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'replan' | 'success' | 'error';
  dependencies: string[];
  subtasks?: string[];
  level?: number;
  position?: { x: number; y: number };
  stdout?: string[];
  stderr?: string[];
  thinking_content?: string;
  tool_name?: string;
  params?: any;
}