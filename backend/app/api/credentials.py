"""Cloud credentials management API (Admin only)"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import CloudCredential, CloudProvider, User
from app.schemas.plugins import CloudCredentialCreate, CloudCredentialResponse
from app.services.crypto import crypto_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/admin/credentials", tags=["Admin - Credentials"])

def check_admin(current_user: User) -> User:
    """Check if user is admin"""
    # TODO: Implement proper role check
    # For now, assume all authenticated users are admins
    return current_user

@router.post("/", response_model=CloudCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    credential: CloudCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update cloud credentials (Admin only)
    """
    # Check admin permission
    check_admin(current_user)
    
    # Validate provider
    try:
        provider_enum = CloudProvider(credential.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {', '.join([p.value for p in CloudProvider])}"
        )
    
    # Check if credential with this name exists
    result = await db.execute(
        select(CloudCredential).where(CloudCredential.name == credential.name)
    )
    existing = result.scalar_one_or_none()
    
    # Encrypt credentials
    encrypted_data = crypto_service.encrypt(credential.credentials)
    
    if existing:
        # Update existing
        existing.provider = provider_enum
        existing.encrypted_data = encrypted_data
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Create new
        new_credential = CloudCredential(
            name=credential.name,
            provider=provider_enum,
            encrypted_data=encrypted_data
        )
        db.add(new_credential)
        await db.commit()
        await db.refresh(new_credential)
        return new_credential

@router.get("/", response_model=List[CloudCredentialResponse])
async def list_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all configured credentials (without secrets)"""
    check_admin(current_user)
    
    result = await db.execute(select(CloudCredential))
    credentials = result.scalars().all()
    return credentials

@router.get("/{credential_id}", response_model=CloudCredentialResponse)
async def get_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get credential details (without secrets)"""
    check_admin(current_user)
    
    result = await db.execute(
        select(CloudCredential).where(CloudCredential.id == credential_id)
    )
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    return credential

@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a credential"""
    check_admin(current_user)
    
    result = await db.execute(
        select(CloudCredential).where(CloudCredential.id == credential_id)
    )
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    await db.delete(credential)
    await db.commit()
