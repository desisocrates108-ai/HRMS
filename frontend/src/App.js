import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { Toaster } from '@/components/ui/sonner';
import Layout from '@/components/Layout';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import BranchesPage from '@/pages/BranchesPage';
import BranchDetailPage from '@/pages/BranchDetailPage';
import JobsPage from '@/pages/JobsPage';
import LeadsPipelinePage from '@/pages/LeadsPipelinePage';
import LeadDetailPage from '@/pages/LeadDetailPage';
import TaskManagerPage from '@/pages/TaskManagerPage';
import PerformancePage from '@/pages/PerformancePage';
import UsersPage from '@/pages/UsersPage';
import EmployeesPage from '@/pages/EmployeesPage';
import AuditPage from '@/pages/AuditPage';
import ChatPage from '@/pages/ChatPage';
import PostPanelPage from '@/pages/PostPanelPage';
import CampaignsPage from '@/pages/CampaignsPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import FeedbackSubmissionsPage from '@/pages/FeedbackSubmissionsPage';
import FeedbackPage from '@/pages/FeedbackPage';
import '@/App.css';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-blue-700 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-500 mt-3">Loading...</p>
      </div>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AuthRoute() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/" replace />;
  return <LoginPage />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<AuthRoute />} />
          <Route path="/feedback/:token" element={<FeedbackPage />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/branches" element={<BranchesPage />} />
            <Route path="/branches/:id" element={<BranchDetailPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/leads" element={<LeadsPipelinePage />} />
            <Route path="/leads/:id" element={<LeadDetailPage />} />
            <Route path="/tasks" element={<TaskManagerPage />} />
            <Route path="/performance" element={<PerformancePage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/employees" element={<EmployeesPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/posts" element={<PostPanelPage />} />
            <Route path="/campaigns" element={<CampaignsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/feedback-submissions" element={<FeedbackSubmissionsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </AuthProvider>
  );
}

export default App;
