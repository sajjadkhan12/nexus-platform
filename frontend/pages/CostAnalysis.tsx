import React from 'react';
import { MOCK_COSTS } from '../constants';
import { DollarSign, TrendingUp, Download, PieChart } from 'lucide-react';

export const CostAnalysisPage: React.FC = () => {
  const maxAmount = Math.max(...MOCK_COSTS.map(c => c.amount));

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Cost Analysis</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Track infrastructure spending and forecast.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <Download className="w-4 h-4" /> Export Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         {/* Main Chart Card */}
         <div className="md:col-span-2 bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">Monthly Spend Trend</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Last 6 months breakdown</p>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                    <span className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-500 rounded-sm"></div> Actual</span>
                    <span className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-200 dark:bg-indigo-500/30 rounded-sm"></div> Projected</span>
                </div>
            </div>

            <div className="h-64 flex items-end justify-between gap-4">
                {MOCK_COSTS.map((metric) => (
                    <div key={metric.month} className="flex-1 flex flex-col items-center gap-2 group">
                        <div className="relative w-full flex items-end justify-center h-full">
                            <div 
                                style={{ height: `${(metric.amount / maxAmount) * 100}%` }}
                                className={`w-full max-w-[40px] rounded-t-lg transition-all duration-500 relative group-hover:opacity-90 ${
                                    metric.projected 
                                        ? 'bg-indigo-200 dark:bg-indigo-500/30 pattern-diagonal-lines' 
                                        : 'bg-indigo-600 dark:bg-indigo-500'
                                }`}
                            >
                                <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                                    ${metric.amount}
                                </div>
                            </div>
                        </div>
                        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{metric.month}</span>
                    </div>
                ))}
            </div>
         </div>

         {/* Summary Card */}
         <div className="md:col-span-1 space-y-6">
             <div className="bg-indigo-600 rounded-2xl p-6 text-white shadow-lg shadow-indigo-500/30">
                <div className="flex items-center gap-2 mb-2 opacity-90">
                    <DollarSign className="w-5 h-5" />
                    <span className="text-sm font-medium">Total Cost (YTD)</span>
                </div>
                <h2 className="text-4xl font-bold mb-4">$14,240.50</h2>
                <div className="flex items-center gap-2 text-indigo-100 text-sm bg-indigo-500/30 px-3 py-1.5 rounded-lg w-fit">
                    <TrendingUp className="w-4 h-4" />
                    <span>+8.4% vs last year</span>
                </div>
             </div>

             <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Cost by Provider</h3>
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-500/20 flex items-center justify-center">
                                <span className="text-orange-600 dark:text-orange-400 font-bold text-xs">AWS</span>
                            </div>
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Amazon Web Services</span>
                        </div>
                        <span className="text-sm font-bold text-gray-900 dark:text-white">$8,450</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center">
                                <span className="text-blue-600 dark:text-blue-400 font-bold text-xs">GCP</span>
                            </div>
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Google Cloud</span>
                        </div>
                        <span className="text-sm font-bold text-gray-900 dark:text-white">$3,240</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-sky-100 dark:bg-sky-500/20 flex items-center justify-center">
                                <span className="text-sky-600 dark:text-sky-400 font-bold text-xs">AZ</span>
                            </div>
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Azure</span>
                        </div>
                        <span className="text-sm font-bold text-gray-900 dark:text-white">$2,550</span>
                    </div>
                </div>
             </div>
         </div>
      </div>
    </div>
  );
};