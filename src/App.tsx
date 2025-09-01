import React from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import TaskViewer from './components/TaskViewer';
import { useSession } from './hooks/useSession';

const App: React.FC = () => {
  const {
    messages,
    isTaskRunning,
    isLoading,
    taskNodes,
    submitTask,
  } = useSession();

  return (
    <div className="container">
      <Header />
      <div className="main-content">
        <TaskViewer tasks={taskNodes} />
        <Sidebar
          messages={messages}
          onSubmitTask={submitTask}
          isTaskRunning={isTaskRunning}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};

export default App;