"""Authentication request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request body.

    Attributes:
        email: User email address.
        full_name: User display name.
        password: Plaintext password (min 8 chars).
        role: Optional role (default USER).
    """

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="USER")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Ensure role is valid."""
        if v.upper() not in ("ADMIN", "USER"):
            raise ValueError("Role must be ADMIN or USER")
        return v.upper()


class LoginRequest(BaseModel):
    """User login request body.

    Attributes:
        email: User email address.
        password: Plaintext password.
    """

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT token response.

    Attributes:
        access_token: JWT access token.
        refresh_token: JWT refresh token.
        token_type: Token type (bearer).
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Token refresh request body.

    Attributes:
        refresh_token: Valid refresh token string.
    """

    refresh_token: str


class UserInfo(BaseModel):
    """Public user information returned with auth responses.

    Attributes:
        id: User UUID.
        email: User email.
        full_name: User display name.
        role: User role.
        department: Optional department.
        is_active: Account active flag.
    """

    id: str
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response including tokens and user info.

    Attributes:
        data: TokenResponse with access/refresh tokens.
        user: UserInfo for the authenticated user.
    """

    data: TokenResponse
    user: UserInfo
    message: str = "Authentication successful"
    status: int = 200
