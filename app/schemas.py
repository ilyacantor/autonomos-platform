from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserRegister(BaseModel):
    name: str  # Organization/tenant name
    email: EmailStr
    password: str

class User(UserBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

class TaskBase(BaseModel):
    payload: dict[str, Any]

class TaskCreate(TaskBase):
    callback_url: Optional[str] = None
    max_retries: Optional[int] = 0
    timeout_seconds: Optional[int] = None
    on_success_next_task: Optional[dict[str, Any]] = None

class Task(TaskBase):
    id: UUID
    status: str
    result: Optional[dict[str, Any]] = None
    callback_url: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    on_success_next_task: Optional[dict[str, Any]] = None
    next_task_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProdModeRequest(BaseModel):
    enabled: bool
