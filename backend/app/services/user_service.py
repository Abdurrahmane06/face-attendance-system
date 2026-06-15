"""User management service: CRUD operations for user accounts.

Provides paginated listing, creation, update, soft-delete,
and profile photo upload functionality.
"""

import logging
import os
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import (
    PaginatedUserResponse,
    UserCreateRequest,
    UserDetailResponse,
    UserResponse,
    UserUpdateRequest,
)

logger = logging.getLogger(__name__)


async def list_users(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    department: Optional[str] = None,
) -> PaginatedUserResponse:
    """Retrieve paginated list of users with optional filtering.

    Args:
        db: Database session.
        page: Page number (1-indexed).
        limit: Items per page.
        search: Optional search term for name or email.
        department: Optional department filter.

    Returns:
        PaginatedUserResponse with user list and metadata.
    """
    query = select(User)

    if search:
        query = query.where(
            User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )
    if department:
        query = query.where(User.department == department)

    query = query.order_by(User.created_at.desc())

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedUserResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
    )


async def create_user(db: AsyncSession, request: UserCreateRequest) -> UserResponse:
    """Create a new user account (admin only).

    Args:
        db: Database session.
        request: User creation details.

    Returns:
        UserResponse with created user data.

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
        department=request.department,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def get_user(db: AsyncSession, user_id: str) -> UserDetailResponse:
    """Get user details by ID.

    Args:
        db: Database session.
        user_id: User UUID.

    Returns:
        UserDetailResponse.

    Raises:
        HTTPException 404: If user not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserDetailResponse.model_validate(user)


async def update_user(
    db: AsyncSession, user_id: str, request: UserUpdateRequest
) -> UserResponse:
    """Update user fields.

    Args:
        db: Database session.
        user_id: User UUID to update.
        request: Fields to update.

    Returns:
        Updated UserResponse.

    Raises:
        HTTPException 404: If user not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def delete_user(db: AsyncSession, user_id: str) -> None:
    """Soft-delete a user by setting is_active to False.

    Args:
        db: Database session.
        user_id: User UUID to delete.

    Raises:
        HTTPException 404: If user not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user.is_active = False
    await db.flush()


async def upload_photo(
    db: AsyncSession, user_id: str, file: UploadFile
) -> UserResponse:
    """Upload a profile photo for a user.

    Args:
        db: Database session.
        user_id: User UUID.
        file: Uploaded image file (JPEG/PNG, max 5MB).

    Returns:
        Updated UserResponse with photo URL.

    Raises:
        HTTPException 400: If file is invalid.
        HTTPException 404: If user not found.
    """
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG files are allowed",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must not exceed 5MB",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    user.photo_url = f"/uploads/{filename}"
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)
