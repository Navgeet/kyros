import React, { useState, useRef, useEffect } from 'react';
import Message from './Message';
import { Message as MessageType } from '../types';

interface ChatContainerProps {
  messages: MessageType[];
  isLoading: boolean;
  onSubmitTask: (task: string) => void;
  isTaskRunning: boolean;
}

const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  isLoading,
  onSubmitTask,
  isTaskRunning
}) => {
  const [task, setTask] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const taskInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!isTaskRunning && taskInputRef.current) {
      taskInputRef.current.focus();
    }
  }, [isTaskRunning]);

  const handleSubmit = () => {
    if (!task.trim() || isTaskRunning) return;
    
    onSubmitTask(task.trim());
    setTask('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };


  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {isLoading && (
        <div className="loading visible">
          <div className="spinner"></div>
          <div>Processing your request...</div>
        </div>
      )}
      
      <div className="input-container">
        <input
          ref={taskInputRef}
          type="text"
          className="task-input"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Enter your task (e.g., 'open a terminal', 'take a screenshot')"
          disabled={isTaskRunning}
        />
        <button
          className="submit-btn"
          onClick={handleSubmit}
          disabled={isTaskRunning || !task.trim()}
        >
          Execute
        </button>
      </div>
    </div>
  );
};

export default ChatContainer;