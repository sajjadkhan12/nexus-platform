import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApp } from '../App';
import { LogEntry, DeploymentStatus as StatusType } from '../types';
import { Terminal, CheckCircle2, Loader2, AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react';

export const DeploymentStatusPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { deployments, updateDeploymentStatus } = useApp();
  const deployment = deployments.find((d) => d.id === id);
  
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Status Badge Helper
  const StatusBadge = ({ status }: { status: StatusType }) => {
    const styles = {
        Provisioning: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20 animate-pulse",
        Running: "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20",
        Failed: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
        Stopped: "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20"
    };
    const icons = {
        Provisioning: <Loader2 className="w-4 h-4 animate-spin" />,
        Running: <CheckCircle2 className="w-4 h-4" />,
        Failed: <AlertCircle className="w-4 h-4" />,
        Stopped: <AlertCircle className="w-4 h-4" />
    };

    return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border ${styles[status]}`}>
            {icons[status]}
            {status}
        </span>
    );
  };

  // Simulate Logs and Status Change
  useEffect(() => {
    if (!deployment || deployment.status !== 'Provisioning') return;

    const mockLogs = [
        "Initializing request parameters...",
        "Validating credentials...",
        "Allocating resources in us-east-1...",
        "Network interface attached: vpc-12345xyz",
        "Security groups configured.",
        "Pulling base images...",
        "Configuring control plane...",
        "Waiting for health checks...",
        "Service reachable at 10.0.0.5",
        "Deployment completed successfully."
    ];

    let step = 0;
    const interval = setInterval(() => {
        if (step >= mockLogs.length) {
            clearInterval(interval);
            updateDeploymentStatus(deployment.id, 'Running');
            return;
        }

        const newLog: LogEntry = {
            id: Math.random().toString(),
            timestamp: new Date(),
            level: step === mockLogs.length - 1 ? 'SUCCESS' : 'INFO',
            message: mockLogs[step]
        };

        setLogs(prev => [...prev, newLog]);
        step++;
    }, 1000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deployment]);

  // Auto scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!deployment) return <div className="text-gray-900 dark:text-white text-center pt-20">Deployment not found</div>;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
       <Link to="/catalog" className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-4">
            <ArrowLeft className="w-4 h-4" /> Back to Deployments
       </Link>

       {/* Header Card */}
       <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 transition-colors">
            <div>
                <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{deployment.name}</h1>
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">ID: {deployment.id}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <span>{deployment.provider}</span>
                    <span>•</span>
                    <span>{deployment.region}</span>
                    <span>•</span>
                    <span>{new Date(deployment.createdAt).toLocaleDateString()}</span>
                </div>
            </div>
            <StatusBadge status={deployment.status} />
       </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Deployment Config */}
            <div className="lg:col-span-1 space-y-6">
                <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Configuration</h3>
                    <div className="space-y-3">
                        {Object.entries(deployment.configuration).map(([key, value]) => (
                            <div key={key} className="flex flex-col border-b border-gray-100 dark:border-gray-800 pb-2 last:border-0 last:pb-0">
                                <span className="text-xs text-gray-500 uppercase font-semibold">{key}</span>
                                <span className="text-gray-700 dark:text-gray-300">{value}</span>
                            </div>
                        ))}
                    </div>
                </div>
                
                {deployment.status === 'Running' && (
                     <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 transition-colors">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Actions</h3>
                        <button className="w-full py-2 bg-red-500/10 text-red-600 dark:text-red-500 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors text-sm font-medium">
                            Terminate Resources
                        </button>
                    </div>
                )}
            </div>

            {/* Live Logs Console */}
            <div className="lg:col-span-2">
                <div className="bg-gray-950 border border-gray-800 rounded-2xl overflow-hidden flex flex-col h-[500px] shadow-2xl">
                    <div className="bg-gray-900 px-4 py-2 border-b border-gray-800 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Terminal className="w-4 h-4 text-gray-400" />
                            <span className="text-sm font-mono text-gray-300">build_log.txt</span>
                        </div>
                        <div className="flex gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
                            <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                            <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
                        </div>
                    </div>
                    
                    <div className="flex-1 p-4 overflow-y-auto font-mono text-sm space-y-1.5 scrollbar-hide">
                        {logs.length === 0 && deployment.status === 'Provisioning' && (
                             <div className="flex items-center gap-2 text-gray-500 animate-pulse">
                                <RefreshCw className="w-3 h-3 animate-spin" /> Connecting to stream...
                             </div>
                        )}
                        {logs.length === 0 && deployment.status === 'Running' && (
                            <div className="text-gray-500">Log history archived.</div>
                        )}
                        {logs.map((log) => (
                            <div key={log.id} className="flex gap-3">
                                <span className="text-gray-600 select-none flex-shrink-0">
                                    {log.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                                <span className={`${
                                    log.level === 'ERROR' ? 'text-red-400' :
                                    log.level === 'WARN' ? 'text-yellow-400' :
                                    log.level === 'SUCCESS' ? 'text-green-400' :
                                    'text-gray-300'
                                }`}>
                                    {log.level === 'SUCCESS' ? 'Done: ' : '> '}{log.message}
                                </span>
                            </div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                </div>
            </div>
        </div>
    </div>
  );
};