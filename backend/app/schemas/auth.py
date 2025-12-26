from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.schemas.user import UserResponse
import re

class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Email address or username")
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    pass # No body needed, uses cookie
