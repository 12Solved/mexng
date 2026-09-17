import { Route, Routes } from 'react-router-dom';
import { Toaster } from 'sonner';
import EmailsPage from './pages/EmailsPage.tsx';
import LogsPage from './pages/LogsPage.tsx';
import SingleEmailPage from './pages/SingleEmailPage.tsx';
import WorkflowEditor from './pages/Workflow.js';
import Navbar from './components/Navbar'
import WorkflowsPage from './pages/WorkflowsPage.tsx';
import CheckpointsPage from './pages/CheckpointsPage.tsx';
import DashboardPage from './pages/DashboardPage.tsx';
import { UserProvider } from './context/UserContext.tsx';

function App() {
  return (
    <UserProvider>
      <Toaster position="bottom-right" richColors />
      <div className="min-h-screen bg-background text-foreground">
        <Navbar />
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/emails" element={<EmailsPage />} />
          <Route path="/workflow" element={<WorkflowsPage />} />
          <Route path="/workflow/new" element={<WorkflowEditor />} />
          <Route path="/workflow/:id" element={<WorkflowEditor />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/email/:id" element={<SingleEmailPage />} />
          <Route path="/checkpoints" element={<CheckpointsPage />} />
        </Routes>
      </div>
    </UserProvider>
  )
}

export default App
