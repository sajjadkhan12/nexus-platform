from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.database import get_db
from app.api.deps import get_current_active_superuser, is_allowed
from app.models.rbac import Permission
from app.core.rbac import Permission as PermConstants
from app.schemas.rbac import PermissionResponse

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    current_user = Depends(is_allowed(PermConstants.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Permission))
    return result.scalars().all()
