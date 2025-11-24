export type Provider = 'AWS' | 'GCP' | 'Azure' | 'DigitalOcean';
export type ServiceType = 'Compute' | 'Storage' | 'Database' | 'Network' | 'Container';

export interface ServiceTemplate {
  id: string;
  name: string;
  description: string;
  provider: Provider;
  type: ServiceType;
  tags: string[];
  icon: string;
  guide: string;
}

export type DeploymentStatus = 'Provisioning' | 'Running' | 'Failed' | 'Stopped';

export interface Deployment {
  id: string;
  serviceId: string;
  name: string;
  provider: Provider;
  region: string;
  status: DeploymentStatus;
  createdAt: Date;
  configuration: Record<string, string>;
  costPerMonth?: number; // Estimated cost
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
  message: string;
}

export interface ActivityLog {
  id: string;
  user: string;
  avatar: string;
  action: string;
  target: string;
  timestamp: Date;
  type: 'deploy' | 'alert' | 'config' | 'security';
}

export interface CostMetric {
    month: string;
    amount: number;
    projected: boolean;
}

export interface Plugin {
  id: string;
  name: string;
  description: string;
  author: string;
  version: string;
  icon: string;
  status: 'Enabled' | 'Disabled';
  tags: string[];
  features: string[];
}

export interface Build {
    id: string;
    project: string;
    branch: string;
    commit: string;
    status: 'Running' | 'Success' | 'Failed' | 'Queued';
    startedAt: Date;
    duration: string;
    initiator: string;
}