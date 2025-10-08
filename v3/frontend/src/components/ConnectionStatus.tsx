import React from 'react';
import { SessionState } from '../types';

interface ConnectionStatusProps {
  sessionState: SessionState;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ sessionState }) => {
  const getStatusClass = () => {
    return sessionState.connected ? 'connected' : 'disconnected';
  };

  const getStatusText = () => {
    if (!sessionState.connected) {
      return 'Disconnected';
    }

    if (sessionState.sessionId) {
      return `Connected (Session: ${sessionState.sessionId})`;
    }

    return 'Connected';
  };

  const getPhaseText = () => {
    switch (sessionState.phase) {
      case 'greeting':
        return 'Ready';
      case 'text_plan_approval':
        return 'Awaiting Plan Approval';
      case 'code_approval':
        return 'Awaiting Code Approval';
      case 'text_plan_feedback':
        return 'Awaiting Plan Feedback';
      case 'code_feedback':
        return 'Awaiting Code Feedback';
      case 'completed':
        return 'Task Completed';
      default:
        return sessionState.phase;
    }
  };

  return (
    <div className="status-bar">
      <div className={`connection-status ${getStatusClass()}`}>
        <span className="status-indicator"></span>
        {getStatusText()}
      </div>
      <div className="phase-status">
        Phase: {getPhaseText()}
      </div>
    </div>
  );
};