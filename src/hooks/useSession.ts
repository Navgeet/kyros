import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';
import { Message, StatusType } from '../types';

export const useSession = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'system',
      content: 'Welcome to Kyros AI Agent! Enter a task to get started.',
      timestamp: new Date().toISOString(),
    }
  ]);
  const [status, setStatus] = useState<StatusType>('ready');
  const [statusText, setStatusText] = useState('Ready');
  const [isTaskRunning, setIsTaskRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  
  const pollingRef = useRef<number | null>(null);

  const initializeSession = useCallback(async () => {
    try {
      const result = await api.createSession();
      setSessionId(result.session_id);
      console.log('Session initialized:', result.session_id);
    } catch (error) {
      console.error('Failed to initialize session:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'error',
        content: 'Failed to initialize session',
        timestamp: new Date().toISOString(),
      }]);
    }
  }, []);

  const updateStatus = useCallback((newStatus: StatusType, text: string) => {
    setStatus(newStatus);
    setStatusText(text);
  }, []);

  const addMessage = useCallback((type: Message['type'], content: string, metadata?: Message['metadata']) => {
    const message: Message = {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date().toISOString(),
      metadata,
    };
    
    setMessages(prev => [...prev, message]);
  }, []);

  const pollTaskStatus = useCallback(async () => {
    if (!sessionId || !isTaskRunning) return;

    try {
      const result = await api.getMessages({
        session_id: sessionId,
        since_message_id: undefined,
      });

      if (result.messages && result.messages.length > 0) {
        const statusMessage = result.messages[0];
        const metadata = statusMessage.metadata;

        if (metadata?.status) {
          switch (metadata.status) {
            case 'idle':
              updateStatus('ready', 'Ready');
              setIsTaskRunning(false);
              setIsLoading(false);
              setIsPolling(false);
              return;
            case 'running':
              updateStatus('working', `Processing: ${metadata.current_task || 'Task in progress'}`);
              break;
            case 'completed':
              updateStatus('ready', 'Task completed successfully!');
              addMessage('system', `Task completed: ${metadata.current_task}`, metadata);
              setIsTaskRunning(false);
              setIsLoading(false);
              setIsPolling(false);
              return;
            case 'failed':
              updateStatus('error', 'Task failed');
              addMessage('error', `Task failed: ${metadata.result?.error || 'Unknown error'}`);
              setIsTaskRunning(false);
              setIsLoading(false);
              setIsPolling(false);
              return;
          }
        }
      }
    } catch (error) {
      console.error('Polling error:', error);
    }

    if (isTaskRunning) {
      pollingRef.current = window.setTimeout(pollTaskStatus, 2000);
    }
  }, [sessionId, isTaskRunning, updateStatus, addMessage]);

  const startPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
    }
    setIsPolling(true);
    pollTaskStatus();
  }, [pollTaskStatus]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const submitTask = useCallback(async (task: string) => {
    if (isTaskRunning) return;

    if (!sessionId) {
      await initializeSession();
      return;
    }

    setIsTaskRunning(true);
    setIsLoading(true);
    updateStatus('working', 'Starting task...');

    try {
      const result = await api.executeTask({
        task,
        session_id: sessionId,
      });

      addMessage('user', task);

      if (result.status === 'started') {
        console.log('Task started:', result.task_id);
        updateStatus('working', 'Task in progress...');
        startPolling();
      } else {
        addMessage('error', `Unexpected task status: ${result.status}`);
        updateStatus('error', 'Error');
        setIsTaskRunning(false);
        setIsLoading(false);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addMessage('error', `Network error: ${errorMessage}`);
      updateStatus('error', 'Connection Error');
      setIsTaskRunning(false);
      setIsLoading(false);
    }
  }, [sessionId, isTaskRunning, initializeSession, updateStatus, addMessage, startPolling]);

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    messages,
    status,
    statusText,
    isTaskRunning,
    isLoading,
    isPolling,
    submitTask,
  };
};