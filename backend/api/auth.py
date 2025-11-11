"""
Authentication API endpoints
Handles user login, registration, and JWT token management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

from core.database import get_db
from core.security import create_access_token, get_current_user, verify_password, hash_password
from models.user import User, UserRole

router = APIRouter()


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class LoginRequest(BaseModel):
    """Login request payload"""
    email: str
    password: Optional[str] = None  # Optional for OAuth flow
    open_id: Optional[str] = None  # For OAuth (Manus)


class RegisterRequest(BaseModel):
    """Registration request payload"""
    email: EmailStr
    name: str
    password: Optional[str] = None
    open_id: Optional[str] = None  # OAuth identifier
    login_method: Optional[str] = "email"  # "email" or "oauth"


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """User profile response"""
    id: int
    email: Optional[str]
    name: Optional[str]
    role: str
    created_at: str


# ============================================
# Authentication Endpoints
# ============================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    Supports both email/password and OAuth registration
    """
    # Check if user already exists
    existing_user = None

    if request.open_id:
        existing_user = db.query(User).filter(User.open_id == request.open_id).first()
    elif request.email:
        existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    # Create new user
    new_user = User(
        open_id=request.open_id or f"email_{request.email}",
        email=request.email,
        name=request.name,
        login_method=request.login_method,
        role=UserRole.USER,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT token
    access_token = create_access_token(data={"sub": new_user.id})

    return TokenResponse(
        access_token=access_token,
        user=new_user.to_dict()
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT token
    Supports both OAuth (open_id) and email/password
    """
    user = None

    # OAuth login (via Manus or other OAuth provider)
    if request.open_id:
        user = db.query(User).filter(User.open_id == request.open_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OAuth credentials"
            )

    # Email login (future implementation)
    elif request.email:
        user = db.query(User).filter(User.email == request.email).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Update last signed in timestamp
    user.last_signed_in = datetime.utcnow()
    db.commit()

    # Generate JWT token
    access_token = create_access_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        user=user.to_dict()
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user profile
    Requires valid JWT token in Authorization header
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/logout")
async def logout():
    """
    Logout user
    Note: JWT tokens are stateless, so this is mostly for client-side cleanup
    In production, consider implementing token blacklisting with Redis
    """
    return {"message": "Logged out successfully"}


@router.get("/check")
async def check_auth(current_user: User = Depends(get_current_user)):
    """
    Check if user is authenticated
    Returns user data if valid token provided
    """
    return {
        "authenticated": True,
        "user": current_user.to_dict()
    }
