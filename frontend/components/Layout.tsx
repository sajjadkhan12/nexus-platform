import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutGrid, Server, User, Bell, Search, LogOut, Settings, Menu, X, Sun, Moon, ChevronRight, PieChart, Activity, Book, Users, Shield, Upload, Lock, ChevronDown, Package, List, FileText } from 'lucide-react';
import { useApp } from '../App';
import { useAuth } from '../contexts/AuthContext';
import { NotificationCenter } from './NotificationCenter';
import { API_URL } from '../constants/api';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useApp();
  const { user, logout, isAdmin } = useAuth();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside or when route changes
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null);
      }
      if (isProfileOpen && !(event.target as HTMLElement).closest('.profile-dropdown')) {
        setIsProfileOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isProfileOpen]);

  // Close dropdowns when route changes
  useEffect(() => {
    setOpenDropdown(null);
    setIsProfileOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Overview', path: '/', icon: Activity },
    ...(isAdmin ? [{ name: 'Admin Dashboard', path: '/admin-dashboard', icon: Shield }] : []),
    { name: 'Service Catalog', path: '/services', icon: LayoutGrid },
    { name: 'My Deployments', path: '/catalog', icon: Server },
    { name: 'Cost Analysis', path: '/costs', icon: PieChart },
  ];

  // Custom Logo Component for Foundry
  const FoundryLogo = () => (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-orange-600 dark:text-orange-500">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M10 9L15 12L10 15V9Z" fill="currentColor" stroke="none" />
    </svg>
  );

  const SidebarContent = () => (
    <>
      <div className="flex items-center gap-3 px-6 h-20 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
        <FoundryLogo />
        <span className="font-bold text-2xl tracking-tight text-gray-900 dark:text-white font-sans">FOUNDRY</span>
      </div>

      <div className="flex-1 overflow-y-auto py-6 px-3 scrollbar-hide">
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.name}
                to={item.path}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${isActive
                  ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
                  }`}
              >
                <item.icon className={`w-5 h-5 ${isActive ? 'text-orange-600 dark:text-orange-400' : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300'}`} />
                {item.name}
                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-orange-400" />}
              </Link>
            );
          })}
        </nav>

        <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-800 px-3">
          {isAdmin && (
            <>
              <Link to="/admin/jobs" className={`group flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                location.pathname === '/admin/jobs'
                  ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
              }`}>
                <Activity className="w-5 h-5 text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300" />
                All Jobs
              </Link>
              <Link to="/admin/audit-logs" className={`group flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                location.pathname === '/admin/audit-logs'
                  ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
              }`}>
                <FileText className="w-5 h-5 text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300" />
                Audit Logs
              </Link>
              <div className="my-2 border-t border-gray-200 dark:border-gray-700" />
              <Link to="/settings" className="group flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white transition-colors">
                <Settings className="w-5 h-5 text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300" />
                Settings
              </Link>
            </>
          )}
          <a href="#" className="group flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white transition-colors">
            <Book className="w-5 h-5 text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300" />
            Documentation
          </a>
          <Link to="/profile" className="group flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white transition-colors">
            <User className="w-5 h-5 text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300" />
            Profile
          </Link>
        </div>
      </div>

      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-200 dark:border-gray-700/50">
          <h4 className="text-xs font-semibold text-gray-900 dark:text-white mb-1">Status</h4>
          <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Systems Operational
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-300 overflow-hidden">

      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 flex-col fixed inset-y-0 z-30 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-colors duration-300">
        <SidebarContent />
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-64 transition-all duration-300 h-full">

        {/* Top Navigation Bar */}
        <header className="sticky top-0 z-20 h-16 bg-white/70 dark:bg-gray-900/50 backdrop-blur-xl border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4 sm:px-6 lg:px-8 transition-colors duration-300">

          <div className="flex items-center gap-4">
            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="md:hidden p-2 -ml-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Menu className="w-6 h-6" />
            </button>

            {/* Search */}
            <div className="relative hidden sm:block">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <input
                type="text"
                placeholder="Search resources..."
                className="bg-gray-100 dark:bg-gray-800 border-0 rounded-lg py-2 pl-9 pr-4 text-sm text-gray-900 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-orange-500 w-64 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-500"
              />
            </div>
          </div>

          {/* Admin Dropdown Menus */}
          {isAdmin && (
            <div ref={dropdownRef} className="hidden md:flex items-center gap-1">
              {/* Plugins Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setOpenDropdown(openDropdown === 'plugins' ? null : 'plugins')}
                  className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    openDropdown === 'plugins' || location.pathname.startsWith('/plugin') || location.pathname.startsWith('/admin/plugin')
                      ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  <Package className="w-4 h-4" />
                  <span>Plugins</span>
                  <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${openDropdown === 'plugins' ? 'rotate-180' : ''}`} />
                </button>

                {openDropdown === 'plugins' && (
                  <div className="absolute top-full left-0 mt-2 w-56 bg-white dark:bg-gray-900 rounded-xl shadow-lg py-2 border border-gray-200 dark:border-gray-800 ring-1 ring-black ring-opacity-5 z-50 animate-in fade-in zoom-in-95 duration-150 origin-top-left">
                    <Link
                      to="/admin/plugin-requests"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/admin/plugin-requests'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Lock className="w-4 h-4" />
                      <span>Plugin Requests</span>
                    </Link>
                    <Link
                      to="/plugin-upload"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/plugin-upload'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Upload className="w-4 h-4" />
                      <span>Upload Plugin</span>
                    </Link>
                    <Link
                      to="/services"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/services'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <List className="w-4 h-4" />
                      <span>See All Plugins</span>
                    </Link>
                  </div>
                )}
              </div>

              {/* Access Management Dropdown */}
              <div className="relative">
                  <button
                  onClick={() => setOpenDropdown(openDropdown === 'users' ? null : 'users')}
                  className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                    openDropdown === 'users' || location.pathname === '/users' || location.pathname === '/groups' || location.pathname === '/roles' || location.pathname === '/admin/audit-logs'
                      ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  <Users className="w-4 h-4" />
                  <span>Access Management</span>
                  <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${openDropdown === 'users' ? 'rotate-180' : ''}`} />
                </button>

                {openDropdown === 'users' && (
                  <div className="absolute top-full left-0 mt-2 w-56 bg-white dark:bg-gray-900 rounded-xl shadow-lg py-2 border border-gray-200 dark:border-gray-800 ring-1 ring-black ring-opacity-5 z-50 animate-in fade-in zoom-in-95 duration-150 origin-top-left">
                    <Link
                      to="/users"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/users'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Users className="w-4 h-4" />
                      <span>Users</span>
                    </Link>
                    <Link
                      to="/groups"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/groups'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Users className="w-4 h-4" />
                      <span>Groups</span>
                    </Link>
                    <Link
                      to="/roles"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/roles'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Shield className="w-4 h-4" />
                      <span>Roles</span>
                    </Link>
                    <Link
                      to="/admin/audit-logs"
                      onClick={() => setOpenDropdown(null)}
                      className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                        location.pathname === '/admin/audit-logs'
                          ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                      <span>Audit Logs</span>
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Right Actions */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            <NotificationCenter />

            <div className="h-6 w-px bg-gray-200 dark:bg-gray-700 mx-2"></div>

            <div className="relative profile-dropdown">
              <button
                onClick={() => setIsProfileOpen(!isProfileOpen)}
                className="flex items-center gap-3 pl-2 pr-1 py-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="text-right hidden lg:block">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.full_name || user?.username}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">@{user?.username || 'user'}</p>
                </div>
                {user?.avatar_url ? (
                  <img
                    src={user.avatar_url.startsWith('http') ? user.avatar_url : `${API_URL}${user.avatar_url}`}
                    alt="Profile"
                    className="h-8 w-8 rounded-full ring-2 ring-gray-200 dark:ring-gray-800 object-cover"
                  />
                ) : (
                  <div className="h-8 w-8 rounded-full ring-2 ring-gray-200 dark:ring-gray-800 bg-orange-600 dark:bg-orange-500 flex items-center justify-center text-white font-semibold text-sm">
                    {user?.full_name?.charAt(0) || user?.username?.charAt(0) || 'U'}
                  </div>
                )}
              </button>

              {isProfileOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-900 rounded-xl shadow-lg py-1 border border-gray-200 dark:border-gray-800 ring-1 ring-black ring-opacity-5 focus:outline-none animate-in fade-in zoom-in-95 duration-100 origin-top-right z-50">
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800 lg:hidden">
                    <p className="text-sm text-gray-900 dark:text-white">{user?.full_name || user?.username}</p>
                    <p className="text-xs text-gray-500">{user?.email}</p>
                  </div>
                  <Link
                    to="/profile"
                    onClick={() => setIsProfileOpen(false)}
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white flex items-center gap-2"
                  >
                    <User className="w-4 h-4" /> Your Profile
                  </Link>
                  <Link
                    to="/settings"
                    onClick={() => setIsProfileOpen(false)}
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white flex items-center gap-2"
                  >
                    <Settings className="w-4 h-4" /> Settings
                  </Link>
                  <div className="border-t border-gray-200 dark:border-gray-800 my-1"></div>
                  <button onClick={handleLogout} className="w-full text-left block px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-gray-800 hover:text-red-700 dark:hover:text-red-300 flex items-center gap-2">
                    <LogOut className="w-4 h-4" /> Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 scroll-smooth">
          {children}
        </main>
      </div>

      {/* Mobile Menu Backdrop & Drawer */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" onClick={() => setIsMobileMenuOpen(false)}></div>
          <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white dark:bg-gray-900 transition-transform duration-300 transform translate-x-0 border-r border-gray-200 dark:border-gray-800">
            <div className="absolute top-0 right-0 -mr-12 pt-2">
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white text-white"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <SidebarContent />
          </div>
        </div>
      )}

    </div>
  );
};