"""Users management router: CRUD operations for user accounts.

All endpoints require ADMIN role.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.user import (
    PaginatedUserResponse,
    UserCreateRequest,
    UserDetailResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services import user_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedUserResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> PaginatedUserResponse:
    """List users with pagination and optional search.

    Args:
        page: Page number.
        limit: Items per page.
        search: Search term for name/email.
        department: Department filter.
        db: Database session.
        admin: Authenticated admin user.

    Returns:
        PaginatedUserResponse.
    """
    return await user_service.list_users(db, page, limit, search, department)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """Create a new user (admin only).

    Args:
        request: User creation details.
        db: Database session.
        admin: Authenticated admin user.

    Returns:
        UserResponse for created user.
    """
    return await user_service.create_user(db, request)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserDetailResponse:
    """Get user details by ID.

    Args:
        user_id: User UUID.
        db: Database session.
        admin: Authenticated admin user.

    Returns:
        UserDetailResponse.
    """
    return await user_service.get_user(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """Update a user's details.

    Args:
        user_id: User UUID.
        request: Fields to update.
        db: Database session.
        admin: Authenticated admin user.

    Returns:
        Updated UserResponse.
    """
    return await user_service.update_user(db, user_id, request)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    """Soft-delete a user account.

    Args:
        user_id: User UUID to delete.
        db: Database session.
        admin: Authenticated admin user.
    """
    await user_service.delete_user(db, user_id)


@router.post("/{user_id}/photo", response_model=UserResponse)
async def upload_user_photo(
    user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserResponse:
    """Upload a profile photo for a user.

    Args:
        user_id: User UUID.
        file: Image file (JPEG/PNG, max 5MB).
        db: Database session.
        admin: Authenticated admin user.

    Returns:
        Updated UserResponse with photo URL.
    """
    return await user_service.upload_photo(db, user_id, file)
