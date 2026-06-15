"""Authentication service: registration, login, token management.

Handles user creation, password verification, JWT token generation,
and refresh token lifecycle management.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserInfo

logger = logging.getLogger(__name__)


async def register_user(
    db: AsyncSession, request: RegisterRequest
) -> AuthResponse:
    """Register a new user account.

    Args:
        db: Database session.
        request: Registration details (email, full_name, password, role).

    Returns:
        AuthResponse with tokens and user info.

    Raises:
        HTTPException 409: If email already exists.
    """
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        role=request.role,
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token({"sub": user.id})
    refresh_token_str = create_refresh_token({"sub": user.id})

    await _store_refresh_token(db, user.id, refresh_token_str)

    return AuthResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        ),
        user=UserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            department=user.department,
            is_active=user.is_active,
        ),
    )


async def login_user(db: AsyncSession, request: LoginRequest) -> AuthResponse:
    """Authenticate a user and return tokens.

    Args:
        db: Database session.
        request: Login credentials (email, password).

    Returns:
        AuthResponse with tokens and user info.

    Raises:
        HTTPException 401: If credentials are invalid.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    access_token = create_access_token({"sub": user.id})
    refresh_token_str = create_refresh_token({"sub": user.id})

    await _store_refresh_token(db, user.id, refresh_token_str)

    return AuthResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        ),
        user=UserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            department=user.department,
            is_active=user.is_active,
        ),
    )


async def refresh_access_token(
    db: AsyncSession, refresh_token_str: str
) -> TokenResponse:
    """Issue a new access token using a valid refresh token.

    Args:
        db: Database session.
        refresh_token_str: Refresh token string.

    Returns:
        TokenResponse with new access token.

    Raises:
        HTTPException 401: If refresh token is invalid or revoked.
    """
    payload = verify_token(refresh_token_str, expected_type="refresh")
    user_id: str = payload.get("sub")

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token_str,
            RefreshToken.is_revoked == False,
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
        )

    new_access = create_access_token({"sub": user_id})
    return TokenResponse(
        access_token=new_access,
        refresh_token=refresh_token_str,
    )


async def logout_user(db: AsyncSession, refresh_token_str: str) -> None:
    """Revoke a refresh token.

    Args:
        db: Database session.
        refresh_token_str: Refresh token to revoke.
    """
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    stored = result.scalar_one_or_none()
    if stored:
        stored.is_revoked = True
        await db.flush()


async def _store_refresh_token(db: AsyncSession, user_id: str, token: str) -> None:
    """Persist a refresh token in the database.

    Args:
        db: Database session.
        user_id: Owner user UUID.
        token: Refresh token string.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    rt = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    db.add(rt)
    await db.flush()
