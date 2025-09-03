import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';
import { Message, StatusType, TaskNode } from '../types';

export const useSession = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'system',
      content: 'Hi, how can I assist you today?',
      timestamp: new Date().toISOString(),
    }
  ]);
  const [status, setStatus] = useState<StatusType>('ready');
  const [statusText, setStatusText] = useState('Ready');
  const [isTaskRunning, setIsTaskRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [taskNodes, setTaskNodes] = useState<TaskNode[]>([]);
  const processedAgentMessagesRef = useRef<Set<string>>(new Set());
  
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
    if (!sessionId || !isTaskRunning) {
      console.log('Polling stopped - sessionId:', sessionId, 'isTaskRunning:', isTaskRunning);
      return;
    }

    console.log('Polling task status for session:', sessionId);
    try {
      const result = await api.getMessages({
        session_id: sessionId,
        since_message_id: undefined,
      });

      console.log('Polling response:', result);

      if (result.messages && result.messages.length > 0) {
        const statusMessage = result.messages[0];
        const metadata = statusMessage.metadata;

        // Update task nodes for TaskViewer
        if (metadata?.task_nodes) {
          setTaskNodes(metadata.task_nodes);
        }
        
        // Process agent messages and add them as separate messages
        if (metadata?.agent_messages && metadata.agent_messages.length > 0) {
          metadata.agent_messages.forEach((agentMsg) => {
            // Create a unique key for this message based on content and timestamp
            const messageKey = `${agentMsg.message}_${agentMsg.timestamp}`;
            if (!processedAgentMessagesRef.current.has(messageKey)) {
              processedAgentMessagesRef.current.add(messageKey);
              addMessage('agent', agentMsg.message);
            }
          });
        }

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

  const startPolling = useCallback((currentSessionId: string) => {
    console.log('Starting polling for session:', currentSessionId);
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
    }
    setIsPolling(true);
    
    // Create a direct polling function that doesn't depend on state closure
    const poll = async () => {
      console.log('Direct polling for session:', currentSessionId);
      try {
        const result = await api.getMessages({
          session_id: currentSessionId,
          since_message_id: undefined,
        });

        console.log('Direct polling response:', result);

        if (result.messages && result.messages.length > 0) {
          const statusMessage = result.messages[0];
          const metadata = statusMessage.metadata;

          // Update task nodes for TaskViewer
          if (metadata?.task_nodes) {
            setTaskNodes(metadata.task_nodes);
          }
          
          // Process agent messages and add them as separate messages
          if (metadata?.agent_messages && metadata.agent_messages.length > 0) {
            metadata.agent_messages.forEach((agentMsg) => {
              // Create a unique key for this message based on content and timestamp
              const messageKey = `${agentMsg.message}_${agentMsg.timestamp}`;
              if (!processedAgentMessagesRef.current.has(messageKey)) {
                processedAgentMessagesRef.current.add(messageKey);
                addMessage('agent', agentMsg.message);
              }
            });
          }

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
                pollingRef.current = window.setTimeout(poll, 2000);
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
              default:
                pollingRef.current = window.setTimeout(poll, 2000);
                break;
            }
          } else {
            pollingRef.current = window.setTimeout(poll, 2000);
          }
        } else {
          pollingRef.current = window.setTimeout(poll, 2000);
        }
      } catch (error) {
        console.error('Direct polling error:', error);
        pollingRef.current = window.setTimeout(poll, 2000);
      }
    };
    
    poll();
  }, [updateStatus, addMessage]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const submitTask = useCallback(async (task: string) => {
    if (isTaskRunning) return;

    let currentSessionId = sessionId;
    
    // Initialize session if needed
    if (!currentSessionId) {
      try {
        const result = await api.createSession();
        currentSessionId = result.session_id;
        setSessionId(currentSessionId);
        console.log('Session initialized:', currentSessionId);
      } catch (error) {
        console.error('Failed to initialize session:', error);
        addMessage('error', 'Failed to initialize session');
        return;
      }
    }

    setIsTaskRunning(true);
    setIsLoading(true);
    updateStatus('working', 'Starting task...');
    
    // Clear processed agent messages for new task
    processedAgentMessagesRef.current.clear();

    try {
      const result = await api.executeTask({
        task,
        session_id: currentSessionId,
      });

      addMessage('user', task);

      if (result.status === 'started') {
        console.log('Task started:', result.task_id);
        updateStatus('working', 'Task in progress...');
        startPolling(currentSessionId);
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
  }, [sessionId, isTaskRunning, updateStatus, addMessage, startPolling]);

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
    taskNodes,
    submitTask,
  };
};