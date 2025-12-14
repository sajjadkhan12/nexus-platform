from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.schemas.auth import TokenResponse, LoginRequest
from app.models.rbac import User, RefreshToken
from app.core.security import (
    verify_password, 
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.casbin import enforcer
from app.schemas.user import UserResponse
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

def get_user_with_roles(user: User) -> UserResponse:
    """Helper to convert User model to UserResponse with Casbin roles"""
    roles = enforcer.get_roles_for_user(str(user.id))
    user_response = UserResponse.model_validate(user)
    user_response.roles = roles
    return user_response

@router.post("/login", response_model=TokenResponse)
async def login(response: Response, login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Fetch user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
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
                expires_at=datetime.utcnow() + timedelta(days=7)
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
    
    # Set HTTP-only cookie (secure=False for local development)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": get_user_with_roles(user)
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
        
    # Check if user exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
        
    # Get user_id as string to avoid lazy loading issues after rollback
    user_id_str = str(user.id)
    
    # Rotate tokens
    new_access_token = create_access_token(data={"sub": user_id_str})
    new_refresh_token = create_refresh_token(data={"sub": user_id_str})
    
    # Update DB - delete old token first, then add new one
    await db.delete(db_token)
    await db.flush()  # Ensure delete is processed before insert
    
    # Create new token with retry logic for duplicate key errors (handles race conditions)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            new_db_token = RefreshToken(
                user_id=user.id,  # Use user.id here (before any rollback)
                token=new_refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=7)
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
    
    # Set new cookie (secure=False for local development)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": get_user_with_roles(user)
    }

@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if refresh_token:
        # Delete from DB
        result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token))
        db_token = result.scalars().first()
        if db_token:
            await db.delete(db_token)
            await db.commit()
            
    # Clear cookie
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
