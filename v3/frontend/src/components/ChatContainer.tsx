import React, { useEffect, useRef } from 'react';
import { Message } from '../types';
import { ChatMessage } from './ChatMessage';

interface ChatContainerProps {
  messages: Message[];
  onApproval: (approved: boolean) => void;
  onFeedback: () => void;
  onReplan: (planType: 'text' | 'code') => void;
  onExecuteCode: () => void;
  onStartNewSession: () => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  onApproval,
  onFeedback,
  onReplan,
  onExecuteCode,
  onStartNewSession
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="chat-container" ref={containerRef}>
      {messages.length === 0 && (
        <div className="message agent-message">
          What would you like me to help you with?
        </div>
      )}
      {messages.map((message, index) => (
        <ChatMessage
          key={index}
          message={message}
          onApproval={onApproval}
          onFeedback={onFeedback}
          onReplan={onReplan}
          onExecuteCode={onExecuteCode}
          onStartNewSession={onStartNewSession}
        />
      ))}
    </div>
  );
};