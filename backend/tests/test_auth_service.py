"""Tests for the authentication service.

Covers registration, login, token refresh, and logout flows.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service


@pytest.mark.asyncio
async def test_register_user_success(db_session: AsyncSession):
    """Test successful user registration."""
    request = RegisterRequest(
        email="test@example.com",
        full_name="Test User",
        password="password123",
        role="USER",
    )
    result = await auth_service.register_user(db_session, request)

    assert result.data.access_token is not None
    assert result.data.refresh_token is not None
    assert result.user.email == "test@example.com"
    assert result.user.full_name == "Test User"
    assert result.user.role == "USER"


@pytest.mark.asyncio
async def test_register_duplicate_email(db_session: AsyncSession):
    """Test registration with an existing email raises 409."""
    request = RegisterRequest(
        email="dupe@example.com",
        full_name="First User",
        password="password123",
    )
    await auth_service.register_user(db_session, request)

    with pytest.raises(HTTPException) as exc:
        await auth_service.register_user(db_session, request)
    assert exc.value.status_code == 409
    assert "already registered" in exc.value.detail


@pytest.mark.asyncio
async def test_login_success(db_session: AsyncSession):
    """Test successful login with valid credentials."""
    register_req = RegisterRequest(
        email="login@example.com",
        full_name="Login User",
        password="securepass1",
    )
    await auth_service.register_user(db_session, register_req)

    login_req = LoginRequest(email="login@example.com", password="securepass1")
    result = await auth_service.login_user(db_session, login_req)

    assert result.data.access_token is not None
    assert result.data.refresh_token is not None
    assert result.user.email == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(db_session: AsyncSession):
    """Test login with wrong password raises 401."""
    register_req = RegisterRequest(
        email="wrongpw@example.com",
        full_name="Wrong PW",
        password="correctpw1",
    )
    await auth_service.register_user(db_session, register_req)

    login_req = LoginRequest(email="wrongpw@example.com", password="wrongpw1")
    with pytest.raises(HTTPException) as exc:
        await auth_service.login_user(db_session, login_req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(db_session: AsyncSession):
    """Test login for deactivated user raises 401."""
    register_req = RegisterRequest(
        email="inactive@example.com",
        full_name="Inactive User",
        password="password1",
    )
    await auth_service.register_user(db_session, register_req)

    result = await db_session.execute(
        __import__("sqlalchemy").select(User).where(User.email == "inactive@example.com")
    )
    user = result.scalar_one()
    user.is_active = False
    await db_session.flush()

    login_req = LoginRequest(email="inactive@example.com", password="password1")
    with pytest.raises(HTTPException) as exc:
        await auth_service.login_user(db_session, login_req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(db_session: AsyncSession):
    """Test token refresh flow."""
    register_req = RegisterRequest(
        email="refresh@example.com",
        full_name="Refresh User",
        password="password1",
    )
    reg_result = await auth_service.register_user(db_session, register_req)

    from app.schemas.auth import RefreshRequest
    refresh_result = await auth_service.refresh_access_token(
        db_session, reg_result.data.refresh_token
    )
    assert refresh_result.access_token is not None
    assert refresh_result.token_type == "bearer"


@pytest.mark.asyncio
async def test_logout_revokes_token(db_session: AsyncSession):
    """Test logout revokes the refresh token."""
    register_req = RegisterRequest(
        email="logout@example.com",
        full_name="Logout User",
        password="password1",
    )
    reg_result = await auth_service.register_user(db_session, register_req)

    await auth_service.logout_user(db_session, reg_result.data.refresh_token)

    from app.schemas.auth import RefreshRequest
    with pytest.raises(HTTPException) as exc:
        await auth_service.refresh_access_token(
            db_session, reg_result.data.refresh_token
        )
    assert exc.value.status_code == 401
