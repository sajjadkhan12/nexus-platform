import React, { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, Download, Loader2 } from 'lucide-react';
import { costApi, CostTrendItem, CostByProviderItem } from '../services/api/cost';

export const CostAnalysisPage: React.FC = () => {
  const [costs, setCosts] = useState<CostTrendItem[]>([]);
  const [costsByProvider, setCostsByProvider] = useState<CostByProviderItem[]>([]);
  const [totalCost, setTotalCost] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCostData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch cost trend and costs by provider in parallel
        const [trendData, providerData] = await Promise.all([
          costApi.getCostTrend(6),
          costApi.getCostsByProvider(),
        ]);
        
        setCosts(trendData.trend);
        setCostsByProvider(providerData.costs);
        setTotalCost(trendData.total);
      } catch (err) {
        console.error('Failed to fetch cost data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load cost data');
      } finally {
        setLoading(false);
      }
    };

    fetchCostData();
  }, []);

  const maxAmount = costs.length > 0 ? Math.max(...costs.map(c => c.amount), 1) : 1000;

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
                    <span className="flex items-center gap-1.5"><div className="w-3 h-3 bg-orange-500 rounded-sm"></div> Actual</span>
                    <span className="flex items-center gap-1.5"><div className="w-3 h-3 bg-orange-200 dark:bg-orange-500/30 rounded-sm"></div> Projected</span>
                </div>
            </div>

            <div className="h-64 flex items-end justify-between gap-4">
                {loading ? (
                    <div className="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                        <Loader2 className="w-6 h-6 animate-spin" />
                    </div>
                ) : error ? (
                    <div className="w-full h-full flex items-center justify-center text-red-500 dark:text-red-400">
                        <p>{error}</p>
                    </div>
                ) : costs.length > 0 ? (
                    costs.map((metric) => (
                        <div key={metric.month} className="flex-1 flex flex-col items-center gap-2 group">
                            <div className="relative w-full flex items-end justify-center h-full">
                                <div 
                                    style={{ height: `${(metric.amount / maxAmount) * 100}%` }}
                                    className={`w-full max-w-[40px] rounded-t-lg transition-all duration-500 relative group-hover:opacity-90 ${
                                        metric.projected 
                                            ? 'bg-orange-200 dark:bg-orange-500/30 pattern-diagonal-lines' 
                                            : 'bg-orange-600 dark:bg-orange-500'
                                    }`}
                                >
                                    <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                                        ${metric.amount.toFixed(2)}
                                    </div>
                                </div>
                            </div>
                            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{metric.month}</span>
                        </div>
                    ))
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                        <p>No cost data available</p>
                    </div>
                )}
            </div>
         </div>

         {/* Summary Card */}
         <div className="md:col-span-1 space-y-6">
             <div className="bg-orange-600 rounded-2xl p-6 text-white shadow-lg shadow-orange-500/30">
                <div className="flex items-center gap-2 mb-2 opacity-90">
                    <DollarSign className="w-5 h-5" />
                    <span className="text-sm font-medium">Total Cost (6 months)</span>
                </div>
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin" />
                    </div>
                ) : (
                    <>
                        <h2 className="text-4xl font-bold mb-4">
                            ${totalCost.toFixed(2)}
                        </h2>
                        {costs.length > 1 && (
                            <div className="flex items-center gap-2 text-orange-100 text-sm bg-orange-500/30 px-3 py-1.5 rounded-lg w-fit">
                                <TrendingUp className="w-4 h-4" />
                                <span>
                                    {costs.length > 0 && costs[costs.length - 1].amount > costs[0].amount
                                        ? `+${(((costs[costs.length - 1].amount - costs[0].amount) / costs[0].amount) * 100).toFixed(1)}%`
                                        : costs[0].amount > 0
                                        ? `${(((costs[costs.length - 1].amount - costs[0].amount) / costs[0].amount) * 100).toFixed(1)}%`
                                        : '0%'} vs first month
                                </span>
                            </div>
                        )}
                    </>
                )}
             </div>

             <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Cost by Provider</h3>
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                ) : costsByProvider.length > 0 ? (
                    <div className="space-y-4">
                        {costsByProvider.map((provider) => {
                            const providerConfig: Record<string, { label: string; bgColor: string; textColor: string; shortName: string }> = {
                                'gcp': {
                                    label: 'Google Cloud',
                                    bgColor: 'bg-blue-100 dark:bg-blue-500/20',
                                    textColor: 'text-blue-600 dark:text-blue-400',
                                    shortName: 'GCP'
                                },
                                'aws': {
                                    label: 'Amazon Web Services',
                                    bgColor: 'bg-orange-100 dark:bg-orange-500/20',
                                    textColor: 'text-orange-600 dark:text-orange-400',
                                    shortName: 'AWS'
                                },
                                'azure': {
                                    label: 'Azure',
                                    bgColor: 'bg-sky-100 dark:bg-sky-500/20',
                                    textColor: 'text-sky-600 dark:text-sky-400',
                                    shortName: 'AZ'
                                }
                            };
                            
                            const config = providerConfig[provider.provider.toLowerCase()] || {
                                label: provider.provider,
                                bgColor: 'bg-gray-100 dark:bg-gray-500/20',
                                textColor: 'text-gray-600 dark:text-gray-400',
                                shortName: provider.provider.substring(0, 2).toUpperCase()
                            };
                            
                            return (
                                <div key={provider.provider} className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center`}>
                                            <span className={`${config.textColor} font-bold text-xs`}>{config.shortName}</span>
                                        </div>
                                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{config.label}</span>
                                    </div>
                                    <span className="text-sm font-bold text-gray-900 dark:text-white">
                                        ${provider.amount.toFixed(2)}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        <p>No provider cost data available</p>
                    </div>
                )}
             </div>
         </div>
      </div>
    </div>
  );
};