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

export interface DeploymentTag {
  key: string;
  value: string;
}

export interface Deployment {
  id: string;
  name: string;
  plugin_id: string;
  version: string;
  status: string;
  deployment_type?: string; // 'infrastructure' or 'microservice'
  environment: string; // 'development' | 'staging' | 'production'
  tags: DeploymentTag[];
  cost_center?: string;
  project_code?: string;
  cloud_provider?: string;
  region?: string;
  stack_name?: string;
  created_at: string;
  updated_at?: string;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
  user_id?: string;
  job_id?: string;
  // Microservice fields
  github_repo_url?: string;
  github_repo_name?: string;
  ci_cd_status?: string; // 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  ci_cd_run_id?: number;
  ci_cd_run_url?: string;
  ci_cd_updated_at?: string;
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
  deployment_type?: string; // 'infrastructure' or 'microservice'
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