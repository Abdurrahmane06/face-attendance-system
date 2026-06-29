"""Justification ORM model.

Links an absence attendance record to an AbsenceType and stores optional
supporting documents plus admin approval metadata.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Justification(Base):
    """Absence justification record.

    Attributes:
        id: Primary UUID.
        attendance_id: FK to the absence attendance record.
        absence_type_id: FK to the AbsenceType catalogue entry.
        comment: Free-text justification comment.
        document_url: Optional URL / path to supporting document.
        approved_by: FK to admin User who approved (nullable until approved).
        approved_at: Timestamp of approval (nullable).
        deleted_at: Soft-delete timestamp.
        created_at: Row creation timestamp.
    """

    __tablename__ = "justifications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    attendance_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("attendances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    absence_type_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("absence_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    attendance = relationship("Attendance", back_populates="justifications")
    absence_type = relationship("AbsenceType", back_populates="justifications")
    approver = relationship("User", foreign_keys=[approved_by])
