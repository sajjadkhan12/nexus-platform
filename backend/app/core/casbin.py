import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.enforcer_wrapper import MultiTenantEnforcerWrapper, create_enforcer_with_org_context
from app.models.rbac import User
from typing import Optional
import os
import time

# Create a synchronous engine for Casbin adapter
# The adapter currently requires a sync engine
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
if "postgresql://" not in sync_db_url and "postgresql+psycopg2://" not in sync_db_url:
    sync_db_url = sync_db_url.replace("postgresql:", "postgresql+psycopg2:")

engine = create_engine(sync_db_url)

# Initialize adapter
adapter = Adapter(engine)

# Path to model.conf
model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rbac_model.conf")

# Initialize enforcer
_base_enforcer = casbin.Enforcer(model_path, adapter)

# For backward compatibility, keep the global enforcer reference
# but it will be wrapped
enforcer = _base_enforcer

# Policy cache: track last reload time and cache TTL (5 seconds)
_policy_cache = {
    "last_reload": 0,
    "cache_ttl": 5.0  # Reload policy every 5 seconds max
}

def _should_reload_policy() -> bool:
    """Check if policy should be reloaded based on cache TTL"""
    now = time.time()
    if now - _policy_cache["last_reload"] > _policy_cache["cache_ttl"]:
        _policy_cache["last_reload"] = now
        return True
    return False

def invalidate_policy_cache():
    """Invalidate policy cache - call this when permissions change"""
    _policy_cache["last_reload"] = 0

def get_enforcer():
    """
    Dependency to get Casbin enforcer.
    
    Returns a wrapper that accepts both old (3-param) and new (4-param) formats.
    For proper multi-tenancy, the wrapper needs org_domain to be set via set_org_domain().
    """
    # Reload policy only if cache expired (performance optimization)
    if _should_reload_policy():
        _base_enforcer.load_policy()
    # Return wrapper that supports both old and new formats
    wrapper = MultiTenantEnforcerWrapper(_base_enforcer)
    return wrapper

async def get_enforcer_with_org(
    current_user: Optional[User] = None,
    db: Optional[AsyncSession] = None,
    org_domain: Optional[str] = None
) -> MultiTenantEnforcerWrapper:
    """
    Dependency to get organization-aware Casbin enforcer.
    
    This enforcer automatically injects organization domain into all enforcement checks.
    
    Args:
        current_user: Current authenticated user (to get organization from)
        db: Database session (to load organization if needed)
        org_domain: Explicit organization domain (if already known)
        
    Returns:
        MultiTenantEnforcerWrapper with organization context set
    """
    # Reload policy only if cache expired (performance optimization)
    if _should_reload_policy():
        _base_enforcer.load_policy()
    
    # Determine organization domain
    domain = org_domain
    if not domain and current_user:
        from app.core.organization import get_user_organization, get_organization_domain
        if db:
            org = await get_user_organization(current_user, db)
            domain = get_organization_domain(org)
        elif hasattr(current_user, 'organization') and current_user.organization:
            domain = get_organization_domain(current_user.organization)
    
    if not domain:
        # If we still don't have a domain, create a wrapper without context
        # It will log warnings on enforcement checks
        return MultiTenantEnforcerWrapper(_base_enforcer)
    
    return create_enforcer_with_org_context(_base_enforcer, domain)
