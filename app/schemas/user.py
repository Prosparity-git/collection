from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_id: int
    user_name: str
    user_role: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    mobile: Optional[str] = None
    status: Optional[str] = "active"
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserResponse(BaseModel):
    id: int
    name: str
    user_name: str
    email: str
    mobile: Optional[str] = None
    role: str
    status: Optional[str] = None
    # 🎯 NEW FIELDS FOR LOGIN/LOGOUT TRACKING
    last_login_time: Optional[datetime] = None
    last_logout_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

# Bulk Registration Schemas
class BulkUserCreate(BaseModel):
    users: list[UserCreate]
    
    @validator('users')
    def validate_users_list(cls, v):
        if not v:
            raise ValueError('Users list cannot be empty')
        if len(v) > 100:  # Limit to 100 users per batch
            raise ValueError('Cannot register more than 100 users at once')
        return v

class BulkUserResponse(BaseModel):
    success_count: int
    failed_count: int
    created_users: list[UserResponse]
    failed_users: list[dict]  # Will contain user data and error message

# Keep old schemas for backward compatibility (deprecated)
class UserBase(BaseModel):
    name: str
    email: str
    mobile: str
    role: str
    status: Optional[str] = "active"

class UserOut(UserBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True  # Updated for Pydantic v2 