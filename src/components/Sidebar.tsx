import React from 'react';
import { StatusType } from '../types';

interface SidebarProps {
  status: StatusType;
  statusText: string;
  isPolling: boolean;
  onExampleClick: (task: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  status,
  statusText,
  isPolling,
  onExampleClick
}) => {
  const examples = [
    'open a terminal',
    'take a screenshot',
    'launch firefox'
  ];

  return (
    <div className="sidebar">
      <h3>Status</h3>
      <div>
        <span className={`status-indicator ${status}`}></span>
        {statusText}
      </div>
      
      {isPolling && (
        <div className="polling-status visible">
          <span className="pulse-dot"></span>
          Checking status...
        </div>
      )}

      <h3 style={{ marginTop: '30px' }}>Features</h3>
      <ul className="features-list">
        <li>🧠 AI-powered planning</li>
        <li>⚙️ Desktop automation</li>
        <li>📋 Task dependencies</li>
        <li>🔄 Retry mechanism</li>
        <li>📸 Screen verification</li>
      </ul>
      
      <h3 style={{ marginTop: '30px' }}>Examples</h3>
      <div className="examples">
        {examples.map((example, index) => (
          <div
            key={index}
            className="example-task"
            onClick={() => onExampleClick(example)}
          >
            "{example}"
          </div>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;