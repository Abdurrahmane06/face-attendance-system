"""User (profile) ORM model.

Stores user accounts with role, credentials, and optional work schedule.
Soft-delete is handled via `deleted_at`; `is_active` is a hybrid property
so all existing callers work without changes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """User profile model.

    Attributes:
        id: Primary UUID.
        email: Unique email address.
        full_name: Display name.
        hashed_password: Bcrypt hash.
        role: ADMIN or USER.
        department: Optional department.
        photo_url: Optional profile photo path.
        work_schedule_id: FK to assigned work schedule (nullable).
        deleted_at: Soft-delete timestamp; NULL means the account is active.
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("ADMIN", "USER", name="user_role"), default="USER", nullable=False
    )
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    work_schedule_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("work_schedules.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ------------------------------------------------------------------
    # Hybrid property: backward-compatible `is_active` interface
    # ------------------------------------------------------------------

    @hybrid_property
    def is_active(self) -> bool:
        """True when the account has not been soft-deleted."""
        return self.deleted_at is None

    @is_active.setter
    def is_active(self, value: bool) -> None:
        """Setting False soft-deletes the account; True restores it."""
        self.deleted_at = None if value else datetime.now(timezone.utc)

    @is_active.expression
    @classmethod
    def is_active(cls):
        """SQL expression: deleted_at IS NULL."""
        return cls.deleted_at.is_(None)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    work_schedule = relationship("WorkSchedule", back_populates="users")
    face_encodings = relationship(
        "FaceEncoding", back_populates="user", cascade="all, delete-orphan"
    )
    attendances = relationship(
        "Attendance", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
