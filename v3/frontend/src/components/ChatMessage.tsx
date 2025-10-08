import React from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
  onApproval?: (approved: boolean) => void;
  onFeedback?: () => void;
  onReplan?: (planType: 'text' | 'code') => void;
  onExecuteCode?: () => void;
  onStartNewSession?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onApproval,
  onFeedback,
  onReplan,
  onExecuteCode,
  onStartNewSession
}) => {
  const getMessageClass = () => {
    switch (message.type) {
      case 'user_message':
        return 'message user-message';
      case 'agent_message':
        return 'message agent-message';
      case 'status':
        return 'message status-message';
      case 'error':
        return 'message error-message';
      case 'text_plan_review':
        return 'message plan-review';
      case 'code_review':
        return 'message code-review';
      case 'feedback_request':
        return 'message feedback-request';
      case 'completion':
        return 'message completion';
      case 'execution_result':
        return `message ${message.success ? 'completion' : 'error-message'}`;
      default:
        return 'message agent-message';
    }
  };

  const renderTextPlanReview = () => (
    <div>
      <strong>{message.message}</strong>
      <div className="plan-block">
        <pre>{message.plan}</pre>
      </div>
      <div className="action-buttons">
        <button
          className="approve-button"
          onClick={() => onApproval?.(true)}
        >
          ✅ Approve Plan
        </button>
        <button
          className="reject-button"
          onClick={onFeedback}
        >
          ❌ Request Changes
        </button>
        <button
          className="replan-button"
          onClick={() => onReplan?.('text')}
        >
          🔄 Generate New Plan
        </button>
      </div>
    </div>
  );

  const renderCodeReview = () => (
    <div>
      <strong>{message.message}</strong>
      <div className="code-block">
        <pre>{message.code}</pre>
      </div>
      <div className="action-buttons">
        <button
          className="approve-button"
          onClick={() => onApproval?.(true)}
        >
          ✅ Approve Code
        </button>
        <button
          className="reject-button"
          onClick={onFeedback}
        >
          ❌ Request Changes
        </button>
        <button
          className="replan-button"
          onClick={() => onReplan?.('code')}
        >
          🔄 Generate New Code
        </button>
      </div>
    </div>
  );

  const renderCompletion = () => (
    <div>
      <strong>🎉 {message.message}</strong>
      <details style={{ marginTop: '10px' }}>
        <summary><strong>Final Plan</strong></summary>
        <div className="plan-block">
          <pre>{message.final_plan}</pre>
        </div>
      </details>
      <details style={{ marginTop: '10px' }}>
        <summary><strong>Final Code</strong></summary>
        <div className="code-block">
          <pre>{message.final_code}</pre>
        </div>
      </details>
      <div className="action-buttons" style={{ marginTop: '15px' }}>
        <button className="approve-button" onClick={onExecuteCode}>
          🚀 Execute Code
        </button>
        <button className="feedback-button" onClick={onStartNewSession}>
          🆕 Start New Task
        </button>
      </div>
    </div>
  );

  const renderFeedbackRequest = () => (
    <div>
      <strong>{message.message}</strong>
      <p>Use the feedback form below to describe your changes.</p>
    </div>
  );

  const renderExecutionResult = () => {
    let resultContent = `<strong>${message.success ? '✅' : '❌'} ${message.message}</strong>`;

    if (message.execution_time !== undefined) {
      resultContent += `<p><strong>⏱️ Execution time:</strong> ${message.execution_time}s</p>`;
    }

    if (message.task_messages && message.task_messages.length > 0) {
      resultContent += `
        <details style="margin-top: 10px;" open>
          <summary><strong>📋 Task Messages</strong></summary>
          <div class="task-messages">
            ${message.task_messages.map(msg => `<div class="task-message">${JSON.stringify(msg)}</div>`).join('')}
          </div>
        </details>
      `;
    }

    return <div dangerouslySetInnerHTML={{ __html: resultContent }} />;
  };

  const renderContent = () => {
    switch (message.type) {
      case 'text_plan_review':
        return renderTextPlanReview();
      case 'code_review':
        return renderCodeReview();
      case 'completion':
        return renderCompletion();
      case 'feedback_request':
        return renderFeedbackRequest();
      case 'execution_result':
        return renderExecutionResult();
      default:
        return <>{message.message || message.content}</>;
    }
  };

  return (
    <div className={getMessageClass()}>
      {renderContent()}
    </div>
  );
};