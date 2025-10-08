import React, { useState } from 'react';

interface FeedbackFormProps {
  onSubmitFeedback: (feedback: string) => void;
  onCancel: () => void;
  visible: boolean;
}

export const FeedbackForm: React.FC<FeedbackFormProps> = ({
  onSubmitFeedback,
  onCancel,
  visible
}) => {
  const [feedback, setFeedback] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (feedback.trim()) {
      onSubmitFeedback(feedback.trim());
      setFeedback('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.shiftKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!visible) return null;

  return (
    <div className="feedback-container">
      <h3>Provide Feedback</h3>
      <form onSubmit={handleSubmit}>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Describe what changes you'd like to see..."
          rows={4}
          className="feedback-input"
          autoFocus
        />
        <div className="feedback-buttons">
          <button
            type="submit"
            disabled={!feedback.trim()}
            className="submit-feedback-button"
          >
            Submit Feedback
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="cancel-feedback-button"
          >
            Cancel
          </button>
        </div>
      </form>
      <p className="feedback-hint">
        💡 Tip: Use Ctrl+Enter or Shift+Enter to submit
      </p>
    </div>
  );
};