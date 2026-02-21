from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import logging

from app.database import get_db
from app import models
from app.config import settings

logger = logging.getLogger(__name__)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# auto_error=False allows us to handle missing tokens manually
security_scheme = HTTPBearer(auto_error=False)


class MockUser:
    """
    Mock user object for development mode when authentication is disabled.
    Provides same interface as real User model for seamless operation.
    Uses valid UUIDs for tenant_id and user_id to pass DB validation.
    Includes created_at for response serialization compatibility.
    """
    def __init__(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None, email: str = "dev@autonomos.dev"):
        from uuid import uuid4
        from aam_hybrid.shared.constants import DEMO_TENANT_UUID
        
        # Use valid UUIDs for DB operations (critical for AAM endpoints)
        self.tenant_id = tenant_id or str(DEMO_TENANT_UUID)  # Valid UUID
        self.user_id = user_id or str(uuid4())  # Valid UUID
        self.email = email  # Use .dev domain (valid TLD, passes Pydantic EmailStr validation)
        self.id = self.user_id  # Alias for compatibility
        self.is_admin = True  # Dev user has admin privileges
        self.created_at = datetime.utcnow()  # Required for response serialization
        
    def __repr__(self):
        return f"<MockUser(id='{self.id}', tenant_id='{self.tenant_id}', email='{self.email}')>"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency that extracts and validates the JWT token from the Authorization header.
    Returns the current authenticated user.
    
    When AUTH_ENABLED=false (development mode), returns a MockUser for seamless local development.
    When AUTH_ENABLED=true (production mode), validates JWT and returns real user.
    """
    # Require valid JWT token
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_id: Optional[str] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(models.User).filter(models.User.id == UUID(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """Authenticate a user by email and password."""
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not verify_password(password, str(user.hashed_password)):  # type: ignore[arg-type]  # SQLAlchemy Column resolved to str at runtime
        return None
    return user
