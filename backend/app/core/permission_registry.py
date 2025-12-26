"""
Permission Registry - Centralized definition of all permissions with metadata.

New Permission Format with Scope Prefixes:
- Platform: platform:resource:action (e.g., platform:users:list, platform:roles:create)
- Business Unit: business_unit:resource:action:environment (e.g., business_unit:deployments:create:development)
- User/Individual: user:resource:action (e.g., user:profile:read, user:deployments:list:own)

Casbin Storage:
- Format: (role, org_domain, obj, act)
- obj = resource (e.g., "users", "deployments")
- act = action or action:environment (e.g., "list", "create:development")
"""

from typing import Dict, List, Optional

# Permission metadata structure
PermissionDefinition = Dict[str, str]

# All permissions with metadata - NEW SCOPE-PREFIXED FORMAT
PERMISSIONS: List[PermissionDefinition] = [
    # ============================================================================
    # PLATFORM LEVEL PERMISSIONS (platform:*)
    # ============================================================================
    
    # User Management
    {
        "slug": "platform:users:list",
        "name": "List All Users",
        "description": "View the list of all users in the organization",
        "category": "Platform - User Management",
        "resource": "users",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "👥"
    },
    {
        "slug": "platform:users:create",
        "name": "Create Users",
        "description": "Create new user accounts in the organization",
        "category": "Platform - User Management",
        "resource": "users",
        "action": "create",
        "environment": None,
        "scope": "platform",
        "icon": "➕"
    },
    {
        "slug": "platform:users:read",
        "name": "View User Details",
        "description": "View detailed information about users",
        "category": "Platform - User Management",
        "resource": "users",
        "action": "read",
        "environment": None,
        "scope": "platform",
        "icon": "👁️"
    },
    {
        "slug": "platform:users:update",
        "name": "Update Users",
        "description": "Modify user information and settings",
        "category": "Platform - User Management",
        "resource": "users",
        "action": "update",
        "environment": None,
        "scope": "platform",
        "icon": "✏️"
    },
    {
        "slug": "platform:users:delete",
        "name": "Delete Users",
        "description": "Remove user accounts from the system",
        "category": "Platform - User Management",
        "resource": "users",
        "action": "delete",
        "environment": None,
        "scope": "platform",
        "icon": "🗑️"
    },
    {
        "slug": "platform:users:stats",
        "name": "View User Statistics",
        "description": "View user statistics and metrics for admin dashboard",
        "category": "Platform - User Management",
        "resource": "users",
        "action": "stats",
        "environment": None,
        "scope": "platform",
        "icon": "📊"
    },
    
    # Role Management
    {
        "slug": "platform:roles:list",
        "name": "List Roles",
        "description": "View the list of all roles in the organization",
        "category": "Platform - Role Management",
        "resource": "roles",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "📋"
    },
    {
        "slug": "platform:roles:create",
        "name": "Create Roles",
        "description": "Create new roles with custom permissions",
        "category": "Platform - Role Management",
        "resource": "roles",
        "action": "create",
        "environment": None,
        "scope": "platform",
        "icon": "➕"
    },
    {
        "slug": "platform:roles:read",
        "name": "View Role Details",
        "description": "View detailed information about roles and their permissions",
        "category": "Platform - Role Management",
        "resource": "roles",
        "action": "read",
        "environment": None,
        "scope": "platform",
        "icon": "👁️"
    },
    {
        "slug": "platform:roles:update",
        "name": "Update Roles",
        "description": "Modify role permissions and settings",
        "category": "Platform - Role Management",
        "resource": "roles",
        "action": "update",
        "environment": None,
        "scope": "platform",
        "icon": "✏️"
    },
    {
        "slug": "platform:roles:delete",
        "name": "Delete Roles",
        "description": "Remove roles from the system",
        "category": "Platform - Role Management",
        "resource": "roles",
        "action": "delete",
        "environment": None,
        "scope": "platform",
        "icon": "🗑️"
    },
    
    # Group Management
    {
        "slug": "platform:groups:list",
        "name": "List Groups",
        "description": "View all groups in the organization",
        "category": "Platform - Group Management",
        "resource": "groups",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "👥"
    },
    {
        "slug": "platform:groups:create",
        "name": "Create Groups",
        "description": "Create new groups in the organization",
        "category": "Platform - Group Management",
        "resource": "groups",
        "action": "create",
        "environment": None,
        "scope": "platform",
        "icon": "➕"
    },
    {
        "slug": "platform:groups:read",
        "name": "View Group Details",
        "description": "View detailed information about groups",
        "category": "Platform - Group Management",
        "resource": "groups",
        "action": "read",
        "environment": None,
        "scope": "platform",
        "icon": "👁️"
    },
    {
        "slug": "platform:groups:update",
        "name": "Update Groups",
        "description": "Modify group settings and configurations",
        "category": "Platform - Group Management",
        "resource": "groups",
        "action": "update",
        "environment": None,
        "scope": "platform",
        "icon": "✏️"
    },
    {
        "slug": "platform:groups:delete",
        "name": "Delete Groups",
        "description": "Remove groups from the system",
        "category": "Platform - Group Management",
        "resource": "groups",
        "action": "delete",
        "environment": None,
        "scope": "platform",
        "icon": "🗑️"
    },
    {
        "slug": "platform:groups:manage",
        "name": "Manage Group Members",
        "description": "Add or remove users from groups and assign roles to groups",
        "category": "Platform - Group Management",
        "resource": "groups",
        "action": "manage",
        "environment": None,
        "scope": "platform",
        "icon": "👤"
    },
    
    # Permission Management
    {
        "slug": "platform:permissions:list",
        "name": "List Permissions",
        "description": "View all available permissions in the system",
        "category": "Platform - Permission Management",
        "resource": "permissions",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "🔑"
    },
    
    # Business Unit Management (Platform Level)
    {
        "slug": "platform:business_units:create",
        "name": "Create Business Units",
        "description": "Create new business units in the organization",
        "category": "Platform - Business Unit Management",
        "resource": "business_units",
        "action": "create",
        "environment": None,
        "scope": "platform",
        "icon": "➕"
    },
    {
        "slug": "platform:business_units:list",
        "name": "List Business Units",
        "description": "View all business units in the organization",
        "category": "Platform - Business Unit Management",
        "resource": "business_units",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "📋"
    },
    
    # Organization Management
    {
        "slug": "platform:organizations:list",
        "name": "List Organizations",
        "description": "View all organizations in the system",
        "category": "Platform - Organization Management",
        "resource": "organizations",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "🏢"
    },
    {
        "slug": "platform:organizations:create",
        "name": "Create Organizations",
        "description": "Create new organizations",
        "category": "Platform - Organization Management",
        "resource": "organizations",
        "action": "create",
        "environment": None,
        "scope": "platform",
        "icon": "➕"
    },
    {
        "slug": "platform:organizations:read",
        "name": "View Organization Details",
        "description": "View detailed information about organizations",
        "category": "Platform - Organization Management",
        "resource": "organizations",
        "action": "read",
        "environment": None,
        "scope": "platform",
        "icon": "👁️"
    },
    {
        "slug": "platform:organizations:update",
        "name": "Update Organizations",
        "description": "Modify organization information and settings",
        "category": "Platform - Organization Management",
        "resource": "organizations",
        "action": "update",
        "environment": None,
        "scope": "platform",
        "icon": "✏️"
    },
    {
        "slug": "platform:organizations:delete",
        "name": "Delete Organizations",
        "description": "Remove organizations from the system",
        "category": "Platform - Organization Management",
        "resource": "organizations",
        "action": "delete",
        "environment": None,
        "scope": "platform",
        "icon": "🗑️"
    },
    
    # Plugin Management (Platform Level)
    {
        "slug": "platform:plugins:upload",
        "name": "Upload Plugins",
        "description": "Upload new plugins to the system",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "upload",
        "environment": None,
        "scope": "platform",
        "icon": "📤"
    },
    {
        "slug": "platform:plugins:delete",
        "name": "Delete Plugins",
        "description": "Remove plugins from the system",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "delete",
        "environment": None,
        "scope": "platform",
        "icon": "🗑️"
    },
    {
        "slug": "platform:plugins:lock",
        "name": "Lock Plugins",
        "description": "Lock plugins to require access approval before use",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "lock",
        "environment": None,
        "scope": "platform",
        "icon": "🔒"
    },
    {
        "slug": "platform:plugins:unlock",
        "name": "Unlock Plugins",
        "description": "Unlock plugins to allow unrestricted access",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "unlock",
        "environment": None,
        "scope": "platform",
        "icon": "🔓"
    },
    {
        "slug": "platform:plugins:read",
        "name": "View Plugin Details",
        "description": "View detailed information about plugins",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "read",
        "environment": None,
        "scope": "platform",
        "icon": "👁️"
    },
    {
        "slug": "platform:plugins:list",
        "name": "List Plugins",
        "description": "View all plugins in the system",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "list",
        "environment": None,
        "scope": "platform",
        "icon": "📋"
    },
    {
        "slug": "platform:plugins:access:manage",
        "name": "Manage Plugin Access",
        "description": "Manage plugin access requests, grants, and revocations",
        "category": "Platform - Plugin Management",
        "resource": "plugins",
        "action": "access:manage",
        "environment": None,
        "scope": "platform",
        "icon": "🔐"
    },
    
    # Audit
    {
        "slug": "platform:audit:read",
        "name": "View Audit Logs",
        "description": "View system audit logs and activity history",
        "category": "Platform - Audit",
        "resource": "audit",
        "action": "read",
        "environment": None,
        "scope": "platform",
        "icon": "📊"
    },
    
    # ============================================================================
    # BUSINESS UNIT LEVEL PERMISSIONS (business_unit:*)
    # ============================================================================
    
    # Deployment Management
    {
        "slug": "business_unit:deployments:list",
        "name": "List Deployments",
        "description": "View all deployments in the business unit",
        "category": "Business Unit - Deployment Management",
        "resource": "deployments",
        "action": "list",
        "environment": None,
        "scope": "business_unit",
        "icon": "📦"
    },
    {
        "slug": "business_unit:deployments:read",
        "name": "View Deployment Details",
        "description": "View detailed information about deployments",
        "category": "Business Unit - Deployment Management",
        "resource": "deployments",
        "action": "read",
        "environment": None,
        "scope": "business_unit",
        "icon": "👁️"
    },
    {
        "slug": "business_unit:deployments:create:development",
        "name": "Deploy to Development Environment",
        "description": "Create and deploy infrastructure resources to the development environment. This allows provisioning new resources but not modifying or deleting existing ones.",
        "category": "Business Unit - Deployments - Development",
        "resource": "deployments",
        "action": "create",
        "environment": "development",
        "scope": "business_unit",
        "icon": "🔧"
    },
    {
        "slug": "business_unit:deployments:create:staging",
        "name": "Deploy to Staging Environment",
        "description": "Create and deploy infrastructure resources to the staging environment. This allows provisioning new resources but not modifying or deleting existing ones.",
        "category": "Business Unit - Deployments - Staging",
        "resource": "deployments",
        "action": "create",
        "environment": "staging",
        "scope": "business_unit",
        "icon": "🧪"
    },
    {
        "slug": "business_unit:deployments:create:production",
        "name": "Deploy to Production Environment",
        "description": "Create and deploy infrastructure resources to the production environment. This requires approval and allows provisioning new resources but not modifying or deleting existing ones.",
        "category": "Business Unit - Deployments - Production",
        "resource": "deployments",
        "action": "create",
        "environment": "production",
        "scope": "business_unit",
        "icon": "🚀"
    },
    {
        "slug": "business_unit:deployments:update:development",
        "name": "Update Development Deployments",
        "description": "Modify deployments in the development environment",
        "category": "Business Unit - Deployments - Development",
        "resource": "deployments",
        "action": "update",
        "environment": "development",
        "scope": "business_unit",
        "icon": "🔧"
    },
    {
        "slug": "business_unit:deployments:update:staging",
        "name": "Update Staging Deployments",
        "description": "Modify deployments in the staging environment",
        "category": "Business Unit - Deployments - Staging",
        "resource": "deployments",
        "action": "update",
        "environment": "staging",
        "scope": "business_unit",
        "icon": "🧪"
    },
    {
        "slug": "business_unit:deployments:update:production",
        "name": "Update Production Deployments",
        "description": "Modify deployments in the production environment (requires approval)",
        "category": "Business Unit - Deployments - Production",
        "resource": "deployments",
        "action": "update",
        "environment": "production",
        "scope": "business_unit",
        "icon": "🚀"
    },
    {
        "slug": "business_unit:deployments:delete:development",
        "name": "Delete Development Deployments",
        "description": "Remove deployments from the development environment",
        "category": "Business Unit - Deployments - Development",
        "resource": "deployments",
        "action": "delete",
        "environment": "development",
        "scope": "business_unit",
        "icon": "🔧"
    },
    {
        "slug": "business_unit:deployments:delete:staging",
        "name": "Delete Staging Deployments",
        "description": "Remove deployments from the staging environment",
        "category": "Business Unit - Deployments - Staging",
        "resource": "deployments",
        "action": "delete",
        "environment": "staging",
        "scope": "business_unit",
        "icon": "🧪"
    },
    {
        "slug": "business_unit:deployments:delete:production",
        "name": "Delete Production Deployments",
        "description": "Remove deployments from the production environment (requires approval)",
        "category": "Business Unit - Deployments - Production",
        "resource": "deployments",
        "action": "delete",
        "environment": "production",
        "scope": "business_unit",
        "icon": "🚀"
    },
    {
        "slug": "business_unit:deployments:retry",
        "name": "Retry Failed Deployments",
        "description": "Retry failed or errored deployments",
        "category": "Business Unit - Deployment Management",
        "resource": "deployments",
        "action": "retry",
        "environment": None,
        "scope": "business_unit",
        "icon": "🔄"
    },
    
    # Deployment History
    {
        "slug": "business_unit:deployments:history:read",
        "name": "View Deployment History",
        "description": "View deployment version history and changes",
        "category": "Business Unit - Deployment History",
        "resource": "deployments",
        "action": "history:read",
        "environment": None,
        "scope": "business_unit",
        "icon": "📜"
    },
    {
        "slug": "business_unit:deployments:history:rollback",
        "name": "Rollback Deployments",
        "description": "Rollback deployments to a previous version",
        "category": "Business Unit - Deployment History",
        "resource": "deployments",
        "action": "history:rollback",
        "environment": None,
        "scope": "business_unit",
        "icon": "⏪"
    },
    
    # Deployment Stats
    {
        "slug": "business_unit:deployments:stats:read",
        "name": "View Deployment Statistics",
        "description": "View deployment statistics and metrics",
        "category": "Business Unit - Deployment Statistics",
        "resource": "deployments",
        "action": "stats:read",
        "environment": None,
        "scope": "business_unit",
        "icon": "📊"
    },
    {
        "slug": "business_unit:deployments:stats:environments",
        "name": "View Environment Statistics",
        "description": "View deployment statistics by environment",
        "category": "Business Unit - Deployment Statistics",
        "resource": "deployments",
        "action": "stats:environments",
        "environment": None,
        "scope": "business_unit",
        "icon": "🌍"
    },
    {
        "slug": "business_unit:deployments:stats:tags",
        "name": "View Tag-Based Statistics",
        "description": "View deployment statistics grouped by tags",
        "category": "Business Unit - Deployment Statistics",
        "resource": "deployments",
        "action": "stats:tags",
        "environment": None,
        "scope": "business_unit",
        "icon": "🏷️"
    },
    
    # Deployment Tags
    {
        "slug": "business_unit:deployments:tags:read",
        "name": "View Deployment Tags",
        "description": "View tags associated with deployments",
        "category": "Business Unit - Deployment Tags",
        "resource": "deployments",
        "action": "tags:read",
        "environment": None,
        "scope": "business_unit",
        "icon": "🏷️"
    },
    {
        "slug": "business_unit:deployments:tags:create",
        "name": "Add Deployment Tags",
        "description": "Add tags to deployments for organization and filtering",
        "category": "Business Unit - Deployment Tags",
        "resource": "deployments",
        "action": "tags:create",
        "environment": None,
        "scope": "business_unit",
        "icon": "➕"
    },
    {
        "slug": "business_unit:deployments:tags:delete",
        "name": "Remove Deployment Tags",
        "description": "Remove tags from deployments",
        "category": "Business Unit - Deployment Tags",
        "resource": "deployments",
        "action": "tags:delete",
        "environment": None,
        "scope": "business_unit",
        "icon": "🗑️"
    },
    
    # Deployment CI/CD
    {
        "slug": "business_unit:deployments:cicd:read",
        "name": "View CI/CD Status",
        "description": "View CI/CD pipeline status and configuration for deployments",
        "category": "Business Unit - Deployment CI/CD",
        "resource": "deployments",
        "action": "cicd:read",
        "environment": None,
        "scope": "business_unit",
        "icon": "🔄"
    },
    {
        "slug": "business_unit:deployments:cicd:sync",
        "name": "Sync CI/CD Configuration",
        "description": "Synchronize CI/CD configuration for deployments",
        "category": "Business Unit - Deployment CI/CD",
        "resource": "deployments",
        "action": "cicd:sync",
        "environment": None,
        "scope": "business_unit",
        "icon": "🔄"
    },
    
    # Deployment Cost
    {
        "slug": "business_unit:deployments:cost:read",
        "name": "View Deployment Costs",
        "description": "View actual costs for deployments",
        "category": "Business Unit - Deployment Cost Analysis",
        "resource": "deployments",
        "action": "cost:read",
        "environment": None,
        "scope": "business_unit",
        "icon": "💰"
    },
    {
        "slug": "business_unit:deployments:cost:estimate",
        "name": "Estimate Deployment Costs",
        "description": "Estimate costs for deployments before provisioning",
        "category": "Business Unit - Deployment Cost Analysis",
        "resource": "deployments",
        "action": "cost:estimate",
        "environment": None,
        "scope": "business_unit",
        "icon": "💵"
    },
    {
        "slug": "business_unit:deployments:cost:trend",
        "name": "View Cost Trends",
        "description": "View cost trends and historical cost data",
        "category": "Business Unit - Deployment Cost Analysis",
        "resource": "deployments",
        "action": "cost:trend",
        "environment": None,
        "scope": "business_unit",
        "icon": "📈"
    },
    {
        "slug": "business_unit:deployments:cost:by_provider",
        "name": "View Costs by Provider",
        "description": "View costs grouped by cloud provider (AWS, GCP, Azure)",
        "category": "Business Unit - Deployment Cost Analysis",
        "resource": "deployments",
        "action": "cost:by_provider",
        "environment": None,
        "scope": "business_unit",
        "icon": "☁️"
    },
    {
        "slug": "business_unit:deployments:cost:aggregate",
        "name": "View Aggregate Costs",
        "description": "View aggregated cost data across deployments",
        "category": "Business Unit - Deployment Cost Analysis",
        "resource": "deployments",
        "action": "cost:aggregate",
        "environment": None,
        "scope": "business_unit",
        "icon": "📊"
    },
    
    # Plugin Provisioning
    {
        "slug": "business_unit:plugins:provision",
        "name": "Provision Resources",
        "description": "Use plugins to provision infrastructure and resources in the business unit",
        "category": "Business Unit - Plugin Provisioning",
        "resource": "plugins",
        "action": "provision",
        "environment": None,
        "scope": "business_unit",
        "icon": "⚙️"
    },
    {
        "slug": "business_unit:plugins:read",
        "name": "View Available Plugins",
        "description": "View plugins available for provisioning in the business unit",
        "category": "Business Unit - Plugin Provisioning",
        "resource": "plugins",
        "action": "read",
        "environment": None,
        "scope": "business_unit",
        "icon": "👁️"
    },
    
    # Jobs
    {
        "slug": "business_unit:jobs:list",
        "name": "List Provisioning Jobs",
        "description": "View all provisioning jobs in the business unit",
        "category": "Business Unit - Jobs",
        "resource": "jobs",
        "action": "list",
        "environment": None,
        "scope": "business_unit",
        "icon": "📋"
    },
    {
        "slug": "business_unit:jobs:read",
        "name": "View Job Details",
        "description": "View detailed information about provisioning jobs",
        "category": "Business Unit - Jobs",
        "resource": "jobs",
        "action": "read",
        "environment": None,
        "scope": "business_unit",
        "icon": "👁️"
    },
    {
        "slug": "business_unit:jobs:logs:read",
        "name": "View Job Logs",
        "description": "View logs from provisioning jobs",
        "category": "Business Unit - Jobs",
        "resource": "jobs",
        "action": "logs:read",
        "environment": None,
        "scope": "business_unit",
        "icon": "📝"
    },
    {
        "slug": "business_unit:jobs:replay",
        "name": "Replay Failed Jobs",
        "description": "Replay failed or dead-letter provisioning jobs",
        "category": "Business Unit - Jobs",
        "resource": "jobs",
        "action": "replay",
        "environment": None,
        "scope": "business_unit",
        "icon": "🔄"
    },
    {
        "slug": "business_unit:jobs:delete",
        "name": "Delete Jobs",
        "description": "Delete provisioning jobs from the system",
        "category": "Business Unit - Jobs",
        "resource": "jobs",
        "action": "delete",
        "environment": None,
        "scope": "business_unit",
        "icon": "🗑️"
    },
    
    # Business Unit Management (BU Level)
    {
        "slug": "business_unit:business_units:read",
        "name": "View Business Unit Details",
        "description": "View detailed information about a business unit",
        "category": "Business Unit - Business Unit Management",
        "resource": "business_units",
        "action": "read",
        "environment": None,
        "scope": "business_unit",
        "icon": "👁️"
    },
    {
        "slug": "business_unit:business_units:update",
        "name": "Update Business Unit",
        "description": "Modify business unit information and settings",
        "category": "Business Unit - Business Unit Management",
        "resource": "business_units",
        "action": "update",
        "environment": None,
        "scope": "business_unit",
        "icon": "✏️"
    },
    {
        "slug": "business_unit:business_units:delete",
        "name": "Delete Business Unit",
        "description": "Remove business units from the system",
        "category": "Business Unit - Business Unit Management",
        "resource": "business_units",
        "action": "delete",
        "environment": None,
        "scope": "business_unit",
        "icon": "🗑️"
    },
    {
        "slug": "business_unit:business_units:manage_members",
        "name": "Manage Business Unit Members",
        "description": "Add or remove members from a business unit and assign roles",
        "category": "Business Unit - Business Unit Management",
        "resource": "business_units",
        "action": "manage_members",
        "environment": None,
        "scope": "business_unit",
        "icon": "👤"
    },
    
    # Business Unit Groups
    {
        "slug": "business_unit:groups:list",
        "name": "List Business Unit Groups",
        "description": "View all groups within the business unit",
        "category": "Business Unit - Groups",
        "resource": "groups",
        "action": "list",
        "environment": None,
        "scope": "business_unit",
        "icon": "📋"
    },
    {
        "slug": "business_unit:groups:create",
        "name": "Create Business Unit Groups",
        "description": "Create new groups within the business unit",
        "category": "Business Unit - Groups",
        "resource": "groups",
        "action": "create",
        "environment": None,
        "scope": "business_unit",
        "icon": "➕"
    },
    {
        "slug": "business_unit:groups:read",
        "name": "View Business Unit Group Details",
        "description": "View detailed information about business unit groups",
        "category": "Business Unit - Groups",
        "resource": "groups",
        "action": "read",
        "environment": None,
        "scope": "business_unit",
        "icon": "👁️"
    },
    {
        "slug": "business_unit:groups:update",
        "name": "Update Business Unit Groups",
        "description": "Modify business unit group settings and configurations",
        "category": "Business Unit - Groups",
        "resource": "groups",
        "action": "update",
        "environment": None,
        "scope": "business_unit",
        "icon": "✏️"
    },
    {
        "slug": "business_unit:groups:delete",
        "name": "Delete Business Unit Groups",
        "description": "Remove groups from the business unit",
        "category": "Business Unit - Groups",
        "resource": "groups",
        "action": "delete",
        "environment": None,
        "scope": "business_unit",
        "icon": "🗑️"
    },
    {
        "slug": "business_unit:groups:manage_members",
        "name": "Manage Business Unit Group Members",
        "description": "Add or remove users from business unit groups",
        "category": "Business Unit - Groups",
        "resource": "groups",
        "action": "manage_members",
        "environment": None,
        "scope": "business_unit",
        "icon": "👤"
    },
    
    # Notifications
    {
        "slug": "business_unit:notifications:read",
        "name": "View Notifications",
        "description": "View notifications in the business unit",
        "category": "Business Unit - Notifications",
        "resource": "notifications",
        "action": "read",
        "environment": None,
        "scope": "business_unit",
        "icon": "🔔"
    },
    {
        "slug": "business_unit:notifications:update",
        "name": "Update Notifications",
        "description": "Mark notifications as read in the business unit",
        "category": "Business Unit - Notifications",
        "resource": "notifications",
        "action": "update",
        "environment": None,
        "scope": "business_unit",
        "icon": "✏️"
    },
    {
        "slug": "business_unit:notifications:delete",
        "name": "Delete Notifications",
        "description": "Delete notifications from the business unit",
        "category": "Business Unit - Notifications",
        "resource": "notifications",
        "action": "delete",
        "environment": None,
        "scope": "business_unit",
        "icon": "🗑️"
    },
    
    # ============================================================================
    # USER/INDIVIDUAL LEVEL PERMISSIONS (user:*)
    # ============================================================================
    
    # Profile
    {
        "slug": "user:profile:read",
        "name": "View Own Profile",
        "description": "View your own profile information",
        "category": "Individual - Profile",
        "resource": "profile",
        "action": "read",
        "environment": None,
        "scope": "user",
        "icon": "👤"
    },
    {
        "slug": "user:profile:update",
        "name": "Update Own Profile",
        "description": "Update your own profile information",
        "category": "Individual - Profile",
        "resource": "profile",
        "action": "update",
        "environment": None,
        "scope": "user",
        "icon": "✏️"
    },
    {
        "slug": "user:profile:avatar:update",
        "name": "Update Own Avatar",
        "description": "Upload or change your profile avatar",
        "category": "Individual - Profile",
        "resource": "profile",
        "action": "avatar:update",
        "environment": None,
        "scope": "user",
        "icon": "🖼️"
    },
    {
        "slug": "user:profile:password:update",
        "name": "Change Own Password",
        "description": "Change your own account password",
        "category": "Individual - Profile",
        "resource": "profile",
        "action": "password:update",
        "environment": None,
        "scope": "user",
        "icon": "🔒"
    },
    
    # Own Deployments
    {
        "slug": "user:deployments:list:own",
        "name": "List Own Deployments",
        "description": "View only your own deployments across all environments",
        "category": "Individual - Own Deployments",
        "resource": "deployments",
        "action": "list:own",
        "environment": None,
        "scope": "user",
        "icon": "📦"
    },
    {
        "slug": "user:deployments:read:own",
        "name": "View Own Deployment Details",
        "description": "View detailed information about your own deployments",
        "category": "Individual - Own Deployments",
        "resource": "deployments",
        "action": "read:own",
        "environment": None,
        "scope": "user",
        "icon": "👁️"
    },
    {
        "slug": "user:deployments:update:own",
        "name": "Update Own Deployments",
        "description": "Modify your own deployment configurations",
        "category": "Individual - Own Deployments",
        "resource": "deployments",
        "action": "update:own",
        "environment": None,
        "scope": "user",
        "icon": "✏️"
    },
    {
        "slug": "user:deployments:delete:own",
        "name": "Delete Own Deployments",
        "description": "Remove your own deployments from the system",
        "category": "Individual - Own Deployments",
        "resource": "deployments",
        "action": "delete:own",
        "environment": None,
        "scope": "user",
        "icon": "🗑️"
    },
    
    # Own Permissions
    {
        "slug": "user:permissions:read",
        "name": "View Own Permissions",
        "description": "View your own permissions and access rights",
        "category": "Individual - Permissions",
        "resource": "permissions",
        "action": "read",
        "environment": None,
        "scope": "user",
        "icon": "🔑"
    },
    
    # Own Notifications
    {
        "slug": "user:notifications:read",
        "name": "View Own Notifications",
        "description": "View your own notifications",
        "category": "Individual - Notifications",
        "resource": "notifications",
        "action": "read",
        "environment": None,
        "scope": "user",
        "icon": "🔔"
    },
    {
        "slug": "user:notifications:update",
        "name": "Update Own Notifications",
        "description": "Mark your own notifications as read",
        "category": "Individual - Notifications",
        "resource": "notifications",
        "action": "update",
        "environment": None,
        "scope": "user",
        "icon": "✏️"
    },
    {
        "slug": "user:notifications:delete",
        "name": "Delete Own Notifications",
        "description": "Delete your own notifications",
        "category": "Individual - Notifications",
        "resource": "notifications",
        "action": "delete",
        "environment": None,
        "scope": "user",
        "icon": "🗑️"
    },
    
    # Active Business Unit
    {
        "slug": "user:business_unit:active:read",
        "name": "View Active Business Unit",
        "description": "View your currently active business unit",
        "category": "Individual - Business Unit",
        "resource": "business_unit",
        "action": "active:read",
        "environment": None,
        "scope": "user",
        "icon": "👁️"
    },
    {
        "slug": "user:business_unit:active:update",
        "name": "Change Active Business Unit",
        "description": "Change your active business unit",
        "category": "Individual - Business Unit",
        "resource": "business_unit",
        "action": "active:update",
        "environment": None,
        "scope": "user",
        "icon": "🔄"
    },
]

# Create lookup dictionaries for easy access
PERMISSIONS_BY_SLUG: Dict[str, PermissionDefinition] = {
    perm["slug"]: perm for perm in PERMISSIONS
}

PERMISSIONS_BY_CATEGORY: Dict[str, List[PermissionDefinition]] = {}
for perm in PERMISSIONS:
    category = perm["category"]
    if category not in PERMISSIONS_BY_CATEGORY:
        PERMISSIONS_BY_CATEGORY[category] = []
    PERMISSIONS_BY_CATEGORY[category].append(perm)

def get_permission(slug: str) -> Optional[PermissionDefinition]:
    """Get permission metadata by slug"""
    return PERMISSIONS_BY_SLUG.get(slug)

def get_permissions_by_category(category: str) -> List[PermissionDefinition]:
    """Get all permissions in a category"""
    return PERMISSIONS_BY_CATEGORY.get(category, [])

def get_all_permissions() -> List[PermissionDefinition]:
    """Get all permissions"""
    return PERMISSIONS

def parse_permission_slug(slug: str) -> tuple[str, str]:
    """
    Parse permission slug into (obj, act) for Casbin storage.
    
    New format: scope:resource:action or scope:resource:action:environment
    Examples:
        "platform:users:list" -> ("users", "list")
        "business_unit:deployments:create:development" -> ("deployments", "create:development")
        "user:profile:read" -> ("profile", "read")
        "business_unit:deployments:history:read" -> ("deployments", "history:read")
    """
    import re
    
    # Strip BU-scoped prefix if present (format: "bu:{uuid}:scope:resource:action")
    bu_prefix_pattern = r'^bu:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:'
    slug = re.sub(bu_prefix_pattern, '', slug, flags=re.IGNORECASE)
    
    parts = slug.split(":")
    
    # New format: scope:resource:action or scope:resource:action:environment
    if len(parts) >= 3 and parts[0] in ["platform", "business_unit", "user"]:
        scope = parts[0]
        resource = parts[1]
        
        if len(parts) == 3:
            # Format: scope:resource:action
            return resource, parts[2]
        elif len(parts) == 4:
            # Format: scope:resource:action:environment or scope:resource:action:qualifier
            return resource, f"{parts[2]}:{parts[3]}"
        elif len(parts) == 5:
            # Format: scope:resource:action:subaction:environment (e.g., platform:plugins:access:manage)
            return resource, f"{parts[2]}:{parts[3]}:{parts[4]}"
        else:
            raise ValueError(f"Invalid permission slug format: {slug}")
    
    # Old format support (for backward compatibility during transition)
    if len(parts) == 2:
        # General permission: resource:action
        return parts[0], parts[1]
    elif len(parts) == 3:
        # Could be environment permission (resource:action:environment) 
        # or special action (resource:action:qualifier like "list:own")
        return parts[0], f"{parts[1]}:{parts[2]}"
    else:
        raise ValueError(f"Invalid permission slug format: {slug}")

def get_permission_scope(permission_slug: str) -> str:
    """
    Get the scope of a permission (platform, business_unit, or user).
    
    Args:
        permission_slug: Permission slug (e.g., "platform:users:list", "business_unit:deployments:create:development")
        
    Returns:
        Scope string: "platform", "business_unit", or "user"
        Defaults to "business_unit" if scope not found
    """
    # Check if it's in the registry first
    perm_def = PERMISSIONS_BY_SLUG.get(permission_slug)
    if perm_def and "scope" in perm_def:
        return perm_def["scope"]
    
    # Extract scope from slug prefix
    parts = permission_slug.split(":")
    if len(parts) >= 1 and parts[0] in ["platform", "business_unit", "user"]:
        return parts[0]
    
    # Default to business_unit for backward compatibility
    return "business_unit"

def is_platform_permission(permission_slug: str) -> bool:
    """Check if a permission is platform-level (no BU required)"""
    return get_permission_scope(permission_slug) == "platform"

def is_bu_permission(permission_slug: str) -> bool:
    """Check if a permission is business unit-scoped (BU required)"""
    return get_permission_scope(permission_slug) == "business_unit"

def is_user_permission(permission_slug: str) -> bool:
    """Check if a permission is user-specific (no BU required)"""
    return get_permission_scope(permission_slug) == "user"

def get_platform_permissions() -> List[str]:
    """Get all platform-level permission slugs"""
    return [perm["slug"] for perm in PERMISSIONS if perm.get("scope") == "platform"]

def get_bu_permissions() -> List[str]:
    """Get all business unit-scoped permission slugs"""
    return [perm["slug"] for perm in PERMISSIONS if perm.get("scope") == "business_unit"]

def get_user_permissions() -> List[str]:
    """Get all user-specific permission slugs"""
    return [perm["slug"] for perm in PERMISSIONS if perm.get("scope") == "user"]
