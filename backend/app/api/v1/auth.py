"""
Authentication API endpoints for ThermalTrace.
Provides POST /api/v1/auth/signup, POST /api/v1/auth/login, GET /api/v1/auth/me, and POST /api/v1/auth/logout.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.user import User
from app.services.auth import (
    hash_password,
    verify_password,
    create_session,
    get_session,
    revoke_session
)

router = APIRouter()


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, description="User full name")
    email: str = Field(..., min_length=5, description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: str
    name: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


@router.post("/auth/signup", response_model=AuthResponse)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    clean_email = req.email.strip().lower()

    # Check existing user
    stmt = select(User).where(User.email == clean_email)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")

    pwd_hash = hash_password(req.password)
    new_user = User(
        name=req.name.strip(),
        email=clean_email,
        password_hash=pwd_hash
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_session(new_user.id, new_user.email, new_user.name)
    return AuthResponse(
        token=token,
        user=UserResponse(id=new_user.id, name=new_user.name, email=new_user.email)
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user email and password."""
    clean_email = req.email.strip().lower()

    stmt = select(User).where(User.email == clean_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_session(user.id, user.email, user.name)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, name=user.name, email=user.email)
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(authorization: Optional[str] = Header(None)):
    """Get profile of current authenticated user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    sess = get_session(authorization)
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    return UserResponse(
        id=sess["user_id"],
        name=sess["name"],
        email=sess["email"]
    )


@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Revoke active session token on logout."""
    if authorization:
        revoke_session(authorization)
    return {"message": "Successfully logged out."}
