import { ServiceTemplate } from './types';

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



