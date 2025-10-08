import { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketService } from '../services/WebSocketService';
import { Message, SessionState } from '../types';

export function useWebSocket() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionState, setSessionState] = useState<SessionState>({
    sessionId: null,
    phase: 'greeting',
    pendingApprovalType: null,
    connected: false
  });

  const wsService = useRef<WebSocketService | null>(null);

  const addMessage = useCallback((message: Message) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const handleMessage = useCallback((message: Message) => {
    console.log('📥 Received:', message.type, message);

    // Update session state based on message
    if (message.session_id) {
      setSessionState(prev => ({
        ...prev,
        sessionId: message.session_id!
      }));

      // Save to localStorage
      localStorage.setItem('agentSessionId', message.session_id);
    }

    if (message.phase) {
      setSessionState(prev => ({
        ...prev,
        phase: message.phase!
      }));

      localStorage.setItem('agentPhase', message.phase);
    }

    // Handle different message types
    switch (message.type) {
      case 'connection':
      case 'reconnection':
        addMessage({
          type: 'status',
          message: message.message
        });
        break;

      case 'text_plan_review':
        setSessionState(prev => ({
          ...prev,
          phase: 'text_plan_approval',
          pendingApprovalType: 'text'
        }));
        addMessage(message);
        break;

      case 'code_review':
        setSessionState(prev => ({
          ...prev,
          phase: 'code_approval',
          pendingApprovalType: 'code'
        }));
        addMessage(message);
        break;

      case 'feedback_request':
        const feedbackPhase = message.message?.includes('plan') ?
          'text_plan_feedback' : 'code_feedback';
        setSessionState(prev => ({
          ...prev,
          phase: feedbackPhase
        }));
        addMessage(message);
        break;

      case 'completion':
        setSessionState(prev => ({
          ...prev,
          phase: 'completed',
          pendingApprovalType: null
        }));
        addMessage(message);
        break;

      case 'session_state':
        // Silent state restoration - don't add message
        setSessionState(prev => ({
          ...prev,
          phase: message.phase || prev.phase,
          pendingApprovalType: message.phase === 'text_plan_approval' ? 'text' :
                              message.phase === 'code_approval' ? 'code' : null
        }));
        break;

      default:
        addMessage(message);
        break;
    }
  }, [addMessage]);

  const handleConnection = useCallback((connected: boolean) => {
    setSessionState(prev => ({
      ...prev,
      connected
    }));
  }, []);

  const connect = useCallback(async () => {
    if (wsService.current) return;

    const savedSessionId = localStorage.getItem('agentSessionId');
    const savedPhase = localStorage.getItem('agentPhase') || 'greeting';

    if (savedSessionId) {
      setSessionState(prev => ({
        ...prev,
        sessionId: savedSessionId,
        phase: savedPhase
      }));
    }

    wsService.current = new WebSocketService();
    wsService.current.onMessage(handleMessage);
    wsService.current.onConnection(handleConnection);

    try {
      await wsService.current.connect(savedSessionId || undefined);
    } catch (error) {
      console.error('❌ Connection failed:', error);
    }
  }, [handleMessage, handleConnection]);

  const disconnect = useCallback(() => {
    wsService.current?.disconnect();
    wsService.current = null;
  }, []);

  const sendMessage = useCallback((content: string) => {
    if (wsService.current?.isConnected) {
      wsService.current.sendUserMessage(content);
      addMessage({
        type: 'user_message',
        message: content
      });
    }
  }, [addMessage]);

  const sendApproval = useCallback((approved: boolean) => {
    wsService.current?.sendApproval(approved);
  }, []);

  const sendFeedback = useCallback((content: string) => {
    wsService.current?.sendFeedback(content);
  }, []);

  const sendReplan = useCallback((planType: 'text' | 'code') => {
    wsService.current?.sendReplan(planType);
  }, []);

  const startNewSession = useCallback(() => {
    // Clear session data
    localStorage.removeItem('agentSessionId');
    localStorage.removeItem('agentPhase');

    // Reset state
    setMessages([]);
    setSessionState({
      sessionId: null,
      phase: 'greeting',
      pendingApprovalType: null,
      connected: false
    });

    // Reconnect
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return {
    messages,
    sessionState,
    sendMessage,
    sendApproval,
    sendFeedback,
    sendReplan,
    startNewSession,
    connect,
    disconnect
  };
}