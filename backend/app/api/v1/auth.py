from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.schemas.auth import TokenResponse, RegisterRequest, LoginRequest
from app.models.rbac import User, Role, RefreshToken
from app.core.security import (
    verify_password, 
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Get default 'engineer' role
    result = await db.execute(select(Role).where(Role.name == "engineer"))
    engineer_role = result.scalars().first()
    
    if not engineer_role:
        # Create default role if it doesn't exist (should be done in seeding)
        engineer_role = Role(name="engineer", description="Default user role")
        db.add(engineer_role)
    
    # Create new user
    username = request.email.split("@")[0]
    user = User(
        email=request.email,
        username=username,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        roles=[engineer_role]
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token in DB
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_refresh_token)
    await db.commit()

    # Set HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True, # Set to True in production
        samesite="lax"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/login", response_model=TokenResponse)
async def login(response: Response, login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    from app.logger import logger
    
    # Fetch user with roles
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Debug logging
    logger.info(f"User {user.email} logging in")
    logger.info(f"User has {len(user.roles)} roles")
    for role in user.roles:
        logger.info(f"  - Role: {role.name} with {len(role.permissions)} permissions")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_refresh_token)
    await db.commit()
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
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
        
    # Rotate tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Update DB
    await db.delete(db_token)
    new_db_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(new_db_token)
    await db.commit()
    
    # Set new cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": user
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
