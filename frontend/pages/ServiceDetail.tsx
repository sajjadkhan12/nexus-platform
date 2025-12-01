import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { SERVICES } from '../constants';
import { useApp } from '../App';
import { Rocket, BookOpen, CheckCircle, Info, ArrowLeft } from 'lucide-react';

export const ServiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addDeployment } = useApp();
  const service = SERVICES.find((s) => s.id === id);
  
  const [formData, setFormData] = useState({
    name: '',
    region: 'us-east-1',
    env: 'dev'
  });
  const [isDeploying, setIsDeploying] = useState(false);

  if (!service) {
    return <div className="text-center py-20 text-gray-900 dark:text-white">Service not found</div>;
  }

  const handleDeploy = (e: React.FormEvent) => {
    e.preventDefault();
    setIsDeploying(true);

    // Simulate API call delay
    setTimeout(() => {
        const newDeploymentId = Math.random().toString(36).substring(7);
        addDeployment({
            id: newDeploymentId,
            serviceId: service.id,
            name: formData.name,
            provider: service.provider,
            region: formData.region,
            status: 'Provisioning',
            createdAt: new Date(),
            configuration: { ...formData }
        });
        setIsDeploying(false);
        navigate(`/deployment/${newDeploymentId}`);
    }, 1500);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-500">
        
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Catalog
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Details & Guide */}
        <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden transition-colors">
                <div className="p-6 border-b border-gray-200 dark:border-gray-800 flex items-start gap-4 bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
                    <div className="p-3 bg-white rounded-xl shadow-lg border border-gray-100 dark:border-none">
                        <img src={service.icon} alt={service.provider} className="w-10 h-10 object-contain" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{service.name}</h1>
                        <p className="text-gray-500 dark:text-gray-400 mt-1">{service.description}</p>
                    </div>
                </div>
                
                <div className="p-6">
                    <div className="flex items-center gap-2 mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                        <BookOpen className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                        <h2>Deployment Guide</h2>
                    </div>
                    <div className="prose prose-sm max-w-none text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-950/50 p-6 rounded-xl border border-gray-200 dark:border-gray-800">
                        <div dangerouslySetInnerHTML={{ __html: service.guide.replace(/\n/g, '<br/>') }} />
                    </div>
                </div>
            </div>
        </div>

        {/* Right Column: Deploy Form */}
        <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 sticky top-24 shadow-xl transition-colors">
                <div className="flex items-center gap-2 mb-6">
                    <Rocket className="w-5 h-5 text-orange-600 dark:text-orange-500" />
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">Deploy Service</h3>
                </div>

                <form onSubmit={handleDeploy} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Resource Name</label>
                        <input
                            required
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                            placeholder="e.g., my-cluster-01"
                            className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-lg py-2 px-3 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-600"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Region</label>
                        <select
                            value={formData.region}
                            onChange={(e) => setFormData({...formData, region: e.target.value})}
                            className="w-full bg-gray-50 dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-lg py-2 px-3 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm"
                        >
                            <option value="us-east-1">US East (N. Virginia)</option>
                            <option value="us-west-1">US West (Oregon)</option>
                            <option value="eu-central-1">EU (Frankfurt)</option>
                            <option value="asia-east-1">Asia (Tokyo)</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Environment</label>
                         <div className="grid grid-cols-3 gap-2">
                            {['dev', 'staging', 'prod'].map((env) => (
                                <button
                                    key={env}
                                    type="button"
                                    onClick={() => setFormData({...formData, env})}
                                    className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                                        formData.env === env
                                            ? 'bg-orange-600 text-white border-orange-500 shadow-md shadow-orange-500/20'
                                            : 'bg-gray-50 dark:bg-gray-950 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                                    }`}
                                >
                                    {env.toUpperCase()}
                                </button>
                            ))}
                         </div>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 flex gap-3 items-start">
                        <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                            This will provision infrastructure in your {service.provider} account. Estimated time: 5-10 mins.
                        </p>
                    </div>

                    <button
                        type="submit"
                        disabled={isDeploying}
                        className={`w-full py-2.5 px-4 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all ${
                            isDeploying 
                                ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed' 
                                : 'bg-orange-600 hover:bg-orange-500 text-white shadow-lg shadow-orange-500/25'
                        }`}
                    >
                        {isDeploying ? (
                            <>Processing...</>
                        ) : (
                            <>
                                Initialize Deployment <CheckCircle className="w-4 h-4" />
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>

      </div>
    </div>
  );
};