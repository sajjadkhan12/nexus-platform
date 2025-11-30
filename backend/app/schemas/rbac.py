from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class PermissionBase(BaseModel):
    slug: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionResponse(PermissionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permissions: List[str] = [] # List of permission slugs

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleResponse(RoleBase):
    id: UUID
    created_at: datetime
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class GroupResponse(GroupBase):
    id: UUID
    created_at: datetime
    # We will populate these manually in the API
    users: List[dict] = [] 
    roles: List[RoleResponse] = []

    class Config:
        from_attributes = True
