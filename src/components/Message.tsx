import React from 'react';
import { Message as MessageType } from '../types';

interface MessageProps {
  message: MessageType;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const getHeaderText = (type: string) => {
    switch (type) {
      case 'user': return 'You';
      case 'system': return 'Agent';
      case 'error': return 'Error';
      case 'status': return 'Status';
      case 'execution': return 'Execution';
      default: return 'System';
    }
  };

  const renderPlan = () => {
    if (!message.metadata?.plan || message.metadata.plan.length === 0) {
      return null;
    }

    return (
      <div className="plan-display">
        <strong>Execution Plan:</strong>
        {message.metadata.plan.map((task, index) => {
          const indent = '  '.repeat(task.level || 0);
          const deps = task.dependencies ? ` (depends on: ${task.dependencies.join(', ')})` : '';
          return (
            <div key={index} className="plan-task">
              {indent}{task.name}{deps}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className={`message ${message.type}`}>
      <div className="message-header">{getHeaderText(message.type)}</div>
      <div>{message.content}</div>
      {renderPlan()}
    </div>
  );
};

export default Message;