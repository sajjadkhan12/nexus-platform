import React, { createContext, useContext, useState, useEffect } from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { DashboardPage } from './pages/Dashboard';
import { ServicesPage } from './pages/Services';
import { ServiceDetailPage } from './pages/ServiceDetail';
import { DeploymentStatusPage } from './pages/DeploymentStatus';
import { CatalogPage } from './pages/Catalog';
import { ProfilePage } from './pages/Profile';
import { UsersPage } from './pages/Users';
import { CostAnalysisPage } from './pages/CostAnalysis';
import { SettingsPage } from './pages/Settings';
import { PluginsPage } from './pages/Plugins';
import { PluginDetailPage } from './pages/PluginDetail';
import { Plugin } from './types';
import { INITIAL_PLUGINS } from './constants';

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

  const [plugins, setPlugins] = useState<Plugin[]>(INITIAL_PLUGINS);

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
      <AppContext.Provider value={{ theme, toggleTheme, plugins, togglePlugin }}>
        <HashRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Routes */}
            <Route path="/" element={<ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>} />
            <Route path="/services" element={<ProtectedRoute><Layout><ServicesPage /></Layout></ProtectedRoute>} />
            <Route path="/service/:id" element={<ProtectedRoute><Layout><ServiceDetailPage /></Layout></ProtectedRoute>} />
            <Route path="/deployment/:id" element={<ProtectedRoute><Layout><DeploymentStatusPage /></Layout></ProtectedRoute>} />
            <Route path="/catalog" element={<ProtectedRoute><Layout><CatalogPage /></Layout></ProtectedRoute>} />
            <Route path="/costs" element={<ProtectedRoute><Layout><CostAnalysisPage /></Layout></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute adminOnly><Layout><SettingsPage /></Layout></ProtectedRoute>} />
            <Route path="/users" element={<ProtectedRoute adminOnly><Layout><UsersPage /></Layout></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute><Layout><ProfilePage /></Layout></ProtectedRoute>} />
            <Route path="/plugins" element={<ProtectedRoute><Layout><PluginsPage /></Layout></ProtectedRoute>} />
            <Route path="/plugin/:id" element={<ProtectedRoute><Layout><PluginDetailPage /></Layout></ProtectedRoute>} />
          </Routes>
        </HashRouter>
      </AppContext.Provider>
    </AuthProvider>
  );
};

export default App;