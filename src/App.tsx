import React from 'react';
import Header from './components/Header';
import ChatContainer from './components/ChatContainer';
import Sidebar from './components/Sidebar';
import { useSession } from './hooks/useSession';

const App: React.FC = () => {
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

  return (
    <div className="container">
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