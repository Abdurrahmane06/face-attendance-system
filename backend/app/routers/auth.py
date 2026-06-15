"""Authentication router: register, login, refresh, logout, me.

All endpoints are public except /me which requires authentication.
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
    TokenResponse,
    UserInfo,
)
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Register a new user account.

    Args:
        request: Registration details.
        db: Database session.

    Returns:
        AuthResponse with JWT tokens and user info.
    """
    return await auth_service.register_user(db, request)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Authenticate a user and return JWT tokens.

    Args:
        request: Login credentials.
        db: Database session.

    Returns:
        AuthResponse with JWT tokens and user info.
    """
    return await auth_service.login_user(db, request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Refresh an access token using a valid refresh token.

    Args:
        request: Refresh token string.
        db: Database session.

    Returns:
        TokenResponse with new access token.
    """
    return await auth_service.refresh_access_token(db, request.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke a refresh token (logout).

    Args:
        request: Refresh token to revoke.
        db: Database session.
        current_user: Authenticated user.
    """
    await auth_service.logout_user(db, request.refresh_token)


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)) -> UserInfo:
    """Get the profile of the currently authenticated user.

    Args:
        current_user: Authenticated user.

    Returns:
        UserInfo for the current user.
    """
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active,
    )
