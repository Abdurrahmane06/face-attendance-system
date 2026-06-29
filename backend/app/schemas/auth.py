"""Authentication request / response schemas."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Public user registration — always creates a USER-role account.

    Admins are created via POST /api/v1/users (admin-only) or the seed endpoint.
    """

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class SeedAdminRequest(BaseModel):
    """First-admin bootstrap request.

    Only succeeds when no ADMIN exists in the database yet.
    Defaults are provided so the endpoint works without a body in dev.
    """

    email: EmailStr = "admin@faceattend.local"
    full_name: str = Field(default="Administrateur", min_length=1, max_length=255)
    password: str = Field(default="Admin@1234!", min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """User login credentials."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh-token payload for /auth/refresh and /auth/logout."""

    refresh_token: str


class UserInfo(BaseModel):
    """Public user info returned with auth responses."""

    id: str
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Combined auth response: tokens + user profile."""

    data: TokenResponse
    user: UserInfo
    message: str = "Authentication successful"
    status: int = 200
