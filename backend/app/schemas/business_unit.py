from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union
from datetime import datetime
import uuid

class BusinessUnitBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class BusinessUnitCreate(BusinessUnitBase):
    pass

class BusinessUnitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

class BusinessUnitResponse(BusinessUnitBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    is_active: bool
    role: Optional[str] = None  # Role name (e.g., "bu-owner", "developer", "viewer")
    member_count: Optional[int] = 0  # Number of members in this business unit
    can_manage_members: Optional[bool] = False  # Whether user has business_units:manage_members permission
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class BusinessUnitMemberAdd(BaseModel):
    user_email: str = Field(..., description="Email of user to add")
    role_id: Optional[Union[uuid.UUID, str]] = Field(None, description="Role ID (UUID or string UUID)")
    role: Optional[str] = Field(None, description="Role name (for backward compatibility: 'owner' -> 'bu-owner', 'member' -> 'viewer')")
    
    @field_validator('role_id', mode='before')
    @classmethod
    def validate_role_id(cls, v):
        """Convert string UUID to UUID object, or None if empty/invalid"""
        if v is None:
            return None
        if isinstance(v, uuid.UUID):
            return v
        if isinstance(v, str):
            # Handle empty string
            if v.strip() == '':
                return None
            try:
                return uuid.UUID(v)
            except (ValueError, TypeError):
                # Invalid UUID string, return None
                return None
        return v

class BusinessUnitMemberResponse(BaseModel):
    id: uuid.UUID
    business_unit_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: Optional[str]
    role: str  # Role name (e.g., "bu-owner", "developer", "viewer")
    role_id: Optional[uuid.UUID] = None  # Role ID for reference
    created_at: datetime
    
    model_config = {"from_attributes": True}

class BusinessUnitGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    role_id: uuid.UUID = Field(..., description="Role ID to assign to group members")

class BusinessUnitGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    role_id: Optional[uuid.UUID] = None

class BusinessUnitGroupResponse(BaseModel):
    id: uuid.UUID
    business_unit_id: uuid.UUID
    name: str
    description: Optional[str]
    role_id: uuid.UUID
    role_name: Optional[str] = None
    member_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class BusinessUnitGroupMemberAdd(BaseModel):
    user_email: str = Field(..., description="Email of user to add to group")

class BusinessUnitGroupMemberResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}

