"""
Organization management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models import User, Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.api.deps import get_current_user, is_allowed
from app.logger import logger
import uuid

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(is_allowed("platform:organizations:list")),
    db: AsyncSession = Depends(get_db)
):
    """
    List all organizations (admin only).
    """
    result = await db.execute(
        select(Organization)
        .offset(skip)
        .limit(limit)
        .order_by(Organization.created_at.desc())
    )
    organizations = result.scalars().all()
    return organizations


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return organization


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(is_allowed("platform:organizations:list")),
    db: AsyncSession = Depends(get_db)
):
    """
    Get organization by ID (admin only).
    """
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return organization


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    current_user: User = Depends(is_allowed("platform:organizations:list")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new organization (admin only).
    """
    # Check if organization with same name or slug exists
    result = await db.execute(
        select(Organization).where(
            (Organization.name == org_in.name) | (Organization.slug == org_in.slug)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.name == org_in.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this name already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this slug already exists"
            )
    
    # Create new organization
    organization = Organization(
        id=uuid.uuid4(),
        name=org_in.name,
        slug=org_in.slug,
        description=org_in.description,
        is_active=True
    )
    
    db.add(organization)
    await db.commit()
    await db.refresh(organization)
    
    logger.info(f"Organization created: {organization.name} by {current_user.email}")
    
    return organization


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_in: OrganizationUpdate,
    current_user: User = Depends(is_allowed("platform:organizations:list")),
    db: AsyncSession = Depends(get_db)
):
    """
    Update organization (admin only).
    """
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    if org_in.name is not None:
        # Check if name is taken by another organization
        result = await db.execute(
            select(Organization).where(
                (Organization.name == org_in.name) & (Organization.id != org_uuid)
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already in use"
            )
        organization.name = org_in.name
    
    if org_in.description is not None:
        organization.description = org_in.description
    
    if org_in.is_active is not None:
        organization.is_active = org_in.is_active
    
    await db.commit()
    await db.refresh(organization)
    
    logger.info(f"Organization updated: {organization.name} by {current_user.email}")
    
    return organization


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    current_user: User = Depends(is_allowed("platform:organizations:list")),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete organization (admin only).
    WARNING: This will cascade delete all users in the organization!
    """
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID"
        )
    
    result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Prevent deletion of default organization
    if organization.slug == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default organization"
        )
    
    # Check if organization has users
    result = await db.execute(
        select(func.count(User.id)).where(User.organization_id == org_uuid)
    )
    user_count = result.scalar()
    
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {user_count} users. Move or delete users first."
        )
    
    await db.delete(organization)
    await db.commit()
    
    logger.info(f"Organization deleted: {organization.name} by {current_user.email}")
    
    from fastapi.responses import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
