from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.schemas.rbac import RoleResponse

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserAdminUpdate(UserUpdate):
    roles: Optional[List[str]] = None # List of role names or IDs
    is_active: Optional[bool] = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    roles: List[str] = []  # List of role names from Casbin
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UserInDB(UserResponse):
    hashed_password: str

class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    skip: int
    limit: int
