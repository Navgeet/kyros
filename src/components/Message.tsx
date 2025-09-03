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
      case 'agent': return 'Agent';
      case 'error': return 'Error';
      case 'status': return 'Status';
      case 'execution': return 'Execution';
      default: return 'System';
    }
  };

  return (
    <div className={`message ${message.type}`}>
      <div className="message-header">{getHeaderText(message.type)}</div>
      <div>{message.content}</div>
    </div>
  );
};

export default Message;