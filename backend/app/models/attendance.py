"""Attendance ORM model for FaceAttend.

Records daily check-in and check-out events with status tracking.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Attendance(Base):
    """Daily attendance record model.

    Attributes:
        id: Primary UUID.
        user_id: Foreign key to users table.
        date: Attendance date.
        check_in: Check-in timestamp.
        check_out: Check-out timestamp.
        status: PRESENT, ABSENT, or LATE.
        recognized_by: FACE or MANUAL.
        notes: Optional notes.
        created_at: Record creation timestamp.
    """

    __tablename__ = "attendances"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("PRESENT", "ABSENT", "LATE", name="attendance_status"), default="PRESENT", nullable=False
    )
    recognized_by: Mapped[str] = mapped_column(
        Enum("FACE", "MANUAL", name="recognition_method"), default="FACE", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
    )

    user = relationship("User", back_populates="attendances")
