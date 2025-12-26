"""
Casbin Policy Migration for Business Unit-Scoped RBAC

This module migrates existing Casbin policies to support BU-scoped permissions.
It creates BU-scoped role assignments and permission policies.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import uuid
from casbin import Enforcer

from app.models.business_unit import BusinessUnit, BusinessUnitMember
from app.models.rbac import Role
from app.core.organization import get_organization_domain
from app.core.permission_registry import get_bu_permissions, parse_permission_slug
from app.logger import logger


async def create_default_bu_role_permissions(
    role_name: str,
    business_unit_id: uuid.UUID,
    org_domain: str,
    enforcer: Enforcer
):
    """
    Assign appropriate permissions to a default role in a business unit context.
    
    Args:
        role_name: Name of the role (e.g., "bu-owner", "developer", "viewer")
        business_unit_id: UUID of the business unit
        org_domain: Organization domain
        enforcer: Casbin enforcer
    """
    # Get BU-scoped permissions (list of permission slugs)
    bu_permission_slugs = get_bu_permissions()
    
    # Get full permission definitions for wildcard expansion
    from app.core.permission_registry import PERMISSIONS_BY_SLUG
    bu_permissions = [PERMISSIONS_BY_SLUG[slug] for slug in bu_permission_slugs if slug in PERMISSIONS_BY_SLUG]
    
    # Role templates using new scope-prefixed permission format
    # These templates define permission patterns for common roles
    ROLE_TEMPLATES = {
        "bu-owner": {
            "permission_patterns": [
                "business_unit:*",  # All business unit permissions
            ],
            "description": "Full access to all business unit resources"
        },
        "bu-admin": {
            "permission_patterns": [
                "business_unit:deployments:create:development",
                "business_unit:deployments:create:staging",
                "business_unit:deployments:update:development",
                "business_unit:deployments:update:staging",
                "business_unit:deployments:delete:development",
                "business_unit:deployments:delete:staging",
                "business_unit:deployments:read",
                "business_unit:deployments:list",
                "business_unit:business_units:read",
                "business_unit:business_units:update",
                "business_unit:business_units:manage_members",
            ],
            "description": "Manage deployments and BU resources"
        },
        "developer": {
            "permission_patterns": [
                "business_unit:deployments:create:development",
                "business_unit:deployments:update:development",
                "business_unit:deployments:delete:development",
                "business_unit:deployments:read",
                "business_unit:deployments:list",
                "business_unit:plugins:provision",
            ],
            "description": "Deploy and manage in development environment"
        },
        "engineer": {
            "permission_patterns": [
                "business_unit:deployments:create:development",
                "business_unit:deployments:update:development",
                "business_unit:deployments:delete:development",
                "business_unit:deployments:read",
                "business_unit:deployments:list",
                "business_unit:plugins:provision",
            ],
            "description": "Deploy and manage in development environment"
        },
        "senior-engineer": {
            "permission_patterns": [
                "business_unit:deployments:create:development",
                "business_unit:deployments:update:development",
                "business_unit:deployments:delete:development",
                "business_unit:deployments:create:staging",
                "business_unit:deployments:update:staging",
                "business_unit:deployments:delete:staging",
                "business_unit:deployments:read",
                "business_unit:deployments:list",
                "business_unit:plugins:provision",
            ],
            "description": "Deploy in development and staging environments"
        },
        "viewer": {
            "permission_patterns": [
                "business_unit:deployments:read",
                "business_unit:deployments:list",
                "business_unit:business_units:read",
            ],
            "description": "Read-only access to business unit resources"
        },
    }
    
    # Get permissions for role from template
    role_permissions = {}
    for role_name, template in ROLE_TEMPLATES.items():
        permission_slugs = []
        for pattern in template["permission_patterns"]:
            if pattern.endswith(":*"):
                # Expand wildcard - get all permissions starting with the prefix
                prefix = pattern[:-2]  # Remove ":*"
                matching_perms = [p["slug"] for p in bu_permissions if p["slug"].startswith(prefix + ":")]
                permission_slugs.extend(matching_perms)
            else:
                permission_slugs.append(pattern)
        role_permissions[role_name] = permission_slugs
    
    # Normalize role name (lowercase, strip spaces, handle variations)
    role_name_normalized = role_name.lower().strip()
    # Handle common variations
    role_name_variations = {
        "infrastructure engineer": "engineer",
        "infrastructure engineers": "engineer",
        "infrastructure-engineer": "engineer",
        "infrastructure_engineer": "engineer",
        "senior infrastructure engineer": "senior-engineer",
        "senior infrastructure engineers": "senior-engineer",
    }
    normalized_name = role_name_variations.get(role_name_normalized, role_name_normalized)
    
    # Get permissions for this role
    permission_slugs = role_permissions.get(normalized_name, [])
    
    # If role not found in default mapping, try to get permissions from Casbin (global scope)
    if not permission_slugs:
        # Try case-insensitive matching first
        for default_role, perms in role_permissions.items():
            if default_role.lower() == normalized_name:
                permission_slugs = perms
                logger.info(f"Matched role '{role_name}' (normalized: '{normalized_name}') to default role '{default_role}'")
                break
        
        # If still not found, try to get permissions from Casbin for this role
        if not permission_slugs:
            try:
                # Get all policies for this role in the org domain (global scope)
                all_policies = enforcer.get_filtered_policy(0, role_name, org_domain)
                # Extract unique (obj, act) pairs
                global_permissions = set()
                bu_perm_slugs = set(get_bu_permissions())  # Get list of BU-scoped permission slugs
                
                for policy in all_policies:
                    if len(policy) >= 4:
                        # Format: [role, domain, obj, act, ...]
                        policy_obj = policy[2]
                        policy_act = policy[3]
                        # Check if this permission is BU-scoped
                        perm_slug = f"{policy_obj}:{policy_act}"
                        if perm_slug in bu_perm_slugs:
                            global_permissions.add(perm_slug)
                
                if global_permissions:
                    permission_slugs = list(global_permissions)
                    logger.info(f"Found {len(permission_slugs)} BU-scoped permissions for role '{role_name}' from Casbin: {permission_slugs}")
                else:
                    logger.warning(f"No BU-scoped permissions found for role '{role_name}' in Casbin. Using default 'developer' permissions as fallback.")
                    # Fallback to developer permissions if nothing found
                    permission_slugs = role_permissions.get("developer", [])
            except Exception as e:
                logger.warning(f"Failed to get permissions from Casbin for role '{role_name}': {e}. Using default 'developer' permissions.")
                permission_slugs = role_permissions.get("developer", [])
    
    # Permissions are already expanded from templates, but handle any remaining wildcards
    expanded_permissions = []
    for perm_slug in permission_slugs:
        if perm_slug.endswith(":*"):
            # Expand wildcard - get all permissions starting with the prefix
            prefix = perm_slug[:-2]  # Remove ":*"
            matching_perms = [p["slug"] for p in bu_permissions if p["slug"].startswith(prefix + ":")]
            expanded_permissions.extend(matching_perms)
        else:
            expanded_permissions.append(perm_slug)
    
    # Add permissions to Casbin with BU context
    for perm_slug in expanded_permissions:
        try:
            obj, act = parse_permission_slug(perm_slug)
            # Format: (role, org_domain, bu:{bu_id}:resource, action)
            bu_obj = f"bu:{business_unit_id}:{obj}"
            
            # Check if policy already exists
            existing = enforcer.get_filtered_policy(0, role_name, org_domain, bu_obj, act)
            if not existing:
                enforcer.add_policy(role_name, org_domain, bu_obj, act)
                logger.info(f"Added BU permission: {role_name} -> {bu_obj}:{act} for permission {perm_slug}")
        except Exception as e:
            logger.warning(f"Failed to add permission {perm_slug} for role {role_name} in BU {business_unit_id}: {e}")


async def migrate_to_bu_scoped_policies(
    db: AsyncSession,
    enforcer: Enforcer
):
    """
    Migrate existing Casbin policies to support BU-scoped permissions.
    
    For each business unit:
    1. Get all members
    2. Add BU-scoped role assignment: (user_id, role_name, org_domain, bu_id)
    3. Create BU-scoped permission policies: (role, org_domain, bu:{bu_id}:resource, action)
    
    Note: This function assumes default roles have already been created and
    business_unit_members have been migrated to use role_id.
    """
    logger.info("Starting Casbin policy migration to BU-scoped format...")
    
    # Get all business units
    result = await db.execute(select(BusinessUnit))
    business_units = result.scalars().all()
    
    if not business_units:
        logger.info("No business units found, skipping policy migration")
        return
    
    logger.info(f"Found {len(business_units)} business units to migrate")
    
    total_members = 0
    total_policies = 0
    
    for bu in business_units:
        # Get organization domain
        org_domain = get_organization_domain(bu.organization)
        
        # Get all members of this BU
        members_result = await db.execute(
            select(BusinessUnitMember)
            .options(selectinload(BusinessUnitMember.role))
            .where(BusinessUnitMember.business_unit_id == bu.id)
        )
        members = members_result.scalars().all()
        
        if not members:
            logger.debug(f"No members in business unit {bu.name}, skipping")
            continue
        
        logger.info(f"Processing business unit {bu.name} ({bu.id}) with {len(members)} members")
        
        for member in members:
            if not member.role:
                logger.warning(f"Member {member.user_id} in BU {bu.id} has no role, skipping")
                continue
            
            role = member.role
            user_id = str(member.user_id)
            bu_id_str = str(bu.id)
            
            # Add BU-scoped role assignment: (user_id, role_name, org_domain, bu_id)
            # Note: Casbin grouping policies are (user, role, domain), so we'll store
            # BU context in the role name or use a different approach
            # For now, we'll use a composite role name: role_name@bu_id
            # OR we can extend the grouping policy format to include BU ID
            # Since Casbin model uses 3-param grouping, we'll use composite role names
            
            # Option 1: Use composite role name (simpler, works with current model)
            composite_role = f"{role.name}@bu:{bu_id_str}"
            
            # Check if grouping policy already exists
            existing = enforcer.get_filtered_grouping_policy(0, user_id)
            has_bu_role = any(
                len(p) >= 3 and p[1] == composite_role and p[2] == org_domain
                for p in existing
            )
            
            if not has_bu_role:
                enforcer.add_grouping_policy(user_id, composite_role, org_domain)
                total_members += 1
                logger.debug(f"Added BU role assignment: {user_id} -> {composite_role} in {org_domain}")
            
            # Create BU-scoped permission policies for this role
            # Only create once per role per BU (not per member)
            # Check if we've already created policies for this role in this BU
            bu_obj_sample = f"bu:{bu_id_str}:deployments"
            existing_policies = enforcer.get_filtered_policy(0, role.name, org_domain, bu_obj_sample)
            
            if not existing_policies:
                # Create permissions for this role in this BU
                await create_default_bu_role_permissions(role.name, bu.id, org_domain, enforcer)
                total_policies += 1
    
    # Save all policy changes
    enforcer.save_policy()
    
    logger.info(f"✅ Casbin policy migration completed:")
    logger.info(f"  - Processed {len(business_units)} business units")
    logger.info(f"  - Added {total_members} BU role assignments")
    logger.info(f"  - Created {total_policies} BU permission policy sets")

