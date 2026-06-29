"""Attendance ORM model.

Records daily check-in / check-out with status and late duration.
Status values are lowercase to match the Postgres ENUM definition.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Attendance(Base):
    """Daily attendance record.

    Attributes:
        id: Primary UUID.
        user_id: FK to users.
        date: Attendance date (one record per user per day).
        check_in: Check-in timestamp (timestamptz).
        check_out: Check-out timestamp (timestamptz).
        status: 'present' | 'late' | 'absent'  (Postgres ENUM).
        late_minutes: Minutes past the grace period when status = 'late'.
        recognized_by: 'FACE' or 'MANUAL'.
        notes: Optional free-text note.
        deleted_at: Soft-delete timestamp.
        created_at: Row creation timestamp.
    """

    __tablename__ = "attendances"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("present", "late", "absent", name="attendance_status"),
        default="present",
        nullable=False,
    )
    late_minutes: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    recognized_by: Mapped[str] = mapped_column(
        Enum("FACE", "MANUAL", name="recognition_method"),
        default="FACE",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )

    user = relationship("User", back_populates="attendances")
    justifications = relationship(
        "Justification", back_populates="attendance", cascade="all, delete-orphan"
    )
