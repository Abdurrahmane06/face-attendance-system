"""User management request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Admin user creation request.

    Attributes:
        email: User email address.
        full_name: User display name.
        password: Plaintext password (min 8 chars).
        role: User role (ADMIN or USER).
        department: Optional department name.
    """

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="USER")
    department: Optional[str] = Field(default=None, max_length=100)


class UserUpdateRequest(BaseModel):
    """User update request body (all fields optional).

    Attributes:
        full_name: Updated display name.
        email: Updated email.
        role: Updated role.
        department: Updated department.
        is_active: Updated active status.
    """

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    department: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model.

    Attributes:
        id: User UUID.
        email: User email.
        full_name: User display name.
        role: User role.
        department: Optional department.
        photo_url: Optional photo URL.
        is_active: Active flag.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedUserResponse(BaseModel):
    """Paginated list of users.

    Attributes:
        items: List of user responses.
        total: Total user count.
        page: Current page number.
        limit: Items per page.
    """

    items: List[UserResponse]
    total: int
    page: int
    limit: int


class UserDetailResponse(UserResponse):
    """Detailed user response with attendance summary."""

    pass
