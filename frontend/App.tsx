import React, { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/Login';
import { DashboardPage } from './pages/Dashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { ServicesPage } from './pages/Services';
import { ServiceDetailPage } from './pages/ServiceDetail';
import { DeploymentStatusPage } from './pages/DeploymentStatus';
import { CatalogPage } from './pages/Catalog';
import { ProfilePage } from './pages/Profile';
import { UsersPage } from './pages/Users';
import { GroupsPage } from './pages/Groups';
import { RolesPage } from './pages/Roles';
import { CostAnalysisPage } from './pages/CostAnalysis';
import { SettingsPage } from './pages/Settings';
import { PluginDetailPage } from './pages/PluginDetail';
import PluginUpload from './pages/PluginUpload';
import Provision from './pages/Provision';
import { PluginRequestsPage } from './pages/PluginRequests';
import JobStatus from './pages/JobStatus';
import { AdminJobs } from './pages/AdminJobs';
import OIDCTestPage from './pages/OIDCTest';
import { NotFoundPage } from './pages/NotFound';
import { Plugin } from './types';

// Simple Context for Global State
interface AppContextType {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  plugins: Plugin[];
  togglePlugin: (id: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
};

const App: React.FC = () => {
  // Theme State
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('theme');
    return (saved as 'dark' | 'light') || 'dark';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const [plugins, setPlugins] = useState<Plugin[]>([]);

  const togglePlugin = (id: string) => {
    setPlugins(prev => prev.map(p => {
      if (p.id === id) {
        return { ...p, status: p.status === 'Enabled' ? 'Disabled' : 'Enabled' };
      }
      return p;
    }));
  };

  return (
    <AuthProvider>
      <NotificationProvider>
        <AppContext.Provider value={{ theme, toggleTheme, plugins, togglePlugin }}>
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<LoginPage />} />

              {/* Protected Routes */}
              <Route path="/" element={<ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>} />
              <Route path="/services" element={<ProtectedRoute><Layout><ServicesPage /></Layout></ProtectedRoute>} />
              <Route path="/service/:id" element={<ProtectedRoute><Layout><ServiceDetailPage /></Layout></ProtectedRoute>} />
              <Route path="/deployment/:id" element={<ProtectedRoute><Layout><DeploymentStatusPage /></Layout></ProtectedRoute>} />
              <Route path="/catalog" element={<ProtectedRoute><Layout><CatalogPage /></Layout></ProtectedRoute>} />
              <Route path="/costs" element={<ProtectedRoute><Layout><CostAnalysisPage /></Layout></ProtectedRoute>} />
              <Route path="/admin-dashboard" element={<ProtectedRoute adminOnly><Layout><AdminDashboard /></Layout></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute adminOnly><Layout><SettingsPage /></Layout></ProtectedRoute>} />
              <Route path="/users" element={<ProtectedRoute adminOnly><Layout><UsersPage /></Layout></ProtectedRoute>} />
              <Route path="/groups" element={<ProtectedRoute adminOnly><Layout><GroupsPage /></Layout></ProtectedRoute>} />
              <Route path="/roles" element={<ProtectedRoute adminOnly><Layout><RolesPage /></Layout></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><Layout><ProfilePage /></Layout></ProtectedRoute>} />
              <Route path="/plugin/:id" element={<ProtectedRoute><Layout><PluginDetailPage /></Layout></ProtectedRoute>} />

              {/* Plugin System Routes */}
              <Route path="/plugin-upload" element={<ProtectedRoute><Layout><PluginUpload /></Layout></ProtectedRoute>} />
              <Route path="/provision/:pluginId" element={<ProtectedRoute><Layout><Provision /></Layout></ProtectedRoute>} />
              <Route path="/jobs/:jobId" element={<ProtectedRoute><Layout><JobStatus /></Layout></ProtectedRoute>} />
              <Route path="/admin/jobs" element={<ProtectedRoute adminOnly><Layout><AdminJobs /></Layout></ProtectedRoute>} />
              <Route path="/admin/plugin-requests" element={<ProtectedRoute adminOnly><Layout><PluginRequestsPage /></Layout></ProtectedRoute>} />
              <Route path="/oidc-test" element={<ProtectedRoute><Layout><OIDCTestPage /></Layout></ProtectedRoute>} />

              {/* 404 Route */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </BrowserRouter>
        </AppContext.Provider>
      </NotificationProvider>
    </AuthProvider>
  );
};

export default App;