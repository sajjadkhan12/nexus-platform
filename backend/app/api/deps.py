from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.rbac import User
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Async query
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

from app.core.casbin import get_enforcer
from casbin import Enforcer

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
    enforcer: Enforcer = Depends(get_enforcer)
) -> User:
    # Check if user has 'admin' role using Casbin
    # We check if the user has the 'admin' role in the policy
    # g, user_id, role
    
    # Note: Casbin usually checks permissions (p), not just roles (g).
    # But for superuser check, we might want to check a specific high-level permission
    # or just check if they have the 'admin' role.
    
    # Let's check if they have 'users:delete' which is an admin permission
    # Or better, let's check if they are in the 'admin' group/role
    
    user_id = str(current_user.id)
    has_role = enforcer.has_grouping_policy(user_id, "admin")
    
    if not has_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def is_allowed(permission_slug: str):
    """Dependency for checking permissions using Casbin"""
    async def dependency(
        current_user: User = Depends(get_current_user),
        enforcer: Enforcer = Depends(get_enforcer)
    ):
        # Split slug into object and action
        # e.g. "users:list" -> obj="users", act="list"
        parts = permission_slug.split(":")
        if len(parts) < 2:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid permission slug: {permission_slug}"
            )
            
        obj = parts[0]
        act = ":".join(parts[1:])
        
        user_id = str(current_user.id)
        
        # Check permission: sub, obj, act
        if not enforcer.enforce(user_id, obj, act):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_slug} required"
            )
        return current_user
    return dependency
