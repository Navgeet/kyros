export interface Message {
  type: 'user_message' | 'agent_message' | 'status' | 'error' | 'text_plan_review' |
        'code_review' | 'feedback_request' | 'completion' | 'connection' |
        'reconnection' | 'session_state' | 'execution_result';
  message?: string;
  content?: string;
  session_id?: string;
  plan?: string;
  code?: string;
  final_plan?: string;
  final_code?: string;
  phase?: string;
  text_plan?: string;
  python_code?: string;
  user_request?: string;
  success?: boolean;
  execution_time?: number;
  task_messages?: any[];
}

export interface SessionState {
  sessionId: string | null;
  phase: string;
  pendingApprovalType: 'text' | 'code' | null;
  connected: boolean;
}

export type Phase = 'greeting' | 'text_plan_approval' | 'code_approval' |
                    'text_plan_feedback' | 'code_feedback' | 'completed';

export interface ApprovalMessage {
  type: 'approval';
  approved: boolean;
}

export interface FeedbackMessage {
  type: 'feedback';
  content: string;
}

export interface ReplanMessage {
  type: 'replan';
  plan_type: 'text' | 'code';
}