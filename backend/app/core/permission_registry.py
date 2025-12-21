"""
Permission Registry - Centralized definition of all permissions with metadata.

New Permission Format:
- General: resource:action (e.g., users:list, roles:read)
- Environment-specific: resource:action:environment (e.g., deployments:create:development)

Casbin Storage:
- General: obj="resource", act="action"
- Environment: obj="resource", act="action:environment"
"""

from typing import Dict, List, Optional

# Permission metadata structure
PermissionDefinition = Dict[str, str]

# All permissions with metadata
PERMISSIONS: List[PermissionDefinition] = [
    # ============================================================================
    # User Specific Permissions
    # ============================================================================
    {
        "slug": "profile:read",
        "name": "View Profile",
        "description": "View your own profile information",
        "category": "User Specific",
        "resource": "profile",
        "action": "read",
        "environment": None,
        "icon": "👤"
    },
    {
        "slug": "profile:update",
        "name": "Update Profile",
        "description": "Update your own profile information",
        "category": "User Specific",
        "resource": "profile",
        "action": "update",
        "environment": None,
        "icon": "✏️"
    },
    
    # ============================================================================
    # User Management Permissions
    # ============================================================================
    {
        "slug": "users:list",
        "name": "List Users",
        "description": "View the list of all users in the organization",
        "category": "User Management",
        "resource": "users",
        "action": "list",
        "environment": None,
        "icon": "👥"
    },
    {
        "slug": "users:create",
        "name": "Create Users",
        "description": "Create new user accounts",
        "category": "User Management",
        "resource": "users",
        "action": "create",
        "environment": None,
        "icon": "➕"
    },
    {
        "slug": "users:read",
        "name": "View User Details",
        "description": "View detailed information about users",
        "category": "User Management",
        "resource": "users",
        "action": "read",
        "environment": None,
        "icon": "👁️"
    },
    {
        "slug": "users:update",
        "name": "Update Users",
        "description": "Modify user information and settings",
        "category": "User Management",
        "resource": "users",
        "action": "update",
        "environment": None,
        "icon": "✏️"
    },
    {
        "slug": "users:delete",
        "name": "Delete Users",
        "description": "Remove user accounts from the system",
        "category": "User Management",
        "resource": "users",
        "action": "delete",
        "environment": None,
        "icon": "🗑️"
    },
    
    # ============================================================================
    # Role Management Permissions
    # ============================================================================
    {
        "slug": "roles:list",
        "name": "List Roles",
        "description": "View the list of all roles",
        "category": "Role Management",
        "resource": "roles",
        "action": "list",
        "environment": None,
        "icon": "📋"
    },
    {
        "slug": "roles:read",
        "name": "View Role Details",
        "description": "View detailed information about roles and their permissions",
        "category": "Role Management",
        "resource": "roles",
        "action": "read",
        "environment": None,
        "icon": "👁️"
    },
    {
        "slug": "roles:create",
        "name": "Create Roles",
        "description": "Create new roles with custom permissions",
        "category": "Role Management",
        "resource": "roles",
        "action": "create",
        "environment": None,
        "icon": "➕"
    },
    {
        "slug": "roles:update",
        "name": "Update Roles",
        "description": "Modify role permissions and settings",
        "category": "Role Management",
        "resource": "roles",
        "action": "update",
        "environment": None,
        "icon": "✏️"
    },
    {
        "slug": "roles:delete",
        "name": "Delete Roles",
        "description": "Remove roles from the system",
        "category": "Role Management",
        "resource": "roles",
        "action": "delete",
        "environment": None,
        "icon": "🗑️"
    },
    
    # ============================================================================
    # Permission Management
    # ============================================================================
    {
        "slug": "permissions:list",
        "name": "List Permissions",
        "description": "View all available permissions in the system",
        "category": "Permission Management",
        "resource": "permissions",
        "action": "list",
        "environment": None,
        "icon": "🔑"
    },
    
    # ============================================================================
    # Deployment Permissions (General)
    # ============================================================================
    {
        "slug": "deployments:list",
        "name": "List All Deployments",
        "description": "View all deployments across all environments (organization-wide)",
        "category": "Deployment Management",
        "resource": "deployments",
        "action": "list",
        "environment": None,
        "icon": "📦"
    },
    {
        "slug": "deployments:list:own",
        "name": "List Own Deployments",
        "description": "View only your own deployments across all environments",
        "category": "User Specific",
        "resource": "deployments",
        "action": "list:own",
        "environment": None,
        "icon": "👤"
    },
    {
        "slug": "deployments:update:own",
        "name": "Update Own Deployments",
        "description": "Modify your own deployment configurations",
        "category": "User Specific",
        "resource": "deployments",
        "action": "update:own",
        "environment": None,
        "icon": "✏️"
    },
    {
        "slug": "deployments:delete:own",
        "name": "Delete Own Deployments",
        "description": "Remove your own deployments from the system",
        "category": "User Specific",
        "resource": "deployments",
        "action": "delete:own",
        "environment": None,
        "icon": "🗑️"
    },
    {
        "slug": "deployments:read",
        "name": "View Deployment Details",
        "description": "View detailed information about deployments",
        "category": "Deployment Management",
        "resource": "deployments",
        "action": "read",
        "environment": None,
        "icon": "👁️"
    },
    {
        "slug": "deployments:update",
        "name": "Update Deployments",
        "description": "Modify deployment configurations",
        "category": "Deployment Management",
        "resource": "deployments",
        "action": "update",
        "environment": None,
        "icon": "✏️"
    },
    {
        "slug": "deployments:delete",
        "name": "Delete Deployments",
        "description": "Remove deployments from the system",
        "category": "Deployment Management",
        "resource": "deployments",
        "action": "delete",
        "environment": None,
        "icon": "🗑️"
    },
    
    # ============================================================================
    # Deployment Permissions - Development Environment
    # ============================================================================
    {
        "slug": "deployments:create:development",
        "name": "Deploy to Development",
        "description": "Create and deploy resources to the development environment",
        "category": "Deployment - Development",
        "resource": "deployments",
        "action": "create",
        "environment": "development",
        "icon": "🔧"
    },
    {
        "slug": "deployments:update:development",
        "name": "Update Development Deployments",
        "description": "Modify deployments in the development environment",
        "category": "Deployment - Development",
        "resource": "deployments",
        "action": "update",
        "environment": "development",
        "icon": "🔧"
    },
    {
        "slug": "deployments:delete:development",
        "name": "Delete Development Deployments",
        "description": "Remove deployments from the development environment",
        "category": "Deployment - Development",
        "resource": "deployments",
        "action": "delete",
        "environment": "development",
        "icon": "🔧"
    },
    
    # ============================================================================
    # Deployment Permissions - Staging Environment
    # ============================================================================
    {
        "slug": "deployments:create:staging",
        "name": "Deploy to Staging",
        "description": "Create and deploy resources to the staging environment",
        "category": "Deployment - Staging",
        "resource": "deployments",
        "action": "create",
        "environment": "staging",
        "icon": "🧪"
    },
    {
        "slug": "deployments:update:staging",
        "name": "Update Staging Deployments",
        "description": "Modify deployments in the staging environment",
        "category": "Deployment - Staging",
        "resource": "deployments",
        "action": "update",
        "environment": "staging",
        "icon": "🧪"
    },
    {
        "slug": "deployments:delete:staging",
        "name": "Delete Staging Deployments",
        "description": "Remove deployments from the staging environment",
        "category": "Deployment - Staging",
        "resource": "deployments",
        "action": "delete",
        "environment": "staging",
        "icon": "🧪"
    },
    
    # ============================================================================
    # Deployment Permissions - Production Environment
    # ============================================================================
    {
        "slug": "deployments:create:production",
        "name": "Deploy to Production",
        "description": "Create and deploy resources to the production environment (requires approval)",
        "category": "Deployment - Production",
        "resource": "deployments",
        "action": "create",
        "environment": "production",
        "icon": "🚀"
    },
    {
        "slug": "deployments:update:production",
        "name": "Update Production Deployments",
        "description": "Modify deployments in the production environment (requires approval)",
        "category": "Deployment - Production",
        "resource": "deployments",
        "action": "update",
        "environment": "production",
        "icon": "🚀"
    },
    {
        "slug": "deployments:delete:production",
        "name": "Delete Production Deployments",
        "description": "Remove deployments from the production environment (requires approval)",
        "category": "Deployment - Production",
        "resource": "deployments",
        "action": "delete",
        "environment": "production",
        "icon": "🚀"
    },
    
    # ============================================================================
    # Plugin Management Permissions
    # ============================================================================
    {
        "slug": "plugins:upload",
        "name": "Upload Plugins",
        "description": "Upload new plugins to the system",
        "category": "Plugin Management",
        "resource": "plugins",
        "action": "upload",
        "environment": None,
        "icon": "📤"
    },
    {
        "slug": "plugins:delete",
        "name": "Delete Plugins",
        "description": "Remove plugins from the system",
        "category": "Plugin Management",
        "resource": "plugins",
        "action": "delete",
        "environment": None,
        "icon": "🗑️"
    },
    {
        "slug": "plugins:provision",
        "name": "Provision Resources",
        "description": "Use plugins to provision infrastructure and resources",
        "category": "Plugin Management",
        "resource": "plugins",
        "action": "provision",
        "environment": None,
        "icon": "⚙️"
    },
    
    # ============================================================================
    # Group Management Permissions
    # ============================================================================
    {
        "slug": "groups:list",
        "name": "List Groups",
        "description": "View all groups in the organization",
        "category": "Group Management",
        "resource": "groups",
        "action": "list",
        "environment": None,
        "icon": "👥"
    },
    {
        "slug": "groups:create",
        "name": "Create Groups",
        "description": "Create new groups",
        "category": "Group Management",
        "resource": "groups",
        "action": "create",
        "environment": None,
        "icon": "➕"
    },
    {
        "slug": "groups:read",
        "name": "View Group Details",
        "description": "View detailed information about groups",
        "category": "Group Management",
        "resource": "groups",
        "action": "read",
        "environment": None,
        "icon": "👁️"
    },
    {
        "slug": "groups:update",
        "name": "Update Groups",
        "description": "Modify group settings and configurations",
        "category": "Group Management",
        "resource": "groups",
        "action": "update",
        "environment": None,
        "icon": "✏️"
    },
    {
        "slug": "groups:delete",
        "name": "Delete Groups",
        "description": "Remove groups from the system",
        "category": "Group Management",
        "resource": "groups",
        "action": "delete",
        "environment": None,
        "icon": "🗑️"
    },
    {
        "slug": "groups:manage",
        "name": "Manage Group Members",
        "description": "Add or remove users from groups",
        "category": "Group Management",
        "resource": "groups",
        "action": "manage",
        "environment": None,
        "icon": "👤"
    },
    
    # ============================================================================
    # Audit Permissions
    # ============================================================================
    {
        "slug": "audit:read",
        "name": "View Audit Logs",
        "description": "View system audit logs and activity history",
        "category": "Audit",
        "resource": "audit",
        "action": "read",
        "environment": None,
        "icon": "📊"
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
    
    Examples:
        "users:list" -> ("users", "list")
        "deployments:create:development" -> ("deployments", "create:development")
        "deployments:list:own" -> ("deployments", "list:own")
    """
    parts = slug.split(":")
    if len(parts) == 2:
        # General permission: resource:action
        return parts[0], parts[1]
    elif len(parts) == 3:
        # Could be environment permission (resource:action:environment) 
        # or special action (resource:action:qualifier like "list:own")
        # Both are stored as obj="resource", act="action:third_part"
        return parts[0], f"{parts[1]}:{parts[2]}"
    else:
        raise ValueError(f"Invalid permission slug format: {slug}")

