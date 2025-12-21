"""
Wrapper for Casbin enforcer to provide backward compatibility during migration to multi-tenancy.
This wrapper automatically adds organization domain to enforcement checks.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rbac import User
from app.core.organization import get_user_organization, get_organization_domain
from casbin import Enforcer as CasbinEnforcer
import asyncio


class MultiTenantEnforcerWrapper:
    """
    Wrapper around Casbin enforcer that automatically handles organization domains.
    This provides backward compatibility while supporting multi-tenancy.
    """
    
    def __init__(self, enforcer: CasbinEnforcer):
        self.enforcer = enforcer
        self._org_domain: Optional[str] = None
    
    def set_org_domain(self, org_domain: str):
        """Set the organization domain for subsequent enforcement checks"""
        self._org_domain = org_domain
    
    def enforce(self, sub: str, *args) -> bool:
        """
        Enforce permission check with automatic organization domain injection.
        
        Backward compatible: Accepts both old format (sub, obj, act) 
        and new format (sub, dom, obj, act)
        """
        if len(args) == 2:
            # Old format: sub, obj, act
            # Need to inject organization domain
            obj, act = args
            if not self._org_domain:
                # Fallback: try to get from global context or use empty string
                # This should not happen in production as org_domain should be set
                import logging
                logging.warning(f"Organization domain not set for enforcement check: {sub}, {obj}, {act}")
                return False
            return self.enforcer.enforce(sub, self._org_domain, obj, act)
        elif len(args) == 3:
            # New format: sub, dom, obj, act
            return self.enforcer.enforce(sub, *args)
        else:
            raise ValueError(f"Invalid number of arguments for enforce: {len(args) + 1}")
    
    def has_grouping_policy(self, *args) -> bool:
        """
        Check grouping policy with automatic organization domain injection.
        
        Backward compatible: Accepts both old format (user, role)
        and new format (user, role, domain)
        """
        if len(args) == 2:
            # Old format: user, role
            user, role = args
            if not self._org_domain:
                import logging
                logging.warning(f"Organization domain not set for has_grouping_policy: {user}, {role}")
                return False
            return self.enforcer.has_grouping_policy(user, role, self._org_domain)
        elif len(args) == 3:
            # New format: user, role, domain
            return self.enforcer.has_grouping_policy(*args)
        else:
            raise ValueError(f"Invalid number of arguments for has_grouping_policy: {len(args)}")
    
    def add_grouping_policy(self, *args) -> bool:
        """
        Add grouping policy with automatic organization domain injection.
        
        Backward compatible: Accepts both old format (user, role)
        and new format (user, role, domain)
        """
        if len(args) == 2:
            # Old format: user, role
            user, role = args
            if not self._org_domain:
                import logging
                logging.warning(f"Organization domain not set for add_grouping_policy: {user}, {role}")
                return False
            return self.enforcer.add_grouping_policy(user, role, self._org_domain)
        elif len(args) == 3:
            # New format: user, role, domain
            return self.enforcer.add_grouping_policy(*args)
        else:
            raise ValueError(f"Invalid number of arguments for add_grouping_policy: {len(args)}")
    
    def add_policy(self, *args) -> bool:
        """
        Add policy with automatic organization domain injection.
        
        Backward compatible: Accepts both old format (sub, obj, act)
        and new format (sub, dom, obj, act)
        """
        if len(args) == 3:
            # Old format: sub, obj, act
            sub, obj, act = args
            if not self._org_domain:
                import logging
                logging.warning(f"Organization domain not set for add_policy: {sub}, {obj}, {act}")
                return False
            return self.enforcer.add_policy(sub, self._org_domain, obj, act)
        elif len(args) == 4:
            # New format: sub, dom, obj, act
            return self.enforcer.add_policy(*args)
        else:
            raise ValueError(f"Invalid number of arguments for add_policy: {len(args)}")
    
    def remove_policy(self, *args) -> bool:
        """Remove policy - delegates to underlying enforcer"""
        if len(args) == 3:
            # Old format: sub, obj, act
            sub, obj, act = args
            if not self._org_domain:
                return False
            return self.enforcer.remove_policy(sub, self._org_domain, obj, act)
        elif len(args) == 4:
            # New format: sub, dom, obj, act
            return self.enforcer.remove_policy(*args)
        else:
            raise ValueError(f"Invalid number of arguments for remove_policy: {len(args)}")
    
    def remove_grouping_policy(self, *args) -> bool:
        """Remove grouping policy - delegates to underlying enforcer"""
        if len(args) == 2:
            # Old format: user, role
            user, role = args
            if not self._org_domain:
                return False
            return self.enforcer.remove_grouping_policy(user, role, self._org_domain)
        elif len(args) == 3:
            # New format: user, role, domain
            return self.enforcer.remove_grouping_policy(*args)
        else:
            raise ValueError(f"Invalid number of arguments for remove_grouping_policy: {len(args)}")
    
    def load_policy(self):
        """Load policy - delegates to underlying enforcer"""
        return self.enforcer.load_policy()
    
    def save_policy(self):
        """Save policy - delegates to underlying enforcer"""
        return self.enforcer.save_policy()
    
    def get_roles_for_user(self, user: str, domain: Optional[str] = None):
        """
        Get roles for user within a specific domain.
        Includes both direct role assignments and roles through groups.
        In domain-based RBAC, we need to filter grouping policies by domain.
        """
        target_domain = domain or self._org_domain
        if not target_domain:
            return []
        
        # Use Casbin's implicit roles to get roles through groups
        # This handles: user -> group -> role hierarchy
        try:
            implicit_roles = self.enforcer.get_implicit_roles_for_user(user, target_domain)
            # Implicit roles returns roles in format that may include domain
            # Extract just the role names
            roles = []
            for role_info in implicit_roles:
                if isinstance(role_info, (list, tuple)) and len(role_info) > 0:
                    # If it's a tuple/list, take the first element (role name)
                    roles.append(role_info[0] if len(role_info) > 0 else role_info)
                else:
                    roles.append(role_info)
            return list(set(roles))  # Remove duplicates
        except Exception:
            # Fallback: manually check direct roles and groups
            all_policies = self.enforcer.get_filtered_grouping_policy(0, user)
            
            roles = []
            groups = []
            for policy in all_policies:
                if len(policy) >= 3 and str(policy[2]) == str(target_domain):
                    target = policy[1]  # Could be a role or a group
                    # Check if it's a role (has permissions assigned) or a group
                    # For now, we'll check if there are policies where this is the subject
                    # If there are policies with this as subject, it's likely a role
                    # If there are grouping policies with this as subject, it might be a group
                    role_policies = self.enforcer.get_filtered_policy(0, target, target_domain)
                    if role_policies:
                        # Has permissions, so it's a role
                        roles.append(target)
                    else:
                        # Check if it's a group (has roles assigned to it)
                        group_role_policies = self.enforcer.get_filtered_grouping_policy(0, target)
                        for grp_policy in group_role_policies:
                            if len(grp_policy) >= 3 and str(grp_policy[2]) == str(target_domain):
                                # This is a group with a role
                                roles.append(grp_policy[1])
                                groups.append(target)
            
            # Remove duplicates and return
            return list(set(roles))
    
    def get_users_for_role(self, role: str, domain: Optional[str] = None):
        """
        Get users for role within a specific domain.
        In domain-based RBAC, we need to filter grouping policies by domain.
        """
        target_domain = domain or self._org_domain
        if not target_domain:
            return []
        
        # Get all grouping policies for this role
        # In domain RBAC, grouping policies are [user, role, domain]
        all_policies = self.enforcer.get_filtered_grouping_policy(1, role)
        
        # Filter by domain and extract users
        users = []
        for policy in all_policies:
            if len(policy) >= 3 and policy[2] == target_domain:
                users.append(policy[0])  # user is at index 0
        
        return users
    
    def get_permissions_for_user(self, user: str):
        """Get permissions for user"""
        return self.enforcer.get_permissions_for_user(user)
    
    def get_filtered_policy(self, field_index: int, *field_values):
        """
        Get filtered policy from the underlying enforcer.
        Delegates directly to the underlying Casbin enforcer.
        """
        return self.enforcer.get_filtered_policy(field_index, *field_values)
    
    def get_filtered_grouping_policy(self, field_index: int, *field_values):
        """
        Get filtered grouping policy from the underlying enforcer.
        Delegates directly to the underlying Casbin enforcer.
        """
        return self.enforcer.get_filtered_grouping_policy(field_index, *field_values)
    
    def get_all_policy(self):
        """Get all policies from the underlying enforcer"""
        return self.enforcer.get_policy()


def create_enforcer_with_org_context(enforcer: CasbinEnforcer, org_domain: str) -> MultiTenantEnforcerWrapper:
    """
    Create an enforcer wrapper with organization context set.
    Use this in API endpoints to get an enforcer that automatically uses the organization domain.
    """
    wrapper = MultiTenantEnforcerWrapper(enforcer)
    wrapper.set_org_domain(org_domain)
    return wrapper
