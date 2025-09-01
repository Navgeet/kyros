import { TaskRequest, TaskResponse, MessagesRequest, MessagesResponse } from './types';

const API_BASE = '/api';

export const api = {
  async createSession(): Promise<{ session_id: string }> {
    const response = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to create session');
    }
    
    return response.json();
  },

  async executeTask(request: TaskRequest): Promise<TaskResponse> {
    const response = await fetch(`${API_BASE}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      throw new Error('Failed to execute task');
    }
    
    return response.json();
  },

  async getMessages(request: MessagesRequest): Promise<MessagesResponse> {
    const response = await fetch(`${API_BASE}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      throw new Error('Failed to get messages');
    }
    
    return response.json();
  },

  async getStatus(): Promise<{ status: string; sessions?: any }> {
    const response = await fetch(`${API_BASE}/status`);
    
    if (!response.ok) {
      throw new Error('Failed to get status');
    }
    
    return response.json();
  },
};