# Foundry Platform - Internal Developer Platform (IDP)

A production-ready, enterprise-grade Internal Developer Platform for streamlined infrastructure provisioning, microservice management, and multi-cloud deployment orchestration.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://www.typescriptlang.org/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Core Features](#-core-features)
- [API Endpoints](#-api-endpoints)
- [Database Models](#-database-models)
- [Frontend Pages](#-frontend-pages)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Security](#-security)
- [Development](#-development)
- [Production Deployment](#-production-deployment)

---

## 🎯 Overview

**Foundry Platform** is a comprehensive Internal Developer Platform that enables organizations to:

- **Provision Infrastructure**: Deploy cloud resources across AWS, GCP, and Azure using Pulumi-based plugins
- **Manage Microservices**: Create, deploy, and manage microservices with GitOps workflows
- **Multi-Tenant Support**: Organization-based isolation with Casbin RBAC
- **Plugin System**: Extensible architecture with custom infrastructure templates
- **CI/CD Integration**: Native GitHub Actions integration with webhook support
- **OIDC Authentication**: Workload identity federation for secure cloud access
- **Audit Logging**: Complete activity tracking and compliance monitoring

---

## 📸 Screenshots

### Login
![Login](screenshots/login.png)
*User authentication interface with email and password login*

### Dashboard
![Dashboard](screenshots/dashboard.png)
*Main dashboard showing deployments, plugins, and notifications overview*

### Service Catalog
![Service Catalog](screenshots/service-catalog.png)
*Service catalog displaying available plugins and infrastructure templates*

### Jobs
![Jobs](screenshots/jobs.png)
*Job management interface showing provisioning job status, logs, and history*

### Plugin Upload
![Plugin Upload](screenshots/plugin-upload.png)
*Plugin upload interface for uploading Pulumi-based infrastructure plugins*

### User Management
![User Management](screenshots/user-management.png)
*User management interface for creating, updating, and managing users*

### Group Management
![Group Management](screenshots/group-management.png)
*Group management interface with role assignment and member management*

### Role Management
![Role Management](screenshots/role-management.png)
*Role management interface with permission assignment and metadata*

### Audit Logs
![Audit Logs](screenshots/audit-logs.png)
*Audit logs interface showing complete activity tracking and compliance monitoring*

### Profile
![Profile](screenshots/profile.png)
*User profile management interface with avatar upload and personal information*

---

## 🏗️ Architecture

### Backend Stack

```
FastAPI (Python 3.11+)
├── Database: PostgreSQL + SQLAlchemy ORM (Async)
├── Authorization: Casbin (RBAC with domain isolation)
├── Task Queue: Celery + Redis
├── IaC Engine: Pulumi
├── Git Operations: GitPython
├── Cloud SDKs: boto3 (AWS), Google Cloud, Azure SDK
├── Encryption: Cryptography (Fernet)
└── Authentication: JWT (Access + Refresh tokens)
```

### Frontend Stack

```
React 18 + TypeScript
├── Build Tool: Vite
├── Routing: React Router v6
├── State: React Context + Hooks
├── Styling: Tailwind CSS
├── Icons: Lucide React
└── API Client: Axios
```

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  Dashboard | Provision | Users | Roles | Groups | Plugins   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTPS/JWT
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Auth API   │  │  Plugin API  │  │  Deploy API  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Casbin RBAC  │  │    Celery    │  │  Pulumi Svc  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │    │    Redis     │    │    GitHub    │
└──────────────┘    └──────────────┘    └──────────────┘
         ↓                                        ↓
┌──────────────────────────────────────────────────────────────┐
│              Cloud Providers (via OIDC)                       │
│         AWS          │        GCP       │       Azure        │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ Core Features

### 🔐 Advanced RBAC & Multi-Tenancy

- **Organization Isolation**: Each organization operates in its own domain with complete data isolation
- **Business Unit Separation**: Multi-tenant data isolation with business unit-scoped permissions and resources
- **Casbin Integration**: Policy-based access control with high performance (10K+ rules)
- **Hierarchical Permissions**: `User → Groups → Roles → Permissions`
- **Multiple Group Membership**: Users inherit permissions from all groups
- **Domain-Aware Enforcement**: Automatic organization context in all authorization checks
- **Business Unit-Scoped RBAC**: Permissions evaluated within business unit context for complete data isolation
- **Platform vs BU Roles**: Platform-level roles (admin) vs business unit-scoped roles (developer, engineer, viewer)
- **Granular Permissions**: Fine-grained control over resources and actions
- **Environment-Based Permissions**: Separate permissions for development, staging, and production environments
- **Permission Debugging**: Debug endpoints to inspect user permissions and roles

### 👥 User & Access Management

- **User Management**: Create, update, delete users with profile support
- **Business Unit Management**: Create and manage business units with owners and members
- **Business Unit Owners**: Owners can manage members and approve plugin access requests
- **Group Management**: Organize users by teams, departments, or functions (scoped to business units)
- **Role Management**: Custom roles with specific permission sets (global roles, reusable across BUs)
- **Business Unit Membership**: Users can belong to multiple business units with different roles in each
- **Active Business Unit Selection**: Users select an active business unit for their session
- **Avatar Support**: Upload and manage user avatars
- **Profile Management**: Users can update their own profiles
- **Password Management**: Secure password change with verification

### 🔧 Plugin System

- **Upload Infrastructure Plugins**: Pulumi-based ZIP file uploads with validation
- **Microservice Templates**: GitOps-based microservice scaffolding
- **Version Management**: Multiple versions per plugin with automatic latest selection
- **Multi-Cloud Support**: AWS, GCP, Azure, Kubernetes
- **Dynamic Forms**: Auto-generated input forms from plugin schemas
- **Plugin Locking**: Restrict plugin access with approval workflows
- **Access Requests**: Users can request access to locked plugins
- **GitOps Integration**: Automatic Git branch creation for each plugin
- **Environment-Aware Provisioning**: Deploy to specific environments with permission checks
- **Tag Validation**: Enforce required tags (team, owner, purpose) during provisioning

### 🚀 Infrastructure Provisioning

- **Pulumi Integration**: Full Infrastructure as Code support
- **Async Processing**: Background job processing with Celery
- **Job Management**: Complete history, logs, and status tracking
- **Retry Logic**: Automatic retries with dead-letter queue for failed jobs
- **OIDC Credentials**: Workload Identity Federation for secure cloud access
- **Multi-Cloud Deployment**: Deploy to AWS, GCP, Azure from single interface
- **Deployment Tracking**: Real-time status updates and output capture
- **Environment Separation**: Deploy to development, staging, or production with strict access control
- **Tagging System**: Flexible key-value tags for cost tracking and resource organization
- **Cost Tracking**: Built-in cost center and project code fields for financial management

### 🏭 Microservice Management

- **Template-Based Generation**: Create microservices from Git templates
- **GitHub Integration**: Automatic repository creation and initialization
- **CI/CD Setup**: GitHub Actions workflows with webhook integration
- **Real-Time Status**: Live CI/CD pipeline status updates
- **Branch Management**: Automatic deployment branch creation
- **Repository Webhooks**: Receive build status updates automatically

### 🔔 Notifications & Audit

- **Real-Time Notifications**: Job status, access approvals, system events
- **Unread Tracking**: Mark notifications as read/unread
- **Action Links**: Direct links to related resources
- **Audit Logging**: Complete activity tracking with middleware
- **Search & Filter**: Advanced filtering by user, action, resource, date
- **Compliance Ready**: Full audit trail for security compliance

### 🔒 Security Features

- **JWT Authentication**: Access tokens (15min) + Refresh tokens (7 days)
- **HTTP-Only Cookies**: Secure refresh token storage
- **Password Hashing**: Bcrypt with secure password policies
- **OIDC Provider**: Built-in OpenID Connect server for cloud workload identity
- **Encrypted Credentials**: Fernet encryption for sensitive data
- **CORS Configuration**: Secure cross-origin resource sharing
- **Rate Limiting Ready**: Infrastructure for rate limiting
- **Environment-Based Access Control**: Strict permissions for development/staging/production
- **Tag Validation**: Required tags for all deployments with format validation

---

## 📡 API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/login` | Login with email/password, returns JWT + refresh token | No |
| POST | `/refresh` | Refresh access token using refresh token cookie | Yes (Refresh) |
| POST | `/logout` | Logout and invalidate refresh token | Yes |

### Users (`/api/v1/users`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/me` | Get current user profile | `profile:read` |
| PUT | `/me` | Update current user profile | `profile:update` |
| POST | `/me/avatar` | Upload user avatar | `profile:update` |
| PUT | `/me/password` | Change password | `profile:update` |
| GET | `/me/permissions` | Get current user's permissions | Authenticated |
| GET | `/me/debug` | Debug endpoint for user permissions/roles | Authenticated |
| GET | `/stats` | Get user statistics (admin dashboard) | `users:list` |
| GET | `/` | List users (paginated, searchable) | `users:list` |
| POST | `/` | Create new user | `users:create` |
| PUT | `/{user_id}` | Update user | `users:update` |
| DELETE | `/{user_id}` | Delete user | `users:delete` |

**Query Parameters for List:**
- `skip`: Pagination offset (default: 0)
- `limit`: Page size (default: 50)
- `search`: Search by email, username, or full name
- `role`: Filter by role name

### Roles (`/api/v1/roles`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List all roles with permissions | `roles:list` |
| POST | `/` | Create new role | `roles:create` |
| GET | `/{role_id}` | Get role details | `roles:read` |
| PUT | `/{role_id}` | Update role | `roles:update` |
| DELETE | `/{role_id}` | Delete role | `roles:delete` |

### Groups (`/api/v1/groups`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List all groups | `groups:list` |
| POST | `/` | Create new group | `groups:create` |
| GET | `/{group_id}` | Get group details | `groups:read` |
| PUT | `/{group_id}` | Update group | `groups:update` |
| DELETE | `/{group_id}` | Delete group | `groups:delete` |
| POST | `/{group_id}/users/{user_id}` | Add user to group | `groups:manage` |
| DELETE | `/{group_id}/users/{user_id}` | Remove user from group | `groups:manage` |
| POST | `/{group_id}/roles/{role_id}` | Assign role to group | `groups:manage` |
| DELETE | `/{group_id}/roles/{role_id}` | Remove role from group | `groups:manage` |

### Permissions (`/api/v1/permissions`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List all available permissions | `permissions:list` |

**Available Permission Categories:**
- **User Specific**: `profile:read`, `profile:update`, `deployments:list:own`, `deployments:update:own`, `deployments:delete:own`
- **User Management**: `users:list`, `users:create`, `users:update`, `users:delete`, `users:read`
- **Group Management**: `groups:list`, `groups:create`, `groups:update`, `groups:delete`, `groups:read`, `groups:manage`
- **Role Management**: `roles:list`, `roles:create`, `roles:update`, `roles:delete`, `roles:read`
- **Permission Management**: `permissions:list`
- **Deployment Management**: `deployments:list`, `deployments:read`, `deployments:update`, `deployments:delete`
- **Deployment - Development**: `deployments:create:development`, `deployments:update:development`, `deployments:delete:development`
- **Deployment - Staging**: `deployments:create:staging`, `deployments:update:staging`, `deployments:delete:staging`
- **Deployment - Production**: `deployments:create:production`, `deployments:update:production`, `deployments:delete:production`
- **Plugin Management**: `plugins:upload`, `plugins:delete`, `plugins:provision`
- **Audit**: `audit:read`

**Permission Format:**
- General: `resource:action` (e.g., `users:list`, `roles:read`)
- Environment-specific: `resource:action:environment` (e.g., `deployments:create:development`)
- User-specific: `resource:action:own` (e.g., `deployments:list:own`, `deployments:update:own`)

### Organizations (`/api/v1/organizations`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List all organizations | Admin only |
| GET | `/current` | Get current user's organization | Authenticated |
| POST | `/` | Create new organization | Admin only |
| GET | `/{org_id}` | Get organization details | Admin only |
| PUT | `/{org_id}` | Update organization | Admin only |
| DELETE | `/{org_id}` | Delete organization | Admin only |

### Plugins (`/api/v1/plugins`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List all plugins | Authenticated |
| POST | `/upload` | Upload plugin ZIP file | `plugins:upload` |
| POST | `/upload-template` | Create microservice template | `plugins:upload` |
| GET | `/{plugin_id}` | Get plugin details | Authenticated |
| DELETE | `/{plugin_id}` | Delete plugin | `plugins:delete` |
| PUT | `/{plugin_id}/lock` | Lock plugin (require access approval) | `plugins:upload` |
| PUT | `/{plugin_id}/unlock` | Unlock plugin | `plugins:upload` |
| GET | `/{plugin_id}/versions` | List plugin versions | Authenticated |
| GET | `/{plugin_id}/versions/{version}` | Get specific version | Authenticated |

**Plugin Access Management:**

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/{plugin_id}/access/request` | Request access to locked plugin | Authenticated |
| GET | `/{plugin_id}/access/requests` | List access requests for plugin | `plugins:upload` |
| GET | `/access/requests` | List all access requests | `plugins:upload` |
| POST | `/{plugin_id}/access/grant` | Grant access to user | `plugins:upload` |
| DELETE | `/{plugin_id}/access/{user_id}` | Revoke user access | `plugins:upload` |
| POST | `/{plugin_id}/access/{user_id}/restore` | Restore revoked access | `plugins:upload` |
| GET | `/{plugin_id}/access` | List users with access | `plugins:upload` |
| GET | `/access/grants` | List all access grants | `plugins:upload` |

### Provisioning (`/api/v1/provision`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/` | Trigger provisioning job | `plugins:provision` + environment-specific permission |
| GET | `/jobs` | List jobs (filterable, paginated) | Authenticated |
| GET | `/jobs/{job_id}` | Get job status | Authenticated |
| GET | `/jobs/{job_id}/logs` | Get job logs | Authenticated |
| POST | `/jobs/{job_id}/replay` | Replay dead-letter job | `plugins:provision` |
| DELETE | `/jobs/{job_id}` | Delete job | Admin only |
| POST | `/jobs/bulk-delete` | Delete multiple jobs | Admin only |

**Provisioning Request Body:**
- `environment`: Required - `development`, `staging`, or `production`
- `tags`: Required - Key-value pairs (must include: `team`, `owner`, `purpose`)
- `deployment_name`: Optional - Custom name for the deployment
- `cost_center`: Optional - Cost center code for financial tracking
- `project_code`: Optional - Project identifier

**Environment Permissions:**
- `deployments:development:create` - Engineers and admins
- `deployments:staging:create` - Senior engineers and admins
- `deployments:production:create` - Admins only

**Job Query Parameters:**
- `job_id`: Filter by job ID (partial match)
- `email`: Filter by triggered_by email
- `start_date`: Filter by start date (ISO format)
- `end_date`: Filter by end date (ISO format)
- `skip`: Pagination offset
- `limit`: Page size (max 50)

### Deployments (`/api/v1/deployments`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List deployments | `deployments:list` or `deployments:list:own` |
| POST | `/` | Create deployment record | `deployments:create` |
| GET | `/{deployment_id}` | Get deployment details | `deployments:list` or `deployments:list:own` (if own) |
| POST | `/{deployment_id}/retry` | Retry failed deployment | `deployments:update` or `deployments:update:own` (if own) |
| DELETE | `/{deployment_id}` | Destroy deployment | `deployments:delete` or `deployments:delete:own` (if own) |
| GET | `/{deployment_id}/ci-cd-status` | Get CI/CD status (microservices) | Authenticated |
| POST | `/{deployment_id}/sync-ci-cd` | Sync CI/CD status from GitHub | `deployments:update` |
| GET | `/{deployment_id}/repository` | Get repository info (microservices) | Authenticated |
| GET | `/environments` | List available environments | Authenticated |
| GET | `/tags/keys` | List unique tag keys (autocomplete) | Authenticated |
| GET | `/tags/values/{key}` | List values for a tag key | Authenticated |
| POST | `/{deployment_id}/tags` | Add/update tags for deployment | `deployments:update` |
| DELETE | `/{deployment_id}/tags/{key}` | Remove tag from deployment | `deployments:update` |
| GET | `/stats/by-environment` | Get deployment statistics by environment | Authenticated |
| GET | `/stats/tags` | Get tag usage statistics | Authenticated |

**Deployment Query Parameters:**
- `search`: Search by name, plugin_id, stack_name, region
- `status`: Filter by status (active, provisioning, failed, deleted)
- `environment`: Filter by environment (development, staging, production)
- `cloud_provider`: Filter by provider (aws, gcp, azure)
- `plugin_id`: Filter by plugin ID
- `tags`: Filter by tags (key=value format)
- `skip`: Pagination offset
- `limit`: Page size (max 50)

### Notifications (`/api/v1/notifications`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | List user notifications | Yes |
| PUT | `/{notification_id}/read` | Mark notification as read | Yes |
| PUT | `/read-all` | Mark all notifications as read | Yes |
| DELETE | `/{notification_id}` | Delete notification | Yes |

**Query Parameters:**
- `limit`: Max notifications to return (default: 50)
- `skip`: Pagination offset
- `unread_only`: Show only unread notifications

### Audit Logs (`/api/v1/audit-logs`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/` | List audit logs (paginated, filterable) | Admin only |
| GET | `/{log_id}` | Get specific audit log | Admin only |

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Page size (1-100, default: 50)
- `user_id`: Filter by user UUID
- `action`: Filter by action type
- `resource_type`: Filter by resource type
- `resource_id`: Filter by resource UUID
- `start_date`: Filter by start date (ISO format)
- `end_date`: Filter by end date (ISO format)
- `search`: Search in details, action, resource type
- `status`: Filter by status (success, failure)

### Cloud Credentials (`/api/v1/admin/credentials`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/` | Create/update credentials | Admin only |
| GET | `/` | List all credentials | Admin only |
| GET | `/{credential_id}` | Get credential details | Admin only |
| DELETE | `/{credential_id}` | Delete credential | Admin only |

### OIDC Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/.well-known/openid-configuration` | OIDC discovery endpoint | No |
| GET | `/.well-known/jwks.json` | JSON Web Key Set | No |
| POST | `/oidc/token` | Issue OIDC token (testing) | No |

**Cloud-Specific OIDC:**
- `/api/oidc/aws/token` - AWS STS token exchange
- `/api/oidc/azure/token` - Azure token exchange
- `/api/oidc/gcp/token` - GCP access token exchange

### Webhooks (`/api/webhooks`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/github` | GitHub webhook for CI/CD updates | No (Signature verified) |

---

## 🗄️ Database Models

### Core Models

#### Organization
```python
- id: UUID (PK)
- name: String(255) UNIQUE
- slug: String(255) UNIQUE
- description: String(1000)
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

#### User
```python
- id: UUID (PK)
- email: String(255) UNIQUE
- username: String(255) UNIQUE
- hashed_password: String(255)
- full_name: String(255)
- avatar_url: String(500)
- is_active: Boolean
- organization_id: UUID (FK -> organizations.id)
- active_business_unit_id: UUID (FK -> business_units.id) - User's selected active BU
- aws_role_arn: String(255)
- gcp_service_account: String(255)
- azure_client_id: String(255)
- created_at: DateTime
- updated_at: DateTime
```

#### BusinessUnit
```python
- id: UUID (PK)
- name: String(255)
- code: String(50) UNIQUE - Short code for the business unit (e.g., "It-Operations")
- description: String(1000)
- owner_id: UUID (FK -> users.id) - Business unit owner
- organization_id: UUID (FK -> organizations.id)
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

#### BusinessUnitMember
```python
- id: UUID (PK)
- business_unit_id: UUID (FK -> business_units.id)
- user_id: UUID (FK -> users.id)
- role_id: UUID (FK -> roles.id) - Role in this business unit
- created_at: DateTime
- updated_at: DateTime
UNIQUE(business_unit_id, user_id) - One role per user per BU
```

#### BusinessUnitGroup
```python
- id: UUID (PK)
- business_unit_id: UUID (FK -> business_units.id)
- name: String(255)
- description: String(500)
- role_id: UUID (FK -> roles.id) - Role assigned to group members
- created_at: DateTime
- updated_at: DateTime
UNIQUE(business_unit_id, name) - Unique group name per BU
```

#### BusinessUnitGroupMember
```python
- id: UUID (PK)
- group_id: UUID (FK -> business_unit_groups.id)
- user_id: UUID (FK -> users.id)
- created_at: DateTime
UNIQUE(group_id, user_id) - One membership per user per group
```

#### Role
```python
- id: UUID (PK)
- name: String(255) UNIQUE
- description: String(500)
- is_platform_role: Boolean - True for platform-level roles (admin), False for BU-scoped roles
- created_at: DateTime
- updated_at: DateTime
```

#### Group
```python
- id: UUID (PK)
- name: String(255) UNIQUE
- description: String(500)
- created_at: DateTime
- updated_at: DateTime
```

### Plugin Models

#### Plugin
```python
- id: String (PK)
- name: String
- description: Text
- author: String
- is_locked: Boolean (default: False)
- deployment_type: String(50) (infrastructure|microservice)
- created_at: DateTime
- updated_at: DateTime
```

#### PluginVersion
```python
- id: Integer (PK, Auto)
- plugin_id: String (FK)
- version: String
- manifest: JSON
- storage_path: String
- git_repo_url: String
- git_branch: String
- template_repo_url: String
- template_path: String
- created_at: DateTime
```

#### PluginAccess
```python
- id: Integer (PK, Auto)
- plugin_id: String (FK)
- user_id: UUID (FK)
- granted_by: UUID (FK)
- granted_at: DateTime
UNIQUE(plugin_id, user_id)
```

#### PluginAccessRequest
```python
- id: UUID (PK)
- plugin_id: String (FK)
- user_id: UUID (FK)
- business_unit_id: UUID (FK -> business_units.id) - Business unit context for the request
- status: Enum (pending|approved|rejected|revoked)
- requested_at: DateTime
- reviewed_at: DateTime
- reviewed_by: UUID (FK)
```

### Deployment Models

#### Deployment
```python
- id: UUID (PK)
- name: String(255)
- status: String(50) (active|provisioning|failed|deleted)
- deployment_type: String(50) (infrastructure|microservice)
- environment: String(50) (development|staging|production) - Indexed
- business_unit_id: UUID (FK -> business_units.id) - Business unit this deployment belongs to
- cost_center: String(100) - Optional, for cost tracking
- project_code: String(100) - Optional, for project identification
- plugin_id: String
- version: String
- stack_name: String(255)
- cloud_provider: String(50)
- region: String(100)
- git_branch: String(255)
- github_repo_url: String(500)
- github_repo_name: String(255)
- ci_cd_status: String(50)
- ci_cd_run_id: BigInteger
- ci_cd_run_url: String(500)
- ci_cd_updated_at: DateTime
- inputs: JSONB
- outputs: JSONB
- user_id: UUID (FK)
- created_at: DateTime
- updated_at: DateTime
```

#### DeploymentTag
```python
- id: UUID (PK)
- deployment_id: UUID (FK -> deployments.id, CASCADE delete)
- key: String(100) - Tag key (e.g., "team", "owner", "purpose")
- value: String(255) - Tag value
- created_at: DateTime
- UNIQUE(deployment_id, key) - One tag key per deployment
```

### Job Models

#### Job
```python
- id: String (PK, UUID)
- plugin_version_id: Integer (FK)
- deployment_id: UUID (FK)
- status: Enum (pending|running|success|failed|cancelled|dead_letter)
- triggered_by: String
- inputs: JSON
- outputs: JSON
- retry_count: Integer (default: 0)
- error_state: String
- error_message: Text
- created_at: DateTime
- finished_at: DateTime
```

#### JobLog
```python
- id: Integer (PK, Auto)
- job_id: String (FK)
- timestamp: DateTime
- level: String (INFO|ERROR|WARNING)
- message: Text
```

### Security Models

#### CloudCredential
```python
- id: Integer (PK, Auto)
- name: String UNIQUE
- provider: Enum (aws|gcp|azure|kubernetes)
- encrypted_data: Text
- created_at: DateTime
- updated_at: DateTime
```

#### RefreshToken
```python
- id: UUID (PK)
- user_id: UUID (FK)
- token: String(500) UNIQUE
- expires_at: DateTime
- created_at: DateTime
```

#### AuditLog
```python
- id: UUID (PK)
- user_id: UUID (FK)
- action: String
- resource_type: String
- resource_id: UUID
- details: JSONB
- ip_address: String
- created_at: DateTime
```

#### Notification
```python
- id: UUID (PK)
- user_id: UUID (FK)
- title: String
- message: Text
- type: Enum (info|success|warning|error)
- link: String
- is_read: Boolean (default: False)
- created_at: DateTime
```

---

## 💻 Frontend Pages

### Public Pages
- **Login** (`/login`) - Email/password authentication

### User Pages
- **Dashboard** (`/`) - Overview with stats and recent activity
- **Profile** (`/profile`) - User profile management and avatar upload
- **Provision** (`/provision/:pluginId?`) - Infrastructure provisioning interface with environment selector and tags
- **Plugin Detail** (`/plugin/:pluginId`) - Plugin information and versions
- **Services** (`/services`) - List of deployed services/infrastructure with environment filtering
- **Service Detail** (`/service/:deploymentId`) - Deployment details, CI/CD status, environment badge, and tags
- **Job Status** (`/job/:jobId`) - Job execution logs and status
- **Deployment Status** (`/deployment/:deploymentId`) - Deployment tracking with environment and tags display

### Admin Pages
- **Admin Dashboard** (`/admin`) - System-wide statistics and metrics
- **Users Management** (`/users`) - CRUD operations for users
- **Roles Management** (`/roles`) - Role and permission management
- **Groups Management** (`/groups`) - Group management with member assignment
- **Plugin Upload** (`/admin/plugins/upload`) - Upload infrastructure plugins
- **Plugin Requests** (`/admin/plugin-requests`) - Approve/reject plugin access requests
- **Admin Jobs** (`/admin/jobs`) - View and manage all jobs
- **Audit Logs** (`/admin/audit`) - Complete audit trail
- **Settings** (`/admin/settings`) - System configuration

### Future Pages (Planned)
- **Catalog** (`/catalog`) - Plugin marketplace
- **Cost Analysis** (`/cost`) - Cloud spending analytics

---

## 🚀 Quick Start

### Prerequisites

- **PostgreSQL** (v14+)
- **Node.js** (v18+)
- **Python** (v3.11+)
- **UV** package manager
- **Redis** (v6+)

### Option 1: Automated Start (Recommended)

**Terminal 1 - Backend:**
```bash
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start-frontend.sh
```

Logs will be saved to:
- `logs/backend.log` - Backend API logs
- `logs/frontend.log` - Frontend dev server logs

### Option 2: Manual Start

**1. Backend Setup:**
```bash
cd backend

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Create .env file (see Configuration section)
cp .env.example .env
# Edit .env with your values

# Setup PostgreSQL database
createdb Foundry_platform

# Start backend server
uv run uvicorn app.main:app --reload --port 8000
```

**2. Celery Worker (separate terminal):**
```bash
cd backend
uv run celery -A app.worker worker --loglevel=info
```

**3. Frontend Setup:**
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Start dev server
npm run dev
```

### Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

### Default Admin Credentials

The system creates a default admin user on first startup. Check the backend logs for credentials, or use the values from your `.env` file:

```
Email: [ADMIN_EMAIL from .env]
Password: [ADMIN_PASSWORD from .env]
```

---

## ⚙️ Configuration

### Backend Environment Variables (`.env`)

#### Core Settings
```bash
PROJECT_NAME="Foundry Platform"
DEBUG=true
API_V1_STR="/api/v1"
```

#### Database
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/Foundry_platform
```

#### Security
```bash
SECRET_KEY=your-secret-key-min-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=your-fernet-encryption-key
```

#### Admin User
```bash
ADMIN_EMAIL=admin@example.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
```

#### CORS
```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

#### Redis & Celery
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

#### Pulumi
```bash
PULUMI_ACCESS_TOKEN=pul-your-token
PULUMI_CONFIG_PASSPHRASE=your-pulumi-passphrase
```

#### GitOps & Microservices
```bash
GITHUB_REPOSITORY=https://github.com/your-org/your-repo.git
GITHUB_TOKEN=ghp_your_personal_access_token
GIT_WORK_DIR=./storage/git-repos
GITHUB_TEMPLATE_REPO_URL=https://github.com/your-org/templates.git
GITHUB_WEBHOOK_SECRET=your-webhook-secret
WEBHOOK_BASE_URL=https://your-domain.com
MICROSERVICE_REPO_ORG=your-github-org
```

#### OIDC Configuration
```bash
OIDC_ISSUER=https://your-platform.com
```

#### AWS OIDC
```bash
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/FoundryPlatformRole
AWS_REGION=us-east-1
```

#### GCP OIDC
```bash
GCP_WORKLOAD_IDENTITY_POOL_ID=Foundry-pool
GCP_WORKLOAD_IDENTITY_PROVIDER_ID=Foundry-provider
GCP_SERVICE_ACCOUNT_EMAIL=Foundry@project.iam.gserviceaccount.com
GCP_PROJECT_ID=your-project-id
GCP_PROJECT_NUMBER=123456789012
```

#### Azure OIDC
```bash
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

#### Plugin Storage
```bash
PLUGINS_STORAGE_PATH=./storage/plugins
```

### Frontend Environment Variables

Create `frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000
```

---

## 🔒 Security

### Authentication Flow

1. **Login**: User submits email/password
2. **Token Generation**: Backend generates:
   - Access token (JWT, 15 min expiry)
   - Refresh token (UUID, 7 days expiry, stored in DB)
3. **Cookie Storage**: Refresh token stored in HTTP-only cookie
4. **API Requests**: Access token sent in Authorization header
5. **Token Refresh**: When access token expires, use refresh token to get new access token
6. **Logout**: Delete refresh token from DB and clear cookie

### Authorization Flow

1. **Request**: User makes API request with access token
2. **User Extraction**: Decode JWT to get user ID
3. **Organization Context**: Load user's organization
4. **Permission Check**: Casbin enforcer checks:
   - User's direct roles
   - Roles inherited from groups
   - Organization domain isolation
5. **Resource Access**: Grant or deny based on policies

### RBAC Model (Casbin)

**Business Unit-Scoped RBAC:**
```conf
[request_definition]
r = sub, dom, obj, act, bu

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
# Platform-level permissions (no BU required)
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act && p.sub == "platform-admin"

# Business unit-scoped permissions (BU required)
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act && r.bu == p.bu
```

**Example Policies:**
```
# Platform-level permissions (global)
p, platform-admin, org123, users, create
p, platform-admin, org123, business_units, create

# Business unit-scoped permissions
p, developer, org123, bu:bu-123:plugins, provision
p, engineer, org123, bu:bu-123:deployments, create:development
p, bu-owner, org123, bu:bu-123:business_units, manage_members

# Role assignments
g, user456, platform-admin, org123
g, user789, developer, org123
g, user789, bu-123, org123  # User is member of BU bu-123 with developer role
```

**Permission Scopes:**
- **Platform-level**: Actions that don't require a business unit (e.g., `users:create`, `business_units:create`)
- **Business Unit-scoped**: Actions that require an active business unit (e.g., `plugins:provision`, `deployments:create`)
- **User-specific**: Actions on user-owned resources (e.g., `deployments:list:own`)

### Security Best Practices

1. **Always use HTTPS in production**
2. **Change SECRET_KEY and ENCRYPTION_KEY**
3. **Use strong passwords (12+ characters)**
4. **Enable secure cookies** (set `secure=True` in `auth.py`)
5. **Rotate JWT secrets regularly**
6. **Use environment-specific credentials**
7. **Enable rate limiting in production**
8. **Monitor audit logs regularly**
9. **Set up database backups**
10. **Use OIDC for cloud credentials** (avoid static keys)

---

## 👨‍💻 Development

### Backend Development

```bash
cd backend

# Install dependencies
uv sync

# Run tests (if available)
uv run pytest

# Run with hot reload
uv run uvicorn app.main:app --reload --port 8000

# Format code
uv run black app/
uv run isort app/

# Check types
uv run mypy app/
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint

# Format
npm run format
```

### Database Migrations

The application uses SQLAlchemy's automatic table creation on startup. All tables are created automatically when the application starts. For production, consider using Alembic for migrations:

```bash
# Install Alembic
uv pip install alembic

# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

**Current Schema:**
- All tables are automatically created on application startup via `Base.metadata.create_all()`
- `permissions_metadata` table stores permission metadata (name, description, category, icon) for UI display
- `deployments` table includes `environment`, `cost_center`, and `project_code` columns
- `deployment_tags` table provides flexible key-value tagging with unique constraint on (deployment_id, key)

### Adding a New API Endpoint

1. **Create/Edit Router** in `backend/app/api/v1/`
2. **Define Pydantic Schema** in `backend/app/schemas/`
3. **Add Database Model** in `backend/app/models/` (if needed)
4. **Implement Business Logic** in router or `backend/app/services/`
5. **Add Permission Check** using `Depends(is_allowed("resource:action"))`
6. **Register Router** in `backend/app/main.py`
7. **Update Frontend API Client** in `frontend/services/api/`
8. **Create/Update Frontend Page** in `frontend/pages/`

### Testing

#### Quick Test Flow
1. Login with admin credentials
2. Create a business unit (e.g., "Engineering", code: "ENG")
3. Assign yourself or another user as the business unit owner
4. Add members to the business unit with roles (developer, engineer, viewer)
5. As a member, select the business unit as your active business unit
6. Upload a plugin and provision infrastructure
7. All deployments will be tagged with the business unit code

#### Business Unit Test Flow
1. **As Admin:**
   - Create a business unit (e.g., "IT Operations", code: "IT-OPS")
   - Assign a user as the business unit owner
2. **As Business Unit Owner:**
   - Add members to the business unit
   - Assign roles (developer, engineer, viewer)
   - Approve plugin access requests from members
3. **As Member:**
   - Select the business unit as your active business unit
   - Request access to locked plugins
   - Provision infrastructure (if you have the right role)
   - View only deployments from your active business unit

#### Upload Plugin Test
1. Navigate to `/admin/plugins/upload`
2. Upload a Pulumi plugin ZIP file
3. Plugin is validated and extracted
4. If GitOps enabled, pushed to GitHub branch
5. Plugin appears in `/provision` page

#### Provision Infrastructure Test
1. Navigate to `/provision`
2. Select a plugin
3. Fill in required inputs
4. Submit provisioning job
5. Monitor job status in real-time
6. View logs and outputs

---

## 🚀 Production Deployment

### Pre-Deployment Checklist

- [ ] Change `SECRET_KEY` to strong random value (32+ characters)
- [ ] Change `ENCRYPTION_KEY` to Fernet-compatible key
- [ ] Set `secure=True` for cookies in `backend/app/api/v1/auth.py`
- [ ] Enable HTTPS for all connections
- [ ] Use production-grade PostgreSQL (not localhost)
- [ ] Use production-grade Redis (with persistence)
- [ ] Set proper CORS origins (remove localhost)
- [ ] Configure proper logging and monitoring
- [ ] Set up database backups
- [ ] Use environment variables for all secrets
- [ ] Enable rate limiting
- [ ] Configure firewall rules
- [ ] Set up SSL certificates
- [ ] Configure OIDC issuer URL
- [ ] Set up cloud workload identity federation
- [ ] Configure GitHub webhooks
- [ ] Set up Celery with proper concurrency
- [ ] Enable audit log retention policy

### Deployment Options

#### Docker Deployment (Recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: Foundry_platform
      POSTGRES_USER: Foundry
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql+asyncpg://Foundry:${DB_PASSWORD}@db:5432/Foundry_platform
      REDIS_URL: redis://redis:6379/0
    env_file:
      - ./backend/.env
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  celery_worker:
    build: ./backend
    command: celery -A app.worker worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://Foundry:${DB_PASSWORD}@db:5432/Foundry_platform
      REDIS_URL: redis://redis:6379/0
    env_file:
      - ./backend/.env
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

Deploy:
```bash
docker-compose up -d
```

#### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (to be created).

#### Manual Deployment

1. **Setup PostgreSQL and Redis**
2. **Deploy Backend:**
   ```bash
   cd backend
   uv pip install --system .
   gunicorn -k uvicorn.workers.UvicornWorker app.main:app
   ```
3. **Deploy Celery Worker:**
   ```bash
   celery -A app.worker worker --loglevel=info --concurrency=4
   ```
4. **Build & Deploy Frontend:**
   ```bash
   cd frontend
   npm run build
   # Serve dist/ with nginx or other web server
   ```

### Monitoring & Logging

1. **Application Logs**: Use structured logging with JSON format
2. **Metrics**: Integrate Prometheus for metrics collection
3. **APM**: Consider using Datadog, New Relic, or Sentry
4. **Audit Logs**: Regularly export and archive audit logs
5. **Health Checks**: Monitor `/health` endpoint

---

## 🆕 Recent Updates & Improvements

### Business Unit-Scoped RBAC (Latest)

**New Features:**
- ✅ **Business Unit Separation**: Complete multi-tenant data isolation with business unit-scoped permissions
- ✅ **Business Unit Management**: Admins can create business units and assign owners
- ✅ **Owner Management**: Business unit owners can manage members and approve plugin access requests
- ✅ **Multi-BU Membership**: Users can belong to multiple business units with different roles in each
- ✅ **Active Business Unit Selection**: Users select an active business unit for their session
- ✅ **Automatic Data Filtering**: All deployments, jobs, and resources filtered by active business unit
- ✅ **BU-Scoped Permissions**: Permissions evaluated within business unit context for complete isolation
- ✅ **Platform vs BU Roles**: Platform-level roles (admin) vs business unit-scoped roles (developer, engineer, viewer)
- ✅ **Automatic Tagging**: Deployments automatically tagged with `business_unit=<BU_CODE>`
- ✅ **Plugin Access Requests**: Requests routed to business unit owners for approval
- ✅ **Business Unit Groups**: Groups scoped to business units with role assignments

**How It Works:**
1. **Platform Admins** create business units and assign owners
2. **Business Unit Owners** add members and assign roles (developer, engineer, viewer, etc.)
3. **Users** select an active business unit from their accessible business units
4. **All Actions** are scoped to the active business unit (deployments, jobs, plugin access)
5. **Permissions** are evaluated within the business unit context
6. **Data Isolation** ensures users only see resources from their active business unit

**Business Unit Roles:**
- **bu-owner**: Can manage members, approve plugin requests, manage groups
- **developer/engineer**: Can provision resources, deploy to development/staging
- **senior-engineer**: Can deploy to staging in addition to development
- **viewer**: Read-only access to business unit resources

### Permission System Redesign

**New Features:**
- ✅ **Permission Metadata System**: Centralized permission registry with name, description, category, and icon
- ✅ **User-Specific Permissions**: New category for user-owned resources (`deployments:list:own`, `deployments:update:own`, `deployments:delete:own`)
- ✅ **Permission Categories**: Permissions organized by category (User Specific, User Management, Deployment Management, etc.)
- ✅ **Enhanced UI**: Permissions displayed with metadata in role management interface
- ✅ **Automatic Table Creation**: All database tables created automatically on startup
- ✅ **Permission Registry**: Single source of truth for all permissions with metadata

**Permission Categories:**
- **User Specific**: Profile and own deployment management
- **User Management**: Organization-wide user administration
- **Group Management**: Team and group administration
- **Role Management**: Role and permission assignment
- **Permission Management**: Permission viewing and listing
- **Deployment Management**: General deployment operations
- **Deployment - Development/Staging/Production**: Environment-specific permissions
- **Plugin Management**: Plugin upload, deletion, and provisioning
- **Audit**: Audit log access

**API Enhancements:**
- Enhanced: `GET /api/v1/permissions/` - Returns permissions with full metadata (name, description, category, icon)
- Enhanced: `GET /api/v1/roles/{role_id}` - Returns role with enriched permission metadata
- Enhanced: `GET /api/v1/users/me/permissions` - Returns user permissions with metadata
- New: Permission metadata stored in `permissions_metadata` table for UI display

**UI Improvements:**
- ✅ Permissions grouped by category in role management
- ✅ Permission descriptions and icons displayed in UI
- ✅ Search and filter capabilities for permissions
- ✅ User-specific permissions clearly categorized
- ✅ Cleaner, more intuitive permission selection interface

**Database Changes:**
- Created `permissions_metadata` table for storing permission metadata
- Automatic table creation on application startup
- Permission metadata synchronized from registry to database

### Environment Separation & Tags

**Features:**
- ✅ Environment-based deployment (development, staging, production)
- ✅ Flexible key-value tagging system for deployments
- ✅ Cost tracking with `cost_center` and `project_code` fields
- ✅ Environment-specific permission enforcement
- ✅ Tag validation with required tags (team, owner, purpose)
- ✅ Environment filtering and statistics
- ✅ Visual environment badges and selectors in UI

**Bug Fixes:**
- ✅ Fixed deployment status stuck in "provisioning" when jobs fail
- ✅ Automatic cleanup of stuck deployments via Celery periodic tasks
- ✅ Fixed duplicate role display in user profile
- ✅ Fixed foreign key cascade issues for notifications
- ✅ Improved GCP OIDC error handling and diagnostics
- ✅ Fixed permission checking for environment-based deployments

---

## 📚 Additional Documentation

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc (ReDoc)
- **Casbin Documentation**: https://casbin.org/docs/overview
- **Pulumi Documentation**: https://www.pulumi.com/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/

---

## 🤝 Contributing

This is a production-ready IDP. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

[Specify your license here]

---

## 🙏 Acknowledgments

- **FastAPI** for the excellent Python web framework
- **Casbin** for the powerful authorization engine
- **Pulumi** for infrastructure as code
- **React** for the UI framework
- **Tailwind CSS** for beautiful styling
- The entire open-source community

---

## 📞 Support

For issues, questions, or support:
- Open an issue on GitHub
- Contact: ksajjad660@gmail.com

---

**Built with ❤️ by the Foundry Platform Team**
