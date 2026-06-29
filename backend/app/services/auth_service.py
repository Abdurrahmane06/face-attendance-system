"""Authentication service: registration, login, token management, admin seeding.

All passwords are hashed with bcrypt.  Tokens are signed with HS256 JWT.
Refresh tokens are persisted in the database to support revocation.
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
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    SeedAdminRequest,
    TokenResponse,
    UserInfo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def register_user(db: AsyncSession, request: RegisterRequest) -> AuthResponse:
    """Register a new USER-role account.

    Public endpoint — role is always USER. Admins are created via /users or seed.

    Raises:
        HTTPException 409: Email already registered.
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
        role="USER",
    )
    db.add(user)
    await db.flush()

    return await _build_auth_response(db, user)


async def login_user(db: AsyncSession, request: LoginRequest) -> AuthResponse:
    """Authenticate with email + password and return token pair.

    Raises:
        HTTPException 401: Invalid credentials or inactive account.
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

    return await _build_auth_response(db, user)


async def refresh_access_token(db: AsyncSession, refresh_token_str: str) -> TokenResponse:
    """Issue a new access token from a valid, non-revoked refresh token.

    Raises:
        HTTPException 401: Token invalid, expired, or revoked.
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
    """Revoke a refresh token (logout)."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    stored = result.scalar_one_or_none()
    if stored:
        stored.is_revoked = True
        await db.flush()


async def create_first_admin(db: AsyncSession, request: SeedAdminRequest) -> AuthResponse:
    """Bootstrap the very first ADMIN account.

    Succeeds only when no ADMIN exists yet. Subsequent calls return 409.
    Use POST /api/v1/users to create additional admins.

    Raises:
        HTTPException 409: An admin already exists.
        HTTPException 409: Email already registered as a non-admin.
    """
    admin_exists = await db.execute(
        select(User).where(User.role == "ADMIN", User.deleted_at.is_(None))
    )
    if admin_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An admin account already exists. "
                "Log in and use POST /api/v1/users to create additional admins."
            ),
        )

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
        role="ADMIN",
    )
    db.add(user)
    await db.flush()

    logger.info("First admin account created: %s", user.email)
    return await _build_auth_response(db, user)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _build_auth_response(db: AsyncSession, user: User) -> AuthResponse:
    """Generate token pair, persist refresh token, return AuthResponse."""
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


async def _store_refresh_token(db: AsyncSession, user_id: str, token: str) -> None:
    """Persist a refresh token (expires in REFRESH_TOKEN_EXPIRE_DAYS days)."""
    from app.core.config import settings

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    rt = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(rt)
    await db.flush()
