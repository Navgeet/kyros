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
    // Handle both old format (direct array) and new format (object with tasks array)
    let planTasks: any[] = [];
    if (message.metadata?.plan) {
      if (Array.isArray(message.metadata.plan)) {
        // Old format: plan is directly an array
        planTasks = message.metadata.plan;
      } else if (typeof message.metadata.plan === 'object' && 
                 message.metadata.plan !== null && 
                 'tasks' in message.metadata.plan &&
                 Array.isArray(message.metadata.plan.tasks)) {
        // New format: plan is object with tasks array
        planTasks = message.metadata.plan.tasks;
      }
    }

    if (planTasks.length === 0) {
      return null;
    }

    return (
      <div className="plan-display">
        <strong>Execution Plan:</strong>
        {planTasks.map((task: any, index: number) => {
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