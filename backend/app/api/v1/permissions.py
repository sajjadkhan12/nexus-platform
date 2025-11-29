from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.api.deps import is_allowed
from app.models.rbac import Permission as PermissionModel
from app.schemas.rbac import PermissionResponse
from app.core.rbac import Permission as PermissionEnum

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(is_allowed(PermissionEnum.PERMISSIONS_LIST)),
):
    """
    List all permissions from the database.
    """
    result = await db.execute(select(PermissionModel))
    permissions = result.scalars().all()
    return permissions