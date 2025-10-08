import React, { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { ChatContainer } from './components/ChatContainer';
import { ChatInput } from './components/ChatInput';
import { FeedbackForm } from './components/FeedbackForm';
import { ConnectionStatus } from './components/ConnectionStatus';
import './App.css';

function App() {
  const {
    messages,
    sessionState,
    sendMessage,
    sendApproval,
    sendFeedback,
    sendReplan,
    startNewSession
  } = useWebSocket();

  const [showFeedbackForm, setShowFeedbackForm] = useState(false);

  const handleFeedback = () => {
    setShowFeedbackForm(true);
  };

  const handleSubmitFeedback = (feedback: string) => {
    sendFeedback(feedback);
    setShowFeedbackForm(false);
  };

  const handleCancelFeedback = () => {
    setShowFeedbackForm(false);
  };

  const handleExecuteCode = () => {
    // Placeholder for code execution - could integrate with backend execution service
    console.log('🚀 Code execution requested');
    // For now, just show a message
    alert('Code execution functionality would be implemented here');
  };

  const isInputDisabled = !sessionState.connected ||
    sessionState.phase === 'text_plan_approval' ||
    sessionState.phase === 'code_approval' ||
    sessionState.phase === 'text_plan_feedback' ||
    sessionState.phase === 'code_feedback';

  const shouldShowFeedbackForm = showFeedbackForm ||
    sessionState.phase === 'text_plan_feedback' ||
    sessionState.phase === 'code_feedback';

  return (
    <div className="app">
      <div className="container">


        <ConnectionStatus sessionState={sessionState} />

        <ChatContainer
          messages={messages}
          onApproval={sendApproval}
          onFeedback={handleFeedback}
          onReplan={sendReplan}
          onExecuteCode={handleExecuteCode}
          onStartNewSession={startNewSession}
        />

        <FeedbackForm
          visible={shouldShowFeedbackForm}
          onSubmitFeedback={handleSubmitFeedback}
          onCancel={handleCancelFeedback}
        />

        <ChatInput
          onSendMessage={sendMessage}
          disabled={isInputDisabled}
        />

        <div className="debug-actions">
          <button onClick={startNewSession} className="debug-button">
            🆕 Start New Session
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;