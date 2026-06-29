"""Authentication router: register, login, refresh, logout, me, seed-admin.

Public endpoints: /register, /login, /refresh, /seed-admin.
Protected:        /logout (requires valid access token), /me.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SeedAdminRequest,
    TokenResponse,
    UserInfo,
)
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new USER account (public).

    Role is always USER — use POST /api/v1/users to create admins.
    """
    return await auth_service.register_user(db, request)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with email + password, receive JWT token pair."""
    return await auth_service.login_user(db, request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token."""
    return await auth_service.refresh_access_token(db, request.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke the provided refresh token (logout)."""
    await auth_service.logout_user(db, request.refresh_token)


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)) -> UserInfo:
    """Return the profile of the currently authenticated user."""
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active,
    )


@router.post(
    "/seed-admin",
    response_model=AuthResponse,
    status_code=201,
    summary="Bootstrap first admin (one-time use)",
    description=(
        "Creates the very first ADMIN account. "
        "Returns 409 if an admin already exists. "
        "Use the default body or supply custom credentials."
    ),
)
async def seed_admin(
    request: SeedAdminRequest = SeedAdminRequest(),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """One-time endpoint to create the first admin account."""
    return await auth_service.create_first_admin(db, request)
