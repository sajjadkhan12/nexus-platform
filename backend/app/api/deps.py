from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.rbac import User, Organization
from app.config import settings
from app.core.organization import get_user_organization, get_organization_domain

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Async query - eagerly load organization
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

from app.core.casbin import get_enforcer
from casbin import Enforcer

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Check if user has 'admin' role using Casbin with organization domain
    user_id = str(current_user.id)
    
    # Get organization domain
    organization = await get_user_organization(current_user, db)
    org_domain = get_organization_domain(organization)
    
    # Check if user has admin role in their organization
    # g, user_id, role, domain
    has_role = enforcer.has_grouping_policy(user_id, "admin", org_domain)
    
    if not has_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def is_allowed(permission_slug: str):
    """Dependency for checking permissions using Casbin with organization context"""
    async def dependency(
        current_user: User = Depends(get_current_user),
        enforcer: Enforcer = Depends(get_enforcer),
        db: AsyncSession = Depends(get_db)
    ):
        # Split slug into object and action
        # e.g. "users:list" -> obj="users", act="list"
        parts = permission_slug.split(":")
        if len(parts) < 2:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid permission slug: {permission_slug}"
            )
            
        obj = parts[0]
        act = ":".join(parts[1:])
        
        user_id = str(current_user.id)
        
        # Get organization domain
        organization = await get_user_organization(current_user, db)
        org_domain = get_organization_domain(organization)
        
        # Check permission: sub, dom, obj, act
        if not enforcer.enforce(user_id, org_domain, obj, act):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_slug} required"
            )
        return current_user
    return dependency


async def get_org_domain(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Dependency to get organization domain for current user.
    Use this in endpoints that need organization context for Casbin enforcement.
    """
    organization = await get_user_organization(current_user, db)
    return get_organization_domain(organization)


class OrgAwareEnforcer:
    """
    Wrapper that automatically injects organization domain into enforcement checks.
    Use this as a dependency in endpoints to get automatic multi-tenant enforcement.
    """
    def __init__(self, enforcer, org_domain: str):
        self._enforcer = enforcer
        self._org_domain = org_domain
    
    def enforce(self, user_id: str, resource: str, action: str) -> bool:
        """3-param enforce that automatically adds org_domain"""
        return self._enforcer.enforce(user_id, self._org_domain, resource, action)
    
    def has_grouping_policy(self, user_id: str, role: str) -> bool:
        """2-param has_grouping_policy that automatically adds org_domain"""
        return self._enforcer.has_grouping_policy(user_id, role, self._org_domain)
    
    def add_grouping_policy(self, user_id: str, role: str) -> bool:
        """2-param add_grouping_policy that automatically adds org_domain"""
        return self._enforcer.add_grouping_policy(user_id, role, self._org_domain)
    
    def add_policy(self, subject: str, resource: str, action: str) -> bool:
        """3-param add_policy that automatically adds org_domain"""
        return self._enforcer.add_policy(subject, self._org_domain, resource, action)
    
    def remove_policy(self, subject: str, resource: str, action: str) -> bool:
        """3-param remove_policy that automatically adds org_domain"""
        return self._enforcer.remove_policy(subject, self._org_domain, resource, action)
    
    def remove_grouping_policy(self, user_id: str, role: str) -> bool:
        """2-param remove_grouping_policy that automatically adds org_domain"""
        return self._enforcer.remove_grouping_policy(user_id, role, self._org_domain)
    
    def get_roles_for_user(self, user_id: str) -> list:
        """Get roles for user within the organization domain"""
        # Casbin's get_roles_for_user returns [role, domain] pairs in multi-tenant mode
        # We need to filter by domain and return only roles
        all_roles = self._enforcer.get_roles_for_user(user_id, self._org_domain)
        return all_roles
    
    def get_users_for_role(self, role: str) -> list:
        """Get users for role within the organization domain"""
        return self._enforcer.get_users_for_role(role, self._org_domain)
    
    def get_all_roles(self) -> list:
        """Get all roles within the organization domain"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        
        # Get all grouping policies and extract unique roles for this org
        all_grouping = base_enforcer.get_grouping_policy()
        roles = set()
        for policy in all_grouping:
            # Format: [user/group, role, domain]
            if len(policy) >= 3 and policy[2] == self._org_domain:
                roles.add(policy[1])  # role is at index 1
        return list(roles)
    
    def get_permissions_for_user(self, user_id: str) -> list:
        """Get permissions for user within the organization domain"""
        return self._enforcer.get_permissions_for_user(user_id, self._org_domain)
    
    def get_implicit_permissions_for_user(self, user_id: str) -> list:
        """Get all permissions (direct and inherited) for user within the organization domain"""
        return self._enforcer.get_implicit_permissions_for_user(user_id, self._org_domain)
    
    def delete_roles_for_user(self, user_id: str) -> bool:
        """Delete all roles for user within the organization domain"""
        return self._enforcer.delete_roles_for_user(user_id, self._org_domain)
    
    def delete_role(self, role: str) -> bool:
        """Delete a role within the organization domain"""
        return self._enforcer.delete_role(role, self._org_domain)
    
    def delete_user(self, user_id: str) -> bool:
        """Delete all policies and grouping policies for a user within the organization domain"""
        result = False
        
        try:
            # Access the base enforcer (unwrap if necessary)
            base_enforcer = self._enforcer
            if hasattr(self._enforcer, 'enforcer'):
                base_enforcer = self._enforcer.enforcer
            
            # Delete all role assignments (grouping policies) for the user in this organization
            # Get all grouping policies for this user
            grouping_policies = base_enforcer.get_filtered_grouping_policy(0, user_id)
            for policy in grouping_policies:
                # Only delete if it's in this organization domain
                if len(policy) >= 3 and policy[2] == self._org_domain:
                    base_enforcer.remove_grouping_policy(*policy)
                    result = True
            
            # Delete all direct permissions (policies) for the user in this organization
            policies = base_enforcer.get_filtered_policy(0, user_id, self._org_domain)
            for policy in policies:
                base_enforcer.remove_policy(*policy)
                result = True
            
            # Save the policy changes
            if result:
                base_enforcer.save_policy()
        except Exception as e:
            # Log the error but don't fail the deletion
            import logging
            logging.warning(f"Failed to clean up Casbin policies for user {user_id}: {e}")
            # Continue with user deletion even if Casbin cleanup fails
        
        return True  # Always return True to allow user deletion to proceed
    
    def delete_permission(self, *params) -> bool:
        """Delete a permission within the organization domain"""
        # Auto-inject org_domain if needed
        if len(params) == 2:  # resource, action
            return self._enforcer.delete_permission(self._org_domain, params[0], params[1])
        else:
            return self._enforcer.delete_permission(*params)
    
    def get_policy(self) -> list:
        """Get all policies"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        return base_enforcer.get_policy()
    
    def get_filtered_policy(self, field_index: int, *field_values) -> list:
        """Get filtered policies"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        return base_enforcer.get_filtered_policy(field_index, *field_values)
    
    def get_grouping_policy(self) -> list:
        """Get all grouping policies"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        return base_enforcer.get_grouping_policy()
    
    def get_filtered_grouping_policy(self, field_index: int, *field_values) -> list:
        """Get filtered grouping policies"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        return base_enforcer.get_filtered_grouping_policy(field_index, *field_values)
    
    def remove_filtered_policy(self, field_index: int, *field_values) -> bool:
        """Remove filtered policies"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        return base_enforcer.remove_filtered_policy(field_index, *field_values)
    
    def remove_filtered_grouping_policy(self, field_index: int, *field_values) -> bool:
        """Remove filtered grouping policies"""
        # Access the base enforcer (unwrap if necessary)
        base_enforcer = self._enforcer
        if hasattr(self._enforcer, 'enforcer'):
            base_enforcer = self._enforcer.enforcer
        return base_enforcer.remove_filtered_grouping_policy(field_index, *field_values)
    
    def load_policy(self):
        """Delegate to underlying enforcer"""
        return self._enforcer.load_policy()
    
    def save_policy(self):
        """Delegate to underlying enforcer"""
        return self._enforcer.save_policy()


async def get_org_aware_enforcer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OrgAwareEnforcer:
    """
    Get an organization-aware enforcer that automatically injects org_domain.
    
    This allows existing code to work without changes:
    - enforcer.enforce(user_id, "resource", "action") -> automatically adds org_domain
    - enforcer.has_grouping_policy(user_id, "role") -> automatically adds org_domain
    - etc.
    
    Use this dependency in new endpoints or replace Depends(get_enforcer) with this.
    """
    from app.core.casbin import get_enforcer
    base_enforcer = get_enforcer()
    org_domain = await get_org_domain(current_user, db)
    return OrgAwareEnforcer(base_enforcer, org_domain)
