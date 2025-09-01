import React, { useState } from 'react';
import Header from './components/Header';
import ChatContainer from './components/ChatContainer';
import Sidebar from './components/Sidebar';
import TaskViewer from './components/TaskViewer';
import { useSession } from './hooks/useSession';

const App: React.FC = () => {
  const [showTaskViewer, setShowTaskViewer] = useState(false);
  const {
    messages,
    status,
    statusText,
    isTaskRunning,
    isLoading,
    isPolling,
    submitTask,
  } = useSession();

  const handleExampleClick = (task: string) => {
    submitTask(task);
  };

  const handleShowTaskViewer = () => {
    setShowTaskViewer(true);
  };

  const handleCloseTaskViewer = () => {
    setShowTaskViewer(false);
  };

  if (showTaskViewer) {
    return <TaskViewer onClose={handleCloseTaskViewer} />;
  }

  return (
    <div className="container" onClick={handleShowTaskViewer}>
      <Header />
      <div className="main-content">
        <ChatContainer
          messages={messages}
          isLoading={isLoading}
          onSubmitTask={submitTask}
          isTaskRunning={isTaskRunning}
        />
        <Sidebar
          status={status}
          statusText={statusText}
          isPolling={isPolling}
          onExampleClick={handleExampleClick}
        />
      </div>
    </div>
  );
};

export default App;