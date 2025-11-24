import { ServiceTemplate, ActivityLog, CostMetric, Plugin, Build } from './types';

export const SERVICES: ServiceTemplate[] = [
  {
    id: 'gke-standard',
    name: 'Google Kubernetes Engine',
    description: 'Managed Kubernetes service for running containerized applications on Google Cloud infrastructure.',
    provider: 'GCP',
    type: 'Container',
    tags: ['gcp', 'kubernetes', 'cluster', 'managed'],
    icon: 'https://www.vectorlogo.zone/logos/google_cloud/google_cloud-icon.svg',
    guide: `
### GKE Standard Cluster
Deploy a production-ready Kubernetes cluster on GCP.

**Features:**
- Autopilot or Standard modes
- Regional or Zonal availability
- Integrated logging and monitoring with Cloud Operations

**Prerequisites:**
- GCP Service Account with Kubernetes Admin role
- Enabled Container API
    `
  },
  {
    id: 'aks-managed',
    name: 'Azure Kubernetes Service',
    description: 'Simplify deploying a managed Kubernetes cluster in Azure by offloading the operational overhead to Azure.',
    provider: 'Azure',
    type: 'Container',
    tags: ['azure', 'kubernetes', 'k8s', 'microsoft'],
    icon: 'https://www.vectorlogo.zone/logos/microsoft_azure/microsoft_azure-icon.svg',
    guide: `
### Azure Kubernetes Service
Deploy enterprise-grade Kubernetes on Azure.

**Key Configs:**
- Node Pool Sizing
- Network Policy (Calico/Azure)
- RBAC Integration
    `
  },
  {
    id: 'eks-cluster',
    name: 'Amazon EKS',
    description: 'Managed Kubernetes service to run Kubernetes on AWS and on-premises.',
    provider: 'AWS',
    type: 'Container',
    tags: ['aws', 'kubernetes', 'elastic', 'amazon'],
    icon: 'https://www.vectorlogo.zone/logos/amazon_aws/amazon_aws-icon.svg',
    guide: `
### Amazon EKS
Scalable and secure Kubernetes on AWS.

**Setup Steps:**
1. Define VPC configuration
2. Select IAM Roles
3. Choose Node Group types (Fargate or EC2)
    `
  },
  {
    id: 's3-bucket',
    name: 'Amazon S3 Bucket',
    description: 'Object storage built to retrieve any amount of data from anywhere.',
    provider: 'AWS',
    type: 'Storage',
    tags: ['aws', 'storage', 'object', 'blob'],
    icon: 'https://www.vectorlogo.zone/logos/amazon_aws/amazon_aws-icon.svg',
    guide: `
### S3 Bucket Provisioning
Create a secure, highly available object storage bucket.

**Options:**
- Versioning enabled/disabled
- Encryption (SSE-S3, SSE-KMS)
- Public access blocking
    `
  },
  {
    id: 'gcs-bucket',
    name: 'Google Cloud Storage',
    description: 'Unified object storage for developers and enterprises.',
    provider: 'GCP',
    type: 'Storage',
    tags: ['gcp', 'storage', 'bucket'],
    icon: 'https://www.vectorlogo.zone/logos/google_cloud/google_cloud-icon.svg',
    guide: `
### Cloud Storage Bucket
Scalable object storage on Google Cloud.

**Classes:**
- Standard
- Nearline
- Coldline
- Archive
    `
  },
  {
    id: 'rds-postgres',
    name: 'Amazon RDS for PostgreSQL',
    description: 'Managed PostgreSQL database service with high availability.',
    provider: 'AWS',
    type: 'Database',
    tags: ['aws', 'database', 'sql', 'postgres'],
    icon: 'https://www.vectorlogo.zone/logos/postgresql/postgresql-icon.svg',
    guide: `
### RDS PostgreSQL
Deploy a managed relational database.

**Features:**
- Multi-AZ Deployment
- Automated Backups
- Read Replicas
    `
  },
  {
    id: 'azure-blob',
    name: 'Azure Blob Storage',
    description: 'Massively scalable and secure object storage for cloud-native workloads.',
    provider: 'Azure',
    type: 'Storage',
    tags: ['azure', 'storage', 'blob'],
    icon: 'https://www.vectorlogo.zone/logos/microsoft_azure/microsoft_azure-icon.svg',
    guide: `
### Azure Blob Storage
Cloud object storage.

**Tiers:**
- Hot
- Cool
- Archive
    `
  },
  {
    id: 'do-droplet',
    name: 'DigitalOcean Droplet',
    description: 'Scalable virtual machines for your application needs.',
    provider: 'DigitalOcean',
    type: 'Compute',
    tags: ['do', 'vm', 'compute', 'linux'],
    icon: 'https://www.vectorlogo.zone/logos/digitalocean/digitalocean-icon.svg',
    guide: `
### Droplet Creation
Launch a virtual machine in seconds.

**Images:**
- Ubuntu, Fedora, Debian, CentOS
- Marketplace Apps (Docker, NodeJS)
    `
  }
];

export const MOCK_ACTIVITIES: ActivityLog[] = [
    {
        id: '1',
        user: 'Sarah Chen',
        avatar: 'https://i.pravatar.cc/150?u=1',
        action: 'deployed',
        target: 'production-api-cluster',
        timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30 mins ago
        type: 'deploy'
    },
    {
        id: '2',
        user: 'System Bot',
        avatar: '',
        action: 'detected high usage',
        target: 'redis-cache-primary',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
        type: 'alert'
    },
    {
        id: '3',
        user: 'Alex Engineer',
        avatar: 'https://picsum.photos/100/100',
        action: 'updated configuration',
        target: 'load-balancer-external',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5), // 5 hours ago
        type: 'config'
    },
    {
        id: '4',
        user: 'Mike Ross',
        avatar: 'https://i.pravatar.cc/150?u=4',
        action: 'rotated secrets',
        target: 'vault-key-store',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
        type: 'security'
    }
];

export const MOCK_COSTS: CostMetric[] = [
    { month: 'Jun', amount: 850, projected: false },
    { month: 'Jul', amount: 920, projected: false },
    { month: 'Aug', amount: 890, projected: false },
    { month: 'Sep', amount: 1050, projected: false },
    { month: 'Oct', amount: 1150, projected: false },
    { month: 'Nov', amount: 1320, projected: true },
];

export const INITIAL_PLUGINS: Plugin[] = [
  {
    id: 'gcp-provider',
    name: 'Google Cloud Platform',
    description: 'Enables provisioning of GKE, Cloud Storage, and other GCP services.',
    author: 'Google',
    version: '4.2.0',
    icon: 'https://www.vectorlogo.zone/logos/google_cloud/google_cloud-icon.svg',
    status: 'Enabled',
    tags: ['provider', 'cloud', 'gcp'],
    features: ['GKE Autopilot Integration', 'Cloud Run Support', 'IAM Policy Management']
  },
  {
    id: 'aws-provider',
    name: 'AWS Provider',
    description: 'Integrates Amazon Web Services resources including EKS, S3, and RDS.',
    author: 'AWS',
    version: '5.12.0',
    icon: 'https://www.vectorlogo.zone/logos/amazon_aws/amazon_aws-icon.svg',
    status: 'Enabled',
    tags: ['provider', 'cloud', 'aws'],
    features: ['EKS Node Groups', 'S3 Bucket Policy', 'RDS Multi-AZ']
  },
  {
    id: 'azure-provider',
    name: 'Azure Provider',
    description: 'Microsoft Azure cloud services integration.',
    author: 'Microsoft',
    version: '3.0.0',
    icon: 'https://www.vectorlogo.zone/logos/microsoft_azure/microsoft_azure-icon.svg',
    status: 'Enabled',
    tags: ['provider', 'cloud', 'azure'],
    features: ['AKS Clusters', 'Blob Storage', 'Azure Functions']
  },
  {
    id: 'do-provider',
    name: 'DigitalOcean Provider',
    description: 'Simple cloud hosting integration for developers.',
    author: 'DigitalOcean',
    version: '2.5.0',
    icon: 'https://www.vectorlogo.zone/logos/digitalocean/digitalocean-icon.svg',
    status: 'Enabled',
    tags: ['provider', 'cloud', 'digitalocean'],
    features: ['Droplets', 'Kubernetes', 'Spaces']
  },
  {
    id: 'kubernetes-core',
    name: 'Kubernetes Core',
    description: 'Fundamental Kubernetes integration for cluster management and monitoring.',
    author: 'CNCF',
    version: '1.28.0',
    icon: 'https://www.vectorlogo.zone/logos/kubernetes/kubernetes-icon.svg',
    status: 'Enabled',
    tags: ['core', 'container', 'orchestration'],
    features: ['Pod Logs', 'Resource Quotas', 'Helm Chart Deployment']
  },
  {
    id: 'terraform-cloud',
    name: 'Terraform Cloud',
    description: 'Infrastructure as Code state management and remote execution.',
    author: 'HashiCorp',
    version: '1.6.0',
    icon: 'https://www.vectorlogo.zone/logos/terraformio/terraformio-icon.svg',
    status: 'Enabled',
    tags: ['iac', 'automation'],
    features: ['State Locking', 'Remote Runs', 'Policy Sentinel']
  },
  {
    id: 'argocd',
    name: 'ArgoCD',
    description: 'Declarative, GitOps continuous delivery tool for Kubernetes.',
    author: 'Argo Proj',
    version: '2.8.4',
    icon: 'https://www.vectorlogo.zone/logos/argoproj/argoproj-icon.svg',
    status: 'Disabled',
    tags: ['gitops', 'cd', 'k8s'],
    features: ['Git Sync', 'Application Health', 'Visual Diff']
  },
  {
    id: 'datadog',
    name: 'Datadog',
    description: 'Unified monitoring and analytics platform for developers.',
    author: 'Datadog',
    version: '3.1.0',
    icon: 'https://www.vectorlogo.zone/logos/datadoghq/datadoghq-icon.svg',
    status: 'Disabled',
    tags: ['monitoring', 'observability'],
    features: ['APM Tracing', 'Log Management', 'Custom Dashboards']
  },
  {
    id: 'github-actions',
    name: 'GitHub Actions',
    description: 'Automate your workflow from idea to production.',
    author: 'GitHub',
    version: '2.0.0',
    icon: 'https://www.vectorlogo.zone/logos/github/github-icon.svg',
    status: 'Disabled',
    tags: ['ci/cd', 'scm'],
    features: ['Workflow Triggering', 'Status Checks', 'Artifact Management']
  },
  {
    id: 'vault',
    name: 'HashiCorp Vault',
    description: 'Manage secrets and protect sensitive data.',
    author: 'HashiCorp',
    version: '1.14.0',
    icon: 'https://www.vectorlogo.zone/logos/hashicorp_vault/hashicorp_vault-icon.svg',
    status: 'Disabled',
    tags: ['security', 'secrets'],
    features: ['Dynamic Secrets', 'Encryption as Service', 'Identity Management']
  }
];

export const MOCK_BUILDS: Build[] = [
    {
        id: '#4291',
        project: 'payment-service',
        branch: 'main',
        commit: 'feat: update stripe api',
        status: 'Running',
        startedAt: new Date(),
        duration: '1m 45s',
        initiator: 'Alex Engineer'
    },
    {
        id: '#4290',
        project: 'frontend-dashboard',
        branch: 'fix/login-bug',
        commit: 'fix: resolve auth token issue',
        status: 'Success',
        startedAt: new Date(Date.now() - 1000 * 60 * 15), // 15 mins ago
        duration: '3m 20s',
        initiator: 'Sarah Chen'
    },
     {
        id: '#4289',
        project: 'notification-worker',
        branch: 'chore/cleanup',
        commit: 'chore: remove unused logs',
        status: 'Failed',
        startedAt: new Date(Date.now() - 1000 * 60 * 45),
        duration: '45s',
        initiator: 'CI Bot'
    },
    {
        id: '#4288',
        project: 'user-service',
        branch: 'main',
        commit: 'perf: optimize queries',
        status: 'Success',
        startedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
        duration: '5m 10s',
        initiator: 'Mike Ross'
    }
];