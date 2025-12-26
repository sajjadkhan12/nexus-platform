"""Plugin version management endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import PluginVersion, User
from app.schemas.plugins import PluginVersionResponse
from app.api.deps import get_current_user
from app.core.utils import get_or_404

router = APIRouter()

@router.get("/{plugin_id}/versions", response_model=List[PluginVersionResponse])
async def list_plugin_versions(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions of a plugin"""
    result = await db.execute(
        select(PluginVersion).where(PluginVersion.plugin_id == plugin_id)
    )
    versions = result.scalars().all()
    return versions

@router.get("/{plugin_id}/versions/{version}", response_model=PluginVersionResponse)
async def get_plugin_version(
    plugin_id: str,
    version: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific plugin version details"""
    result = await db.execute(
        select(PluginVersion).where(
            PluginVersion.plugin_id == plugin_id,
            PluginVersion.version == version
        )
    )
    plugin_version = await get_or_404(
        db, PluginVersion, version, 
        identifier_field="version",
        resource_name="Plugin version"
    )
    return plugin_version

