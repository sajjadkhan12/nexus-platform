import React, { useState } from 'react';
import { Save, Bell, Lock, Globe, Database } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [slackNotifs, setSlackNotifs] = useState(false);

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-500">
        <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your workspace configuration and preferences.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Sidebar Navigation for settings could go here in a larger app */}
            
            <div className="md:col-span-3 space-y-6">
                
                {/* General Section */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Globe className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white">General Configuration</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Organization Name</label>
                            <input type="text" defaultValue="Acme Corp Engineering" className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 text-sm" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Region</label>
                            <select className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 text-sm">
                                <option>us-east-1 (N. Virginia)</option>
                                <option>eu-central-1 (Frankfurt)</option>
                                <option>ap-northeast-1 (Tokyo)</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Notifications Section */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                     <div className="flex items-center gap-3 mb-6">
                        <Bell className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white">Notifications</h2>
                    </div>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
                            <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">Email Alerts</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">Receive summaries of deployment status changes.</p>
                            </div>
                            <button 
                                onClick={() => setEmailNotifs(!emailNotifs)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${emailNotifs ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${emailNotifs ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-800 last:border-0">
                            <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">Slack Webhook</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">Post incidents to #devops-alerts.</p>
                            </div>
                            <button 
                                onClick={() => setSlackNotifs(!slackNotifs)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${slackNotifs ? 'bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${slackNotifs ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* API Access */}
                <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                     <div className="flex items-center gap-3 mb-6">
                        <Lock className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white">API Access</h2>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-950 p-4 rounded-lg border border-gray-200 dark:border-gray-800 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Personal Access Token</p>
                            <code className="text-sm font-mono text-gray-800 dark:text-gray-300">sk_live_51M...92x</code>
                        </div>
                        <button className="text-sm text-indigo-600 dark:text-indigo-400 font-medium hover:underline">Revoke</button>
                    </div>
                </div>

                <div className="flex justify-end pt-4">
                    <button className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium shadow-lg shadow-indigo-500/25 hover:bg-indigo-500 transition-colors">
                        <Save className="w-4 h-4" /> Save Changes
                    </button>
                </div>
            </div>
        </div>
    </div>
  );
};