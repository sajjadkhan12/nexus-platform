from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import is_allowed, OrgAwareEnforcer, get_org_aware_enforcer, get_db
from app.schemas.rbac import PermissionResponse
from app.models.rbac import PermissionMetadata
from app.core.permission_registry import PERMISSIONS_BY_SLUG, get_permission

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    current_user = Depends(is_allowed("platform:permissions:list")),
    enforcer: OrgAwareEnforcer = Depends(get_org_aware_enforcer),
    db: AsyncSession = Depends(get_db)
):
    """
    List all permissions with enriched metadata.
    Returns permissions from the permission registry with metadata (name, description, category, icon).
    """
    # Get all permissions from registry
    all_permissions = []
    
    # Try to get metadata from database first, fallback to registry
    db_metadata = {}
    try:
        result = await db.execute(select(PermissionMetadata))
        db_metadata = {perm.slug: perm for perm in result.scalars().all()}
    except Exception:
        # Table doesn't exist yet - will use registry metadata only
        pass
    
    # Use registry as source of truth for all available permissions
    # Registry always takes precedence over database metadata
    for perm_def in PERMISSIONS_BY_SLUG.values():
        slug = perm_def["slug"]
        
        # Database metadata is only used for ID and created_at
        # All other fields come from registry (source of truth)
        db_perm = db_metadata.get(slug)
        
        perm_response = PermissionResponse(
            id=db_perm.id if db_perm else None,
            slug=slug,
            name=perm_def.get("name"),  # From registry
            description=perm_def.get("description"),  # From registry
            category=perm_def.get("category"),  # From registry (always use this)
            resource=perm_def.get("resource"),  # From registry
            action=perm_def.get("action"),  # From registry
            environment=perm_def.get("environment"),  # From registry
            icon=perm_def.get("icon"),  # From registry
            created_at=db_perm.created_at if db_perm else None
        )
        all_permissions.append(perm_response)
    
    # Sort by category, then by name
    all_permissions.sort(key=lambda p: (p.category or "", p.name or p.slug))
    
    return all_permissions