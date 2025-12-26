from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy import delete, or_
from app.database import get_db
from app.schemas.auth import TokenResponse, LoginRequest
from app.models.rbac import User, RefreshToken, Role
from app.core.security import (
    verify_password, 
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.casbin import get_enforcer
from app.schemas.user import UserResponse
from app.config import settings
from datetime import datetime, timedelta, timezone
import re

router = APIRouter(prefix="/auth", tags=["authentication"])

async def get_user_with_roles(user: User, db: AsyncSession) -> UserResponse:
    """
    Helper to convert User model to UserResponse with Casbin roles.
    Filters roles to ensure only actual roles from the database are returned (not group names).
    """
    # Use OrgAwareEnforcer to properly handle organization domain
    from app.api.deps import get_org_aware_enforcer
    from app.core.organization import get_user_organization, get_organization_domain
    
    # Get organization and set up enforcer with proper domain
    org = await get_user_organization(user, db)
    org_domain = get_organization_domain(org)
    
    # Get the enforcer (this will be a MultiTenantEnforcerWrapper)
    enforcer = get_enforcer()
    
    # Set the organization domain on the enforcer if it supports it
    if hasattr(enforcer, 'set_org_domain'):
        enforcer.set_org_domain(org_domain)
    
    # Get roles for user within their organization
    # Pass org_domain explicitly to ensure correct domain is used
    if hasattr(enforcer, 'get_roles_for_user'):
        # MultiTenantEnforcerWrapper.get_roles_for_user accepts optional domain parameter
        roles = enforcer.get_roles_for_user(str(user.id), org_domain)
    else:
        # Base Casbin Enforcer, need to use get_implicit_roles_for_user with domain
        try:
            implicit_roles = enforcer.get_implicit_roles_for_user(str(user.id), org_domain)
            roles = []
            for role_info in implicit_roles:
                if isinstance(role_info, (list, tuple)) and len(role_info) > 0:
                    roles.append(role_info[0])
                else:
                    roles.append(role_info)
            roles = list(set(roles))
        except Exception:
            roles = []
    
    # Filter roles to ensure they exist in the database (exclude group names)
    if roles:
        # Get all valid role names from database
        result = await db.execute(select(Role.name))
        valid_role_names = {role_name for role_name in result.scalars().all()}
        
        # Filter roles to only include valid roles
        filtered_roles = [role for role in roles if role in valid_role_names]
        
        # Remove duplicates
        roles = list(set(filtered_roles))
    else:
        roles = []
    
    user_response = UserResponse.model_validate(user)
    user_response.roles = roles
    return user_response

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response, 
    login_data: LoginRequest, 
    db: AsyncSession = Depends(get_db)
):
    from app.logger import logger
    
    # Log login attempt (for security monitoring)
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Login attempt for identifier: {login_data.identifier} from IP: {client_ip}")
    
    # Determine if identifier is an email or username
    # Simple email pattern check
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_email = re.match(email_pattern, login_data.identifier.strip()) is not None
    
    # Fetch user with organization eagerly loaded
    # Try to find user by email or username
    if is_email:
        result = await db.execute(
            select(User)
            .options(selectinload(User.organization))
            .where(User.email == login_data.identifier.strip().lower())
        )
    else:
        result = await db.execute(
            select(User)
            .options(selectinload(User.organization))
            .where(User.username == login_data.identifier.strip())
        )
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        # Log failed login attempt for security monitoring
        logger.warning(f"Failed login attempt for identifier: {login_data.identifier} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password"
        )
    
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {login_data.email} from IP: {client_ip}")
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Log successful login
    logger.info(f"Successful login for user: {user.email} (username: {user.username}, ID: {user.id}) from IP: {client_ip}")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Get user_id as string to avoid lazy loading issues after rollback
    user_id_str = str(user.id)
    
    # Store refresh token with retry logic for duplicate key errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db_refresh_token = RefreshToken(
                user_id=user.id,  # Use user.id here (before any rollback)
                token=refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.add(db_refresh_token)
            await db.commit()
            break  # Success, exit retry loop
        except IntegrityError as e:
            await db.rollback()
            # If duplicate token error, generate a new token and retry
            error_str = str(e).lower()
            if "duplicate key" in error_str or "unique constraint" in error_str or "refresh_tokens_token_key" in error_str:
                if attempt < max_retries - 1:
                    # Generate a new token using user_id_str (avoid lazy loading after rollback)
                    refresh_token = create_refresh_token(data={"sub": user_id_str})
                    continue
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate unique refresh token"
                    )
            else:
                raise
    
    # Set HTTP-only cookie (secure based on environment)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,  # True in production (HTTPS required), False in development
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": await get_user_with_roles(user, db)
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
        
    # Verify token
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
        
    user_id = payload.get("sub")
    
    # Check if token exists in DB and is valid
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token))
    db_token = result.scalars().first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if token has expired (additional check beyond JWT expiration)
    if db_token.expires_at < datetime.now(timezone.utc):
        # Delete expired token from database
        await db.execute(delete(RefreshToken).where(RefreshToken.id == db_token.id))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
        
    # Check if user exists and is active (with organization loaded)
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
        
    # Get user_id as string to avoid lazy loading issues after rollback
    user_id_str = str(user.id)
    
    # Rotate tokens
    new_access_token = create_access_token(data={"sub": user_id_str})
    new_refresh_token = create_refresh_token(data={"sub": user_id_str})
    
    # Update DB - delete old token first, then add new one
    # Use direct DELETE statement to avoid warnings if token was already deleted
    await db.execute(delete(RefreshToken).where(RefreshToken.id == db_token.id))
    await db.flush()  # Ensure delete is processed before insert
    
    # Create new token with retry logic for duplicate key errors (handles race conditions)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            new_db_token = RefreshToken(
                user_id=user_id,  # Use user_id from JWT (already validated)
                token=new_refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.add(new_db_token)
            await db.commit()
            break  # Success, exit retry loop
        except IntegrityError as e:
            await db.rollback()
            # If duplicate token error, generate a new token and retry
            error_str = str(e).lower()
            if "duplicate key" in error_str or "unique constraint" in error_str or "refresh_tokens_token_key" in error_str:
                if attempt < max_retries - 1:
                    # Generate a new token using user_id_str (avoid lazy loading after rollback)
                    new_refresh_token = create_refresh_token(data={"sub": user_id_str})
                    continue
                else:
                    # Last attempt failed, raise the error
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate unique refresh token after multiple attempts"
                    )
            else:
                # Different error, re-raise it
                raise
    
    # Set new cookie (secure based on environment)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=not settings.DEBUG,  # True in production (HTTPS required), False in development
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": await get_user_with_roles(user, db)
    }

@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if refresh_token:
        # Delete from DB using direct DELETE statement to avoid warnings
        await db.execute(delete(RefreshToken).where(RefreshToken.token == refresh_token))
        await db.commit()
            
    # Clear cookie
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
