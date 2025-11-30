from fastapi import APIRouter, Depends
from typing import List
from app.api.deps import is_allowed
from app.schemas.rbac import PermissionResponse
from app.core.casbin import get_enforcer
from casbin import Enforcer
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    current_user = Depends(is_allowed("permissions:list")),
    enforcer: Enforcer = Depends(get_enforcer)
):
    """
    List all unique permissions from Casbin policies.
    A permission is identified by unique (obj, act) pairs.
    """
    all_policies = enforcer.get_policy()
    
    # Extract unique permissions (obj:act)
    permissions = set()
    for policy in all_policies:
        if len(policy) >= 3:
            # policy format: [role, obj, act]
            perm_slug = f"{policy[1]}:{policy[2]}"
            permissions.add(perm_slug)
    
    # Convert to response format
    perm_responses = []
    for perm_slug in permissions:
        perm_responses.append(PermissionResponse(
            id=uuid4(),
            slug=perm_slug,
            description=f"Permission for {perm_slug}",
            created_at=datetime.now()
        ))
    
    return perm_responses