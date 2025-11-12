from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import crud, schemas, models
from app.database import get_db
from app.config import settings
from app.security import authenticate_user, create_access_token, get_current_user

router = APIRouter()

@router.post("/register", response_model=schemas.UserRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user and create their tenant.
    This endpoint creates both a tenant and the first user for that tenant,
    and returns an access token for immediate authentication.
    """
    existing_user = crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        tenant = crud.create_tenant(db, schemas.TenantCreate(name=user_data.name))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists. Please choose a different name."
        )
    
    try:
        user = crud.create_user(
            db, 
            schemas.UserCreate(email=user_data.email, password=user_data.password),
            tenant.id
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create user. Please try again."
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
        expires_delta=access_token_expires
    )
    
    return {
        "user": user,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint to get a JWT access token.
    Accepts JSON body with email and password.
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get the currently authenticated user's information"""
    return current_user
