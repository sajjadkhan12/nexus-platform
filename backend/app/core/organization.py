"""
Organization context helpers for multi-tenancy support
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Organization, User
import uuid


async def get_user_organization(user: User, db: AsyncSession) -> Organization:
    """
    Get the organization for a user.
    
    Args:
        user: The user object
        db: Database session
        
    Returns:
        Organization object
        
    Raises:
        ValueError: If organization not found
    """
    if hasattr(user, 'organization') and user.organization:
        return user.organization
    
    result = await db.execute(
        select(Organization).where(Organization.id == user.organization_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise ValueError(f"Organization not found for user {user.email}")
    
    return org


def get_organization_domain(organization: Organization) -> str:
    """
    Get the domain string for Casbin enforcement.
    
    Args:
        organization: Organization object
        
    Returns:
        Domain string (organization ID as string)
    """
    return str(organization.id)


def get_organization_domain_from_id(org_id: uuid.UUID) -> str:
    """
    Get the domain string from organization ID.
    
    Args:
        org_id: Organization UUID
        
    Returns:
        Domain string (organization ID as string)
    """
    return str(org_id)


async def get_or_create_default_organization(db: AsyncSession) -> Organization:
    """
    Get or create the default organization.
    This is used for backward compatibility and system initialization.
    
    Args:
        db: Database session
        
    Returns:
        Default Organization object
    """
    # Try to find existing default organization
    result = await db.execute(
        select(Organization).where(Organization.slug == "default")
    )
    org = result.scalar_one_or_none()
    
    if org:
        return org
    
    # Create default organization
    org = Organization(
        id=uuid.uuid4(),
        name="Default Organization",
        slug="default",
        description="Default organization for the platform",
        is_active=True
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    
    return org
