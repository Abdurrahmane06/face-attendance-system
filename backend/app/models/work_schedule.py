"""WorkSchedule ORM model.

Stores named work schedules with expected start time and grace period.
Each profile can be assigned a schedule; it drives late detection logic.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import DateTime, Integer, String, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkSchedule(Base):
    """Named work schedule.

    Attributes:
        id: Primary UUID.
        name: Human-readable label (e.g. "Horaire standard").
        expected_start_time: Time employees must arrive by.
        grace_period_minutes: Extra minutes allowed before marking late.
        deleted_at: Soft-delete timestamp; NULL = active.
        created_at: Row creation timestamp.
    """

    __tablename__ = "work_schedules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_start_time: Mapped[time] = mapped_column(Time(), nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer(), nullable=False, default=15)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    users = relationship("User", back_populates="work_schedule")
